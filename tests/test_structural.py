"""
Tests for Week 2 Structural Extraction, Import Resolution, and Knowledge Graph Creation.

Why this module exists:
Verifies the Definition of Done (DoD) for Week 2:
1. Unit tests on 3 tiny fixture Python files with known imports and calls.
2. Relative and absolute import resolution across src/ and test layouts.
3. Class/Function extraction, is_test flag, and deterministic provenance metadata.
4. Neo4j batch persistence of nodes, dual-labeling, and typed relationships.
"""

from __future__ import annotations

from pathlib import Path
import git
import pytest

from devgraph.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from devgraph.extraction.resolver import ImportResolver
from devgraph.extraction.structural import StructuralExtractor
from devgraph.graph.neo4j_store import Neo4jStore
from devgraph.models import RepoHandle


def create_synthetic_fixture_repo(tmp_path: Path) -> RepoHandle:
    """Creates a local Git repository with 3 Python files having known imports and calls."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    src_pkg = repo_dir / "src" / "pkg"
    src_pkg.mkdir(parents=True)
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir(parents=True)

    # 1. Package init
    (src_pkg / "__init__.py").write_text("# pkg init\n")

    # 2. File A: service.py
    file_a = src_pkg / "service.py"
    file_a.write_text(
        "def helper():\n"
        "    return 42\n"
        "\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return helper()\n"
    )

    # 3. File B: client.py
    file_b = src_pkg / "client.py"
    file_b.write_text(
        "from .service import Service, helper\n"
        "\n"
        "class Client:\n"
        "    def invoke(self):\n"
        "        return helper()\n"
    )

    # 4. File C: test_client.py
    file_c = tests_dir / "test_client.py"
    file_c.write_text(
        "import pkg.client as c\n"
        "\n"
        "def test_client_call():\n"
        "    client = c.Client()\n"
        "    return client.invoke()\n"
    )

    # Initialize Git repo and commit
    repo = git.Repo.init(repo_dir)
    repo.index.add([
        "src/pkg/__init__.py",
        "src/pkg/service.py",
        "src/pkg/client.py",
        "tests/test_client.py",
    ])
    commit = repo.index.commit("Initial fixture commit")

    return RepoHandle(
        path=repo_dir,
        head_sha=commit.hexsha,
        name="test_repo",
        url=str(repo_dir),
    )


def test_import_resolver_unit(tmp_path: Path) -> None:
    """Verifies that ImportResolver correctly maps relative and absolute module paths."""
    handle = create_synthetic_fixture_repo(tmp_path)
    resolver = ImportResolver(handle.path)

    # Absolute lookups
    assert resolver.resolve_import("tests/test_client.py", module_name="pkg.service") == "src/pkg/service.py"
    assert resolver.resolve_import("tests/test_client.py", module_name="pkg.client") == "src/pkg/client.py"

    # Relative lookup: from .service in client.py
    assert (
        resolver.resolve_import("src/pkg/client.py", module_name="service", level=1)
        == "src/pkg/service.py"
    )

    # External/stdlib imports should return None
    assert resolver.resolve_import("src/pkg/client.py", module_name="os", level=0) is None
    assert resolver.resolve_import("src/pkg/client.py", module_name="pytest", level=0) is None

    # Candidate internal classification
    assert resolver.is_internal_candidate("pkg.service", level=0) is True
    assert resolver.is_internal_candidate("os", level=0) is False
    assert resolver.is_internal_candidate(None, level=1) is True


def test_structural_extractor_3_fixtures(tmp_path: Path) -> None:
    """Verifies AST parsing, node extraction, and edge creation across 3 fixture files."""
    handle = create_synthetic_fixture_repo(tmp_path)
    extractor = StructuralExtractor(handle)
    artifacts, edges, stats = extractor.extract()

    # 1. Check Artifact counts
    # Repository (1), Files (4: __init__, service, client, test_client), Classes (2), Functions (4)
    file_artifacts = [a for a in artifacts if a.type == "File"]
    class_artifacts = [a for a in artifacts if a.type == "Class"]
    func_artifacts = [a for a in artifacts if a.type == "Function"]

    assert stats.num_files == 4
    assert len(file_artifacts) == 4
    assert stats.num_classes == 2
    assert len(class_artifacts) == 2
    assert stats.num_functions == 4
    assert len(func_artifacts) == 4

    # Check is_test property
    test_files = [f for f in file_artifacts if f.properties.get("is_test")]
    assert len(test_files) == 1
    assert test_files[0].path == "tests/test_client.py"

    # 2. Check IMPORTS edges
    import_edges = [e for e in edges if e.type == "IMPORTS"]
    assert len(import_edges) >= 2

    # client.py IMPORTS service.py
    client_imports_service = any(
        e.src.endswith("src/pkg/client.py") and e.dst.endswith("src/pkg/service.py")
        for e in import_edges
    )
    assert client_imports_service, "client.py must import service.py"

    # test_client.py IMPORTS client.py
    test_imports_client = any(
        e.src.endswith("tests/test_client.py") and e.dst.endswith("src/pkg/client.py")
        for e in import_edges
    )
    assert test_imports_client, "test_client.py must import client.py"

    # 3. Check CALLS edges
    call_edges = [e for e in edges if e.type == "CALLS"]
    # Service.run CALLS helper
    service_run_calls_helper = any(
        "Service.run" in e.src and "helper" in e.dst
        for e in call_edges
    )
    assert service_run_calls_helper, "Service.run must call helper"

    # Client.invoke CALLS helper (cross-file imported call)
    client_calls_helper = any(
        "Client.invoke" in e.src and "helper" in e.dst
        for e in call_edges
    )
    assert client_calls_helper, "Client.invoke must call imported helper"

    # 4. Check DEPENDS_ON edges
    dep_edges = [e for e in edges if e.type == "DEPENDS_ON"]
    assert any(
        e.src.endswith("src/pkg/client.py") and e.dst.endswith("src/pkg/service.py")
        for e in dep_edges
    )

    # 5. Check provenance properties on all edges
    for e in edges:
        assert e.confidence == 1.0
        assert e.method == "ast"
        assert e.source_commit == handle.head_sha
        assert e.is_deterministic is True
        assert e.timestamp is not None and e.timestamp > 0

    # 6. Check resolution rate (all internal candidate imports resolved = 100%)
    assert stats.resolved_import_rate == 100.0


def test_neo4j_batch_storage(tmp_path: Path) -> None:
    """Verifies that extracted nodes and edges are persisted to Neo4j with correct schema."""
    from neo4j import GraphDatabase

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        pytest.skip(f"Neo4j service unreachable at {NEO4J_URI}: {e}")

    handle = create_synthetic_fixture_repo(tmp_path)
    extractor = StructuralExtractor(handle)
    artifacts, edges, stats = extractor.extract()

    with Neo4jStore() as store:
        store.ensure_schema()
        store.clear_repo(handle.name)

        saved_nodes = store.save_artifacts(artifacts)
        saved_edges = store.save_edges(edges)
        assert saved_nodes == len(artifacts)
        assert saved_edges == len(edges)

        db_stats = store.get_repo_stats(handle.name)
        assert db_stats["total_nodes"] == len(artifacts)
        assert db_stats["total_edges"] == len(edges)
        assert "File" in db_stats["nodes"]
        assert "Function" in db_stats["nodes"]
        assert "IMPORTS" in db_stats["edges"]

        # DoD query verification: MATCH (f:File)-[:IMPORTS]->(g:File)
        sample = store.get_sample_imports(handle.name, limit=10)
        assert len(sample) >= 2

        # Cleanup
        store.clear_repo(handle.name)
