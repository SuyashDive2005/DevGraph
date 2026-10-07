#!/usr/bin/env python3
"""
Repository Indexing CLI for DevGraph.

Why this script exists:
Provides the primary CLI entrypoint to run ingestion, extraction, and indexing
stages across candidate repositories. In Week 1, supports the '--stage ingest' workflow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devgraph.config import ensure_data_dirs
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
        choices=["ingest", "all"],
        default="ingest",
        help="Pipeline stage to execute (Week 1 implements 'ingest')",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()

    print(f"=== DevGraph Indexer: Target={args.url} (Stage: {args.stage}) ===")

    if args.stage in ("ingest", "all"):
        print("\n[Stage 1/1: INGESTION]")
        print(f"-> Cloning repository from {args.url} (full history)...")
        handle = clone(args.url)
        print(f"   ✓ Repository cloned to: {handle.path}")
        print(f"   ✓ Pinned HEAD SHA:     {handle.head_sha}")

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

        print("\n=== Ingestion stage completed successfully ===")


if __name__ == "__main__":
    main()
