"""
Import and module resolution for DevGraph.

Why this module exists:
Maps dotted Python module imports and relative imports to actual file paths inside
the repository. Handles standard 'src/' packaging layouts and '__init__.py' modules
while filtering out external third-party dependencies and Python standard library imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ImportResolver:
    """
    Resolves dotted Python module names and relative imports to file paths inside a repository.
    """

    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.module_to_file: Dict[str, str] = {}
        self.valid_repo_files: Set[str] = set()
        self.source_roots: List[Path] = []
        self.repo_packages: Set[str] = set()

        self._discover_files_and_roots()
        self._build_module_map()

    def _discover_files_and_roots(self) -> None:
        """Discovers all valid Python files and potential source roots."""
        excluded_dirs = {
            ".git",
            ".venv",
            "venv",
            "build",
            "dist",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".tox",
            ".mypy_cache",
            ".eggs",
        }

        # Candidate roots: repo root and src/ directory if present
        self.source_roots.append(self.repo_dir)
        src_dir = self.repo_dir / "src"
        if src_dir.is_dir():
            self.source_roots.append(src_dir)

        # Walk repo and index .py files
        for path in self.repo_dir.rglob("*.py"):
            parts = path.parts
            if any(exc in parts for exc in excluded_dirs):
                continue
            # Skip files larger than 1 MB
            try:
                if path.stat().st_size > 1024 * 1024:
                    continue
            except OSError:
                continue

            rel_path = path.relative_to(self.repo_dir).as_posix()
            self.valid_repo_files.add(rel_path)

    def _build_module_map(self) -> None:
        """Builds dotted module name to repo-relative file path mapping."""
        for root in self.source_roots:
            for rel_file in self.valid_repo_files:
                abs_file = self.repo_dir / rel_file
                if not abs_file.is_relative_to(root):
                    continue

                rel_to_root = abs_file.relative_to(root)
                parts = rel_to_root.parts

                if parts[-1] == "__init__.py":
                    dotted = ".".join(parts[:-1])
                elif parts[-1].endswith(".py"):
                    stem = parts[-1][:-3]
                    dotted = ".".join(parts[:-1] + (stem,))
                else:
                    continue

                if dotted:
                    self.module_to_file[dotted] = rel_file
                    top_pkg = dotted.split(".")[0]
                    self.repo_packages.add(top_pkg)

    def is_internal_candidate(
        self,
        module_name: Optional[str],
        level: int = 0,
    ) -> bool:
        """
        Determines whether an import statement is targeting an internal repo module.
        Relative imports are always internal candidates.
        Absolute imports whose top-level package matches a repo package are internal candidates.
        """
        if level > 0:
            return True
        if not module_name:
            return False
        top_name = module_name.split(".")[0]
        return top_name in self.repo_packages

    def resolve_import(
        self,
        source_file: str,
        module_name: Optional[str] = None,
        level: int = 0,
        imported_symbol: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolves an import statement to a relative file path inside the repository.

        Args:
            source_file: Repo-relative path of the importing file (e.g., 'src/click/core.py').
            module_name: Dotted module name string (e.g., 'types', 'click.utils'), or None.
            level: Number of leading dots for relative imports (0 = absolute, 1 = '.', 2 = '..').
            imported_symbol: Optional specific symbol or submodule imported.

        Returns:
            Repo-relative path of the target file, or None if external/unresolved.
        """
        if level > 0:
            return self._resolve_relative(source_file, module_name, level, imported_symbol)
        return self._resolve_absolute(module_name, imported_symbol)

    def _resolve_relative(
        self,
        source_file: str,
        module_name: Optional[str],
        level: int,
        imported_symbol: Optional[str],
    ) -> Optional[str]:
        """Handles relative import resolution based on importing file location."""
        source_path = Path(source_file)
        curr_dir = source_path.parent

        # Level 1 is current dir; level 2 is parent dir, etc.
        target_dir = curr_dir
        for _ in range(level - 1):
            target_dir = target_dir.parent

        # 1. If module_name is provided, navigate into it
        if module_name:
            mod_parts = module_name.split(".")
            candidate_base = target_dir.joinpath(*mod_parts)

            # Check candidate.py
            py_path = candidate_base.with_suffix(".py").as_posix()
            if py_path in self.valid_repo_files:
                return py_path

            # Check candidate/__init__.py
            init_path = (candidate_base / "__init__.py").as_posix()
            if init_path in self.valid_repo_files:
                # If imported_symbol is itself a submodule inside this package:
                if imported_symbol:
                    sub_py = (candidate_base / f"{imported_symbol}.py").as_posix()
                    if sub_py in self.valid_repo_files:
                        return sub_py
                    sub_init = (candidate_base / imported_symbol / "__init__.py").as_posix()
                    if sub_init in self.valid_repo_files:
                        return sub_init
                return init_path

        # 2. If module_name is empty/None (e.g., 'from . import foo'):
        if imported_symbol:
            sym_py = (target_dir / f"{imported_symbol}.py").as_posix()
            if sym_py in self.valid_repo_files:
                return sym_py

            sym_init = (target_dir / imported_symbol / "__init__.py").as_posix()
            if sym_init in self.valid_repo_files:
                return sym_init

        # Check target_dir/__init__.py
        dir_init = (target_dir / "__init__.py").as_posix()
        if dir_init in self.valid_repo_files:
            return dir_init

        return None

    def _resolve_absolute(
        self,
        module_name: Optional[str],
        imported_symbol: Optional[str],
    ) -> Optional[str]:
        """Handles absolute dotted import resolution."""
        if not module_name:
            return None

        # 1. If imported_symbol is provided, test if module.symbol is a submodule file
        if imported_symbol:
            full_dotted = f"{module_name}.{imported_symbol}"
            if full_dotted in self.module_to_file:
                return self.module_to_file[full_dotted]

        # 2. Direct lookup for module_name
        if module_name in self.module_to_file:
            return self.module_to_file[module_name]

        return None
