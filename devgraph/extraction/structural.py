"""
Structural code extraction using Tree-sitter for DevGraph.

Why this module exists:
Parses Python source files using Tree-sitter AST queries, extracting File, Class, and Function
nodes, imports (file-to-file), function calls, definitions, and derived file dependencies.
Enforces deterministic extraction and attaches full provenance to all produced edges.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import git
import tree_sitter
import tree_sitter_python
from pydantic import BaseModel, Field

from devgraph.extraction.resolver import ImportResolver
from devgraph.models import Artifact, Edge, RepoHandle

logger = logging.getLogger(__name__)


def node_text(node: tree_sitter.Node, content: bytes) -> str:
    """Safely extracts text slice from the underlying content bytes."""
    return content[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


class ExtractionStats(BaseModel):
    """Statistics gathered during structural AST extraction."""
    num_files: int = 0
    num_classes: int = 0
    num_functions: int = 0
    num_contains: int = 0
    num_defines: int = 0
    num_imports: int = 0
    num_calls: int = 0
    num_depends_on: int = 0
    total_raw_imports: int = 0
    internal_candidate_imports: int = 0
    resolved_internal_imports: int = 0
    resolved_import_rate: float = 0.0


@dataclass
class RawCall:
    """A raw function call site within a specific function."""
    caller_function_id: str
    caller_file: str
    callee_expr: str
    callee_base: Optional[str] = None
    callee_attr: Optional[str] = None


@dataclass
class DefInterval:
    """Interval representing a Class or Function definition."""
    start_byte: int
    end_byte: int
    kind: str  # "class" or "function"
    name: str
    qualname: str
    node_id: str
    parent_id: str
    start_line: int
    end_line: int
    is_method: bool


@dataclass
class FileASTData:
    """Intermediate AST structures extracted from a single source file."""
    rel_path: str
    loc: int
    is_test: bool
    classes: List[Artifact] = field(default_factory=list)
    functions: List[Artifact] = field(default_factory=list)
    defines_edges: List[Edge] = field(default_factory=list)
    contains_edges: List[Edge] = field(default_factory=list)
    raw_calls: List[RawCall] = field(default_factory=list)
    imported_symbols: Dict[str, Tuple[str, Optional[str]]] = field(default_factory=dict)
    imported_files: Set[str] = field(default_factory=set)


def is_test_file(rel_path: str) -> bool:
    """Checks whether a file path corresponds to a test artifact."""
    p = Path(rel_path)
    if any(part in ("tests", "test") for part in p.parts):
        return True
    if p.name.startswith("test_") or p.name.endswith("_test.py"):
        return True
    return False


class StructuralExtractor:
    """
    Extracts knowledge graph nodes and edges from a repository's Python source files.
    """

    def __init__(self, repo_handle: RepoHandle) -> None:
        self.repo_handle = repo_handle
        self.repo_dir = Path(repo_handle.path).resolve()
        self.repo_name = repo_handle.name
        self.head_sha = repo_handle.head_sha

        # Get snapshot timestamp from Git
        self.commit_timestamp: int = 0
        try:
            repo = git.Repo(self.repo_dir)
            self.commit_timestamp = int(repo.head.commit.committed_date)
        except Exception:
            pass

        self.resolver = ImportResolver(self.repo_dir)
        self.language = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser(self.language)

        # Pre-compile Tree-sitter AST queries
        self.q_defs = tree_sitter.Query(
            self.language,
            """
            [(class_definition name: (identifier) @name) @cls
             (function_definition name: (identifier) @name) @fn]
            """,
        )
        self.q_calls = tree_sitter.Query(self.language, "(call function: (_) @func) @call")
        self.q_imports = tree_sitter.Query(
            self.language,
            "[(import_statement) @imp (import_from_statement) @imp_from]",
        )

    def extract(self) -> Tuple[List[Artifact], List[Edge], ExtractionStats]:
        """
        Executes AST extraction across all discovered Python files in the repository.

        Returns:
            Tuple of (artifacts, edges, stats).
        """
        artifacts: List[Artifact] = []
        edges: List[Edge] = []
        stats = ExtractionStats()

        # 1. Create Repository root node
        repo_node_id = f"{self.repo_name}:Repository:{self.repo_name}"
        repo_artifact = Artifact(
            id=repo_node_id,
            repo=self.repo_name,
            type="Repository",
            name=self.repo_name,
            path="",
            created_at=self.commit_timestamp,
            properties={
                "url": self.repo_handle.url,
                "snapshot_sha": self.head_sha,
            },
        )
        artifacts.append(repo_artifact)

        file_data_list: List[FileASTData] = []
        function_index: Set[str] = set()

        sorted_files = sorted(list(self.resolver.valid_repo_files))
        stats.num_files = len(sorted_files)

        # 2. Extract AST per file
        for rel_path in sorted_files:
            file_data = self._parse_file(rel_path)
            file_data_list.append(file_data)

            # File node
            file_id = f"{self.repo_name}:File:{rel_path}"
            file_artifact = Artifact(
                id=file_id,
                repo=self.repo_name,
                type="File",
                name=Path(rel_path).name,
                path=rel_path,
                created_at=self.commit_timestamp,
                properties={
                    "language": "python",
                    "loc": file_data.loc,
                    "is_test": file_data.is_test,
                    "is_doc": False,
                },
            )
            artifacts.append(file_artifact)

            # Repo CONTAINS File edge
            contains_edge = Edge(
                src=repo_node_id,
                dst=file_id,
                type="CONTAINS",
                confidence=1.0,
                method="ast",
                source_commit=self.head_sha,
                timestamp=self.commit_timestamp,
                is_deterministic=True,
            )
            edges.append(contains_edge)

            # Class and function nodes
            artifacts.extend(file_data.classes)
            artifacts.extend(file_data.functions)
            edges.extend(file_data.defines_edges)
            edges.extend(file_data.contains_edges)

            stats.num_classes += len(file_data.classes)
            stats.num_functions += len(file_data.functions)
            stats.num_defines += len(file_data.defines_edges)
            stats.num_contains += len(file_data.contains_edges)

            for fn in file_data.functions:
                function_index.add(fn.id)

        # 3. Create IMPORTS edges and track resolution stats
        import_edges_map: Dict[Tuple[str, str], Edge] = {}

        for file_data in file_data_list:
            src_file_id = f"{self.repo_name}:File:{file_data.rel_path}"
            for target_file in file_data.imported_files:
                if target_file == file_data.rel_path:
                    continue
                dst_file_id = f"{self.repo_name}:File:{target_file}"
                key = (src_file_id, dst_file_id)
                if key not in import_edges_map:
                    import_edges_map[key] = Edge(
                        src=src_file_id,
                        dst=dst_file_id,
                        type="IMPORTS",
                        confidence=1.0,
                        method="ast",
                        source_commit=self.head_sha,
                        timestamp=self.commit_timestamp,
                        is_deterministic=True,
                    )

        edges.extend(import_edges_map.values())
        stats.num_imports = len(import_edges_map)

        # 4. Resolve function CALLS and build CALLS edges
        call_edges_map: Dict[Tuple[str, str], Edge] = {}
        calls_across_files: Set[Tuple[str, str]] = set()

        for file_data in file_data_list:
            for raw_call in file_data.raw_calls:
                target_func_id = self._resolve_call(raw_call, file_data, function_index)
                if target_func_id:
                    key = (raw_call.caller_function_id, target_func_id)
                    if key not in call_edges_map:
                        call_edges_map[key] = Edge(
                            src=raw_call.caller_function_id,
                            dst=target_func_id,
                            type="CALLS",
                            confidence=1.0,
                            method="ast",
                            source_commit=self.head_sha,
                            timestamp=self.commit_timestamp,
                            is_deterministic=True,
                        )
                    # Track cross-file calls for DEPENDS_ON
                    target_file = target_func_id.split(":")[2].split("::")[0]
                    if target_file != file_data.rel_path:
                        src_fid = f"{self.repo_name}:File:{file_data.rel_path}"
                        dst_fid = f"{self.repo_name}:File:{target_file}"
                        calls_across_files.add((src_fid, dst_fid))

        edges.extend(call_edges_map.values())
        stats.num_calls = len(call_edges_map)

        # 5. Derive DEPENDS_ON edges (from IMPORTS + cross-file CALLS)
        depends_on_map: Dict[Tuple[str, str], Edge] = {}
        # From IMPORTS
        for (src_fid, dst_fid) in import_edges_map.keys():
            if src_fid != dst_fid:
                depends_on_map[(src_fid, dst_fid)] = Edge(
                    src=src_fid,
                    dst=dst_fid,
                    type="DEPENDS_ON",
                    confidence=1.0,
                    method="ast",
                    source_commit=self.head_sha,
                    timestamp=self.commit_timestamp,
                    is_deterministic=True,
                )
        # From cross-file CALLS
        for (src_fid, dst_fid) in calls_across_files:
            if src_fid != dst_fid and (src_fid, dst_fid) not in depends_on_map:
                depends_on_map[(src_fid, dst_fid)] = Edge(
                    src=src_fid,
                    dst=dst_fid,
                    type="DEPENDS_ON",
                    confidence=1.0,
                    method="ast",
                    source_commit=self.head_sha,
                    timestamp=self.commit_timestamp,
                    is_deterministic=True,
                )

        edges.extend(depends_on_map.values())
        stats.num_depends_on = len(depends_on_map)

        # 6. Aggregate import resolution metrics
        for fd in file_data_list:
            stats.total_raw_imports += getattr(fd, "_total_raw_imports", 0)
            stats.internal_candidate_imports += getattr(fd, "_internal_candidates", 0)
            stats.resolved_internal_imports += getattr(fd, "_resolved_internal", 0)

        if stats.internal_candidate_imports > 0:
            stats.resolved_import_rate = (
                stats.resolved_internal_imports / stats.internal_candidate_imports
            ) * 100.0
        else:
            stats.resolved_import_rate = 100.0

        return artifacts, edges, stats

    def _parse_file(self, rel_path: str) -> FileASTData:
        """Parses a single Python file into FileASTData."""
        abs_path = self.repo_dir / rel_path
        try:
            content_bytes = abs_path.read_bytes()
        except OSError:
            content_bytes = b""

        loc = content_bytes.count(b"\n") + (1 if content_bytes and not content_bytes.endswith(b"\n") else 0)
        tree = self.parser.parse(content_bytes)

        file_data = FileASTData(
            rel_path=rel_path,
            loc=loc,
            is_test=is_test_file(rel_path),
        )

        file_node_id = f"{self.repo_name}:File:{rel_path}"

        # 1. Parse Imports via QueryCursor
        qc_imp = tree_sitter.QueryCursor(self.q_imports)
        imp_captures = qc_imp.captures(tree.root_node)

        total_raw_imports = 0
        internal_candidates = 0
        resolved_internal = 0

        # import_statement: 'import x, y as z'
        for stmt in imp_captures.get("imp", []):
            for sub in stmt.children:
                if sub.type == "dotted_name":
                    mod_name = node_text(sub, content_bytes)
                    total_raw_imports += 1
                    is_cand = self.resolver.is_internal_candidate(mod_name, level=0)
                    if is_cand:
                        internal_candidates += 1
                    target_file = self.resolver.resolve_import(rel_path, module_name=mod_name, level=0)
                    if target_file:
                        file_data.imported_files.add(target_file)
                        file_data.imported_symbols[mod_name] = (target_file, None)
                        if is_cand:
                            resolved_internal += 1
                elif sub.type == "aliased_import":
                    name_node = sub.child_by_field_name("name")
                    alias_node = sub.child_by_field_name("alias")
                    if name_node and alias_node:
                        mod_name = node_text(name_node, content_bytes)
                        alias = node_text(alias_node, content_bytes)
                        total_raw_imports += 1
                        is_cand = self.resolver.is_internal_candidate(mod_name, level=0)
                        if is_cand:
                            internal_candidates += 1
                        target_file = self.resolver.resolve_import(rel_path, module_name=mod_name, level=0)
                        if target_file:
                            file_data.imported_files.add(target_file)
                            file_data.imported_symbols[alias] = (target_file, None)
                            if is_cand:
                                resolved_internal += 1

        # import_from_statement: 'from ...x import y as z'
        for stmt in imp_captures.get("imp_from", []):
            mod_node = stmt.child_by_field_name("module_name")
            level = 0
            mod_name = None

            if mod_node:
                if mod_node.type == "relative_import":
                    raw_text = node_text(mod_node, content_bytes)
                    level = len(raw_text) - len(raw_text.lstrip("."))
                    rest = raw_text.lstrip(".")
                    mod_name = rest if rest else None
                else:
                    mod_name = node_text(mod_node, content_bytes)
            else:
                for sub in stmt.children:
                    if sub.type == "import_prefix":
                        dots = node_text(sub, content_bytes)
                        level = len(dots)
                        break

            symbols: List[Tuple[str, str]] = []  # (orig_sym, local_alias)
            in_imports = False
            for sub in stmt.children:
                if sub.type == "import":
                    in_imports = True
                    continue
                if not in_imports:
                    continue
                if sub.type in ("dotted_name", "identifier"):
                    sym_name = node_text(sub, content_bytes)
                    symbols.append((sym_name, sym_name))
                elif sub.type == "aliased_import":
                    name_n = sub.child_by_field_name("name")
                    alias_n = sub.child_by_field_name("alias")
                    if name_n and alias_n:
                        symbols.append((
                            node_text(name_n, content_bytes),
                            node_text(alias_n, content_bytes),
                        ))

            is_cand = self.resolver.is_internal_candidate(mod_name, level=level)

            for orig_sym, local_alias in symbols:
                total_raw_imports += 1
                if is_cand:
                    internal_candidates += 1
                target_file = self.resolver.resolve_import(
                    rel_path, module_name=mod_name, level=level, imported_symbol=orig_sym
                )
                if target_file:
                    file_data.imported_files.add(target_file)
                    file_data.imported_symbols[local_alias] = (target_file, orig_sym)
                    if is_cand:
                        resolved_internal += 1

        file_data._total_raw_imports = total_raw_imports  # type: ignore[attr-defined]
        file_data._internal_candidates = internal_candidates  # type: ignore[attr-defined]
        file_data._resolved_internal = resolved_internal  # type: ignore[attr-defined]

        # 2. Extract Class and Function definitions via intervals
        qc_defs = tree_sitter.QueryCursor(self.q_defs)
        def_captures = qc_defs.captures(tree.root_node)

        raw_def_nodes: List[Tuple[tree_sitter.Node, str]] = []
        for node in def_captures.get("cls", []):
            raw_def_nodes.append((node, "class"))
        for node in def_captures.get("fn", []):
            raw_def_nodes.append((node, "function"))

        # Sort definitions by start_byte ascending, end_byte descending (outer before inner)
        raw_def_nodes.sort(key=lambda item: (item[0].start_byte, -item[0].end_byte))

        # Build definition intervals and qualnames using interval nesting stack
        intervals: List[DefInterval] = []
        scope_stack: List[DefInterval] = []

        for node, kind in raw_def_nodes:
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = node_text(name_node, content_bytes)
            start_byte = node.start_byte
            end_byte = node.end_byte
            start_line = content_bytes[:start_byte].count(b"\n") + 1
            end_line = content_bytes[:end_byte].count(b"\n") + 1

            # Pop scopes that do not enclose current definition
            while scope_stack and not (
                scope_stack[-1].start_byte <= start_byte and end_byte <= scope_stack[-1].end_byte
            ):
                scope_stack.pop()

            parent = scope_stack[-1] if scope_stack else None
            if parent:
                qualname = f"{parent.qualname}.{name}"
                parent_id = parent.node_id
                is_method = (parent.kind == "class")
            else:
                qualname = name
                parent_id = file_node_id
                is_method = False

            if kind == "class":
                node_id = f"{self.repo_name}:Class:{rel_path}::{qualname}"
                class_artifact = Artifact(
                    id=node_id,
                    repo=self.repo_name,
                    type="Class",
                    name=qualname,
                    path=rel_path,
                    created_at=self.commit_timestamp,
                    properties={
                        "qualname": qualname,
                        "file": rel_path,
                        "start_line": start_line,
                        "end_line": end_line,
                    },
                )
                file_data.classes.append(class_artifact)
            else:
                node_id = f"{self.repo_name}:Function:{rel_path}::{qualname}"
                fn_artifact = Artifact(
                    id=node_id,
                    repo=self.repo_name,
                    type="Function",
                    name=qualname,
                    path=rel_path,
                    created_at=self.commit_timestamp,
                    properties={
                        "qualname": qualname,
                        "file": rel_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "is_method": is_method,
                    },
                )
                file_data.functions.append(fn_artifact)

            # DEFINES edge
            file_data.defines_edges.append(
                Edge(
                    src=parent_id,
                    dst=node_id,
                    type="DEFINES",
                    confidence=1.0,
                    method="ast",
                    source_commit=self.head_sha,
                    timestamp=self.commit_timestamp,
                    is_deterministic=True,
                )
            )

            # CONTAINS edge
            file_data.contains_edges.append(
                Edge(
                    src=parent_id,
                    dst=node_id,
                    type="CONTAINS",
                    confidence=1.0,
                    method="ast",
                    source_commit=self.head_sha,
                    timestamp=self.commit_timestamp,
                    is_deterministic=True,
                )
            )

            interval = DefInterval(
                start_byte=start_byte,
                end_byte=end_byte,
                kind=kind,
                name=name,
                qualname=qualname,
                node_id=node_id,
                parent_id=parent_id,
                start_line=start_line,
                end_line=end_line,
                is_method=is_method,
            )
            intervals.append(interval)
            scope_stack.append(interval)

        # 3. Extract Calls and attribute them to the innermost enclosing Function
        func_intervals = [it for it in intervals if it.kind == "function"]

        qc_calls = tree_sitter.QueryCursor(self.q_calls)
        call_captures = qc_calls.captures(tree.root_node)

        for call_node in call_captures.get("call", []):
            fn_node = call_node.child_by_field_name("function")
            if not fn_node:
                continue

            call_start = call_node.start_byte
            call_end = call_node.end_byte

            # Find innermost function interval containing this call
            enclosing_func: Optional[DefInterval] = None
            min_len = float("inf")
            for fi in func_intervals:
                if fi.start_byte <= call_start and call_end <= fi.end_byte:
                    span = fi.end_byte - fi.start_byte
                    if span < min_len:
                        min_len = span
                        enclosing_func = fi

            if not enclosing_func:
                # Top-level call outside any function definition
                continue

            callee_text = node_text(fn_node, content_bytes)
            raw = RawCall(
                caller_function_id=enclosing_func.node_id,
                caller_file=rel_path,
                callee_expr=callee_text,
            )
            if fn_node.type == "attribute":
                obj = fn_node.child_by_field_name("object")
                attr = fn_node.child_by_field_name("attribute")
                if obj and attr:
                    raw.callee_base = node_text(obj, content_bytes)
                    raw.callee_attr = node_text(attr, content_bytes)

            file_data.raw_calls.append(raw)

        return file_data

    def _resolve_call(
        self,
        raw_call: RawCall,
        file_data: FileASTData,
        function_index: Set[str],
    ) -> Optional[str]:
        """
        Attempts to resolve a call site to a target Function node ID.
        Returns the Function ID if resolved, else None.
        """
        expr = raw_call.callee_expr

        # 1. Attribute call: obj.attr()
        if raw_call.callee_base and raw_call.callee_attr:
            base = raw_call.callee_base
            attr = raw_call.callee_attr

            # 1a. self.method() or cls.method()
            if base in ("self", "cls"):
                # Caller ID format: repo:Function:path::Class.method
                qual = raw_call.caller_function_id.split("::")[-1]
                if "." in qual:
                    class_prefix = qual.rsplit(".", 1)[0]
                    target_id = f"{self.repo_name}:Function:{raw_call.caller_file}::{class_prefix}.{attr}"
                    if target_id in function_index:
                        return target_id

            # 1b. imported_mod.func() or imported_alias.func()
            if base in file_data.imported_symbols:
                target_file, _ = file_data.imported_symbols[base]
                target_id = f"{self.repo_name}:Function:{target_file}::{attr}"
                if target_id in function_index:
                    return target_id

            # 1c. ClassName.method() in the same file
            same_file_id = f"{self.repo_name}:Function:{raw_call.caller_file}::{base}.{attr}"
            if same_file_id in function_index:
                return same_file_id

        # 2. Simple identifier call: func()
        # 2a. Function in the same file
        same_file_fn = f"{self.repo_name}:Function:{raw_call.caller_file}::{expr}"
        if same_file_fn in function_index:
            return same_file_fn

        # 2b. Imported symbol: from mod import func
        if expr in file_data.imported_symbols:
            target_file, target_sym = file_data.imported_symbols[expr]
            sym = target_sym if target_sym else expr
            target_fn = f"{self.repo_name}:Function:{target_file}::{sym}"
            if target_fn in function_index:
                return target_fn

        return None
