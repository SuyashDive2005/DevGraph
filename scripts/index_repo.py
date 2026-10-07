#!/usr/bin/env python3
"""
Repository Indexing CLI for DevGraph.

Why this script exists:
Provides the primary CLI entrypoint to run ingestion, structural extraction,
and knowledge graph construction across candidate repositories. Supports stages
'ingest', 'structural', and 'all'.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devgraph.config import ensure_data_dirs
from devgraph.extraction.structural import StructuralExtractor
from devgraph.graph.neo4j_store import Neo4jStore
from devgraph.ingestion.clone import clone
from devgraph.ingestion.github_meta import fetch_github_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DevGraph Repository Indexer - Ingestion & Knowledge Graph Construction"
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Git repository URL or GitHub 'owner/repo' shorthand (e.g. pallets/click)",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["ingest", "structural", "all"],
        default="all",
        help="Pipeline stage to execute: 'ingest', 'structural', or 'all' (default: 'all')",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=300,
        help="Maximum number of issues to fetch from GitHub API (default: 300)",
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=300,
        help="Maximum number of pull requests to fetch from GitHub API (default: 300)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetching GitHub metadata bypassing disk cache",
    )
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Skip persisting extracted nodes and edges to Neo4j",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()

    print(f"=== DevGraph Indexer: Target={args.url} (Stage: {args.stage}) ===")

    # Always obtain repo handle (clones if needed, otherwise opens local)
    handle = clone(args.url)

    # 1. Ingestion stage
    if args.stage in ("ingest", "all"):
        print("\n[Stage 1: INGESTION]")
        print(f"-> Repository checkout: {handle.path}")
        print(f"   ✓ Pinned HEAD SHA:   {handle.head_sha}")

        print(f"-> Fetching GitHub metadata (up to {args.max_issues} issues, {args.max_prs} PRs)...")
        try:
            meta = fetch_github_metadata(
                repo_identifier=args.url,
                max_issues=args.max_issues,
                max_prs=args.max_prs,
                force_refresh=args.force,
            )
            print(f"   ✓ Loaded {meta['issue_count']} issues and {meta['pr_count']} PRs")
            print(f"   ✓ GitHub JSON cached for {meta['repo']}")
        except Exception as e:
            print(f"   ! GitHub metadata warning/error: {e}")
            print("   (Note: If rate limited, please set GITHUB_TOKEN in .env)")

        print("✓ Ingestion stage completed.")

    # 2. Structural extraction stage
    if args.stage in ("structural", "all"):
        print("\n[Stage 2: STRUCTURAL EXTRACTION]")
        print(f"-> Parsing AST with Tree-sitter for '{handle.name}'...")
        extractor = StructuralExtractor(handle)
        artifacts, edges, stats = extractor.extract()

        print("\n--- Structural Extraction Statistics ---")
        print(f"   # Files:                     {stats.num_files}")
        print(f"   # Classes:                   {stats.num_classes}")
        print(f"   # Functions:                 {stats.num_functions}")
        print(f"   # CONTAINS edges:            {stats.num_contains}")
        print(f"   # DEFINES edges:             {stats.num_defines}")
        print(f"   # IMPORTS edges:             {stats.num_imports}")
        print(f"   # CALLS edges:               {stats.num_calls}")
        print(f"   # DEPENDS_ON edges:          {stats.num_depends_on}")
        print(f"   Total raw imports parsed:    {stats.total_raw_imports}")
        print(f"   Internal candidate imports:  {stats.internal_candidate_imports}")
        print(f"   Resolved internal imports:   {stats.resolved_internal_imports}")
        print(f"   % Imports resolved:          {stats.resolved_import_rate:.2f}%")

        if not args.skip_neo4j:
            print("\n-> Persisting knowledge graph to Neo4j...")
            try:
                with Neo4jStore() as store:
                    store.ensure_schema()
                    store.clear_repo(handle.name)
                    saved_artifacts = store.save_artifacts(artifacts)
                    saved_edges = store.save_edges(edges)
                    repo_stats = store.get_repo_stats(handle.name)
                    print(f"   ✓ Saved {saved_artifacts} nodes to Neo4j")
                    print(f"   ✓ Saved {saved_edges} edges to Neo4j")
                    print(f"   ✓ Graph nodes in DB: {repo_stats['nodes']}")
                    print(f"   ✓ Graph edges in DB: {repo_stats['edges']}")
            except Exception as e:
                print(f"   ! Neo4j write failed: {e}")
                print("   (Check docker container 'devgraph-neo4j' status)")
        else:
            print("\n-> Skipped Neo4j persistence (--skip-neo4j enabled).")

        print("\n✓ Structural extraction stage completed.")

    print("\n=== Indexing completed successfully ===")


if __name__ == "__main__":
    main()
