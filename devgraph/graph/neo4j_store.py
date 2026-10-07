"""
Neo4j knowledge graph storage for DevGraph.

Why this module exists:
Manages connections to Neo4j Community Edition, enforces graph schema constraints
(unique artifact ID, repo index, path index), and executes high-throughput batched
UNWIND MERGE operations for nodes and edges while preserving provenance metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set
from neo4j import GraphDatabase, Driver

from devgraph.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from devgraph.models import Artifact, Edge

logger = logging.getLogger(__name__)

ALLOWED_NODE_TYPES: Set[str] = {
    "Repository",
    "File",
    "Class",
    "Function",
    "DocSection",
    "Commit",
    "Issue",
    "PullRequest",
    "Requirement",
    "TestArtifact",
}

ALLOWED_EDGE_TYPES: Set[str] = {
    "CONTAINS",
    "DEFINES",
    "IMPORTS",
    "CALLS",
    "DEPENDS_ON",
    "MODIFIES",
    "FIXES",
    "CO_CHANGED_WITH",
    "VERIFIES",
    "DOCUMENTS",
    "IMPLEMENTS",
}


class Neo4jStore:
    """
    Batch writer and query manager for DevGraph knowledge graph in Neo4j.
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def verify_connectivity(self) -> None:
        """Verifies connection to the Neo4j instance."""
        self.driver.verify_connectivity()

    def close(self) -> None:
        """Closes the Neo4j driver connection pool."""
        self.driver.close()

    def __enter__(self) -> Neo4jStore:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def ensure_schema(self) -> None:
        """
        Creates mandatory constraints and indexes in Neo4j according to Section 7.3.
        """
        statements = [
            "CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (n:Artifact) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX artifact_repo IF NOT EXISTS FOR (n:Artifact) ON (n.repo)",
            "CREATE INDEX artifact_path IF NOT EXISTS FOR (n:Artifact) ON (n.path)",
        ]
        with self.driver.session() as session:
            for stmt in statements:
                session.run(stmt)
        logger.info("Ensured Neo4j schema constraints and indexes.")

    def clear_repo(self, repo_name: str) -> int:
        """
        Deletes all artifacts and incident edges associated with a specific repository.

        Returns:
            Count of deleted nodes.
        """
        cypher = """
        MATCH (n:Artifact {repo: $repo})
        DETACH DELETE n
        RETURN count(n) AS deleted
        """
        with self.driver.session() as session:
            result = session.run(cypher, repo=repo_name)
            record = result.single()
            deleted = record["deleted"] if record else 0
        logger.info("Deleted %d existing nodes for repo '%s'", deleted, repo_name)
        return deleted

    def save_artifacts(self, artifacts: List[Artifact], batch_size: int = 1000) -> int:
        """
        Batches and merges Artifact nodes into Neo4j.
        Nodes are grouped by type label to apply dual labels (:Artifact:<Type>).

        Returns:
            Total count of saved artifacts.
        """
        if not artifacts:
            return 0

        # Group artifacts by type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for a in artifacts:
            node_type = a.type if a.type in ALLOWED_NODE_TYPES else "Artifact"
            props: Dict[str, Any] = {
                "id": a.id,
                "repo": a.repo,
                "type": a.type,
                "name": a.name,
                "path": a.path,
                "created_at": a.created_at,
            }
            # Flatten extra properties
            for k, v in a.properties.items():
                if v is not None:
                    props[k] = v

            row = {"id": a.id, "props": props}
            by_type.setdefault(node_type, []).append(row)

        saved_total = 0
        with self.driver.session() as session:
            for node_type, rows in by_type.items():
                cypher = f"""
                UNWIND $rows AS r
                MERGE (n:Artifact:{node_type} {{id: r.id}})
                SET n += r.props
                """
                for i in range(0, len(rows), batch_size):
                    chunk = rows[i : i + batch_size]
                    session.run(cypher, rows=chunk)
                    saved_total += len(chunk)

        logger.info("Saved %d artifacts to Neo4j.", saved_total)
        return saved_total

    def save_edges(self, edges: List[Edge], batch_size: int = 1000) -> int:
        """
        Batches and merges Edge relationships with provenance properties into Neo4j.
        Edges are grouped by relationship type.

        Returns:
            Total count of saved edges.
        """
        if not edges:
            return 0

        # Group edges by type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for e in edges:
            if e.type not in ALLOWED_EDGE_TYPES:
                logger.warning("Skipping edge with unrecognized type: %s", e.type)
                continue

            props: Dict[str, Any] = {
                "confidence": e.confidence,
                "method": e.method,
                "source_commit": e.source_commit,
                "timestamp": e.timestamp,
                "is_deterministic": e.is_deterministic,
            }
            for k, v in e.properties.items():
                if v is not None:
                    props[k] = v

            row = {
                "src": e.src,
                "dst": e.dst,
                "props": props,
            }
            by_type.setdefault(e.type, []).append(row)

        saved_total = 0
        with self.driver.session() as session:
            for rel_type, rows in by_type.items():
                cypher = f"""
                UNWIND $rows AS r
                MATCH (a:Artifact {{id: r.src}})
                MATCH (b:Artifact {{id: r.dst}})
                MERGE (a)-[e:{rel_type}]->(b)
                SET e += r.props
                """
                for i in range(0, len(rows), batch_size):
                    chunk = rows[i : i + batch_size]
                    session.run(cypher, rows=chunk)
                    saved_total += len(chunk)

        logger.info("Saved %d edges to Neo4j.", saved_total)
        return saved_total

    def get_repo_stats(self, repo_name: str) -> Dict[str, Any]:
        """
        Queries Neo4j for node counts by type and edge counts by relationship type.
        """
        stats: Dict[str, Any] = {"nodes": {}, "edges": {}, "total_nodes": 0, "total_edges": 0}
        with self.driver.session() as session:
            # Nodes
            node_res = session.run(
                "MATCH (n:Artifact {repo: $repo}) RETURN n.type AS type, count(n) AS count",
                repo=repo_name,
            )
            for rec in node_res:
                t = rec["type"] or "Unknown"
                c = rec["count"]
                stats["nodes"][t] = c
                stats["total_nodes"] += c

            # Edges
            edge_res = session.run(
                """
                MATCH (a:Artifact {repo: $repo})-[r]->(b:Artifact {repo: $repo})
                RETURN type(r) AS type, count(r) AS count
                """,
                repo=repo_name,
            )
            for rec in edge_res:
                t = rec["type"]
                c = rec["count"]
                stats["edges"][t] = c
                stats["total_edges"] += c

        return stats

    def get_sample_imports(self, repo_name: str, limit: int = 50) -> List[Dict[str, str]]:
        """
        Queries sample file-to-file IMPORTS edges for inspection and DoD verification.
        """
        cypher = """
        MATCH (f:File {repo: $repo})-[:IMPORTS]->(g:File {repo: $repo})
        RETURN f.path AS src, g.path AS dst
        LIMIT $limit
        """
        results: List[Dict[str, str]] = []
        with self.driver.session() as session:
            for rec in session.run(cypher, repo=repo_name, limit=limit):
                results.append({"src": rec["src"], "dst": rec["dst"]})
        return results
