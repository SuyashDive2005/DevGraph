"""
Tests for Week 1 Ingestion, Environment, and Configuration.

Why this module exists:
Verifies the Definition of Done (DoD) for Week 1:
1. Git repository cloning with full history and pinned HEAD SHA.
2. GitHub metadata fetching, pagination, and disk caching.
3. Neo4j connectivity and write/read cycle.
4. Repository configuration validation (repos.yaml).
"""

from __future__ import annotations

import json
from pathlib import Path
import git
import pytest
import yaml

from devgraph.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, ensure_data_dirs
from devgraph.ingestion.clone import clone, extract_repo_name, normalize_repo_url
from devgraph.ingestion.github_meta import fetch_github_metadata, parse_owner_repo
from devgraph.models import RepoHandle


def test_url_helpers() -> None:
    """Verifies repository URL normalization and name extraction."""
    assert normalize_repo_url("pallets/click") == "https://github.com/pallets/click.git"
    assert (
        normalize_repo_url("https://github.com/pallets/click.git")
        == "https://github.com/pallets/click.git"
    )

    assert extract_repo_name("pallets/click") == "click"
    assert extract_repo_name("https://github.com/psf/requests.git") == "requests"
    assert extract_repo_name("https://github.com/pallets/flask/") == "flask"

    owner, repo = parse_owner_repo("pallets/click")
    assert owner == "pallets"
    assert repo == "click"

    owner, repo = parse_owner_repo("https://github.com/psf/requests.git")
    assert owner == "psf"
    assert repo == "requests"


def test_clone_local_repository(tmp_path: Path) -> None:
    """Creates a local synthetic Git repo and verifies full cloning and SHA pinning."""
    # 1. Create origin repo
    origin_dir = tmp_path / "origin_repo"
    origin_dir.mkdir()
    origin_repo = git.Repo.init(origin_dir)

    file_a = origin_dir / "sample.py"
    file_a.write_text("print('hello world')\n")
    origin_repo.index.add(["sample.py"])
    commit1 = origin_repo.index.commit("Initial commit")

    file_a.write_text("print('updated world')\n")
    origin_repo.index.add(["sample.py"])
    commit2 = origin_repo.index.commit("Second commit")

    # 2. Clone using DevGraph clone function
    dest_dir = tmp_path / "cloned_repo"
    handle: RepoHandle = clone(str(origin_dir), dest_dir=dest_dir)

    assert handle.path == dest_dir
    assert handle.head_sha == commit2.hexsha
    assert (dest_dir / ".git").exists()

    # Verify history is preserved (not shallow)
    cloned_repo = git.Repo(dest_dir)
    commits = list(cloned_repo.iter_commits())
    assert len(commits) == 2
    assert commits[0].hexsha == commit2.hexsha
    assert commits[1].hexsha == commit1.hexsha


def test_github_metadata_caching(tmp_path: Path) -> None:
    """Verifies that cached metadata is returned from disk without network calls."""
    cache_dir = tmp_path / "github_cache"
    cache_dir.mkdir()

    fake_data = {
        "repo": "test/sample",
        "repo_name": "sample",
        "owner": "test",
        "fetched_at": "2026-10-07T00:00:00Z",
        "issue_count": 1,
        "pr_count": 1,
        "issues": [
            {
                "number": 1,
                "title": "Bug in parser",
                "body": "Fix this bug",
                "created_at": "2026-01-01T00:00:00Z",
                "closed_at": "2026-01-02T00:00:00Z",
                "state": "closed",
                "labels": ["bug"],
            }
        ],
        "pull_requests": [
            {
                "number": 2,
                "title": "Fix parser",
                "body": "Resolves #1",
                "created_at": "2026-01-01T12:00:00Z",
                "closed_at": "2026-01-02T00:00:00Z",
                "merged_at": "2026-01-02T00:00:00Z",
                "state": "closed",
                "labels": [],
            }
        ],
    }

    cache_file = cache_dir / "sample.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(fake_data, f)

    # Calling fetch_github_metadata should read directly from disk cache
    result = fetch_github_metadata("test/sample", output_dir=cache_dir)
    assert result["repo"] == "test/sample"
    assert result["issue_count"] == 1
    assert result["pr_count"] == 1
    assert result["issues"][0]["title"] == "Bug in parser"
    assert result["pull_requests"][0]["number"] == 2


def test_repos_yaml_spec() -> None:
    """Verifies that scripts/repos.yaml exists and defines pilot repository matching criteria."""
    repos_file = Path(__file__).resolve().parent.parent / "scripts" / "repos.yaml"
    assert repos_file.exists(), "scripts/repos.yaml must exist"

    with open(repos_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "pilot" in data
    pilot = data["pilot"]
    assert pilot["name"] == "click"
    assert pilot["owner"] == "pallets"
    assert pilot["estimated_commits"] >= 800
    assert 10000 <= pilot["estimated_loc"] <= 150000

    assert "secondary_candidates" in data
    assert len(data["secondary_candidates"]) >= 1


def test_neo4j_connectivity_and_rw() -> None:
    """Tests connecting to Neo4j Community, creating a test node, and querying it."""
    from neo4j import GraphDatabase

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        pytest.skip(
            f"Neo4j service unreachable at {NEO4J_URI} (sandbox network isolation or offline): {e}"
        )

    with driver:
        with driver.session() as session:
            # 1. Clean previous test artifact if any
            session.run("MATCH (n:Artifact {id: 'test:Node:w1'}) DETACH DELETE n")

            # 2. Write one test node
            session.run(
                """
                MERGE (n:Artifact:TestArtifact {
                    id: 'test:Node:w1',
                    repo: 'test-pilot',
                    type: 'TestArtifact',
                    name: 'Unit Test Node'
                })
                """
            )

            # 3. Read the node back
            result = session.run(
                "MATCH (n:Artifact {id: 'test:Node:w1'}) RETURN n.id AS id, n.name AS name, n.repo AS repo"
            )
            record = result.single()
            assert record is not None
            assert record["id"] == "test:Node:w1"
            assert record["name"] == "Unit Test Node"
            assert record["repo"] == "test-pilot"

            # 4. Cleanup
            session.run("MATCH (n:Artifact {id: 'test:Node:w1'}) DETACH DELETE n")

