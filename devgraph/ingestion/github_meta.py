"""
GitHub metadata retrieval (issues and pull requests) for DevGraph.

Why this module exists:
Fetches issues and PRs via the GitHub REST API, paginating up to ~300 items each,
extracting necessary metadata for traceability and semantic link extraction.
Caches results to disk so subsequent runs avoid API calls and rate limits.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

from devgraph.config import GITHUB_DIR, GITHUB_TOKEN, ensure_data_dirs

logger = logging.getLogger(__name__)


def parse_owner_repo(repo_identifier: str) -> Tuple[str, str]:
    """
    Extracts (owner, repo) from a URL or shorthand string.
    Examples:
      'pallets/click' -> ('pallets', 'click')
      'https://github.com/psf/requests.git' -> ('psf', 'requests')
    """
    clean = repo_identifier.strip().rstrip("/")
    if clean.endswith(".git"):
        clean = clean[:-4]

    # Match https://github.com/owner/repo or git@github.com:owner/repo
    m = re.search(r"github\.com[/:]([\w-]+)/([\w.-]+)", clean)
    if m:
        return m.group(1), m.group(2)

    parts = clean.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]

    raise ValueError(f"Cannot parse GitHub owner and repository name from: {repo_identifier}")


def _check_rate_limit(resp: requests.Response) -> None:
    """Logs rate-limit information and checks if quota is exhausted."""
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        try:
            rem_val = int(remaining)
            if rem_val <= 2:
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait_secs = max(0, reset_ts - int(time.time()))
                logger.warning(
                    "GitHub API rate limit nearly exhausted (%d remaining). Reset in %d seconds.",
                    rem_val,
                    wait_secs,
                )
        except ValueError:
            pass


def fetch_github_metadata(
    repo_identifier: str,
    token: Optional[str] = None,
    max_issues: int = 300,
    max_prs: int = 300,
    output_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Fetches up to max_issues and max_prs for a repository and caches the JSON on disk.

    Args:
        repo_identifier: 'owner/repo' or GitHub URL.
        token: Optional GitHub personal access token (falls back to GITHUB_TOKEN from env).
        max_issues: Maximum number of issues to fetch.
        max_prs: Maximum number of pull requests to fetch.
        output_dir: Target directory (defaults to data/github).
        force_refresh: If True, bypass disk cache and re-fetch from API.

    Returns:
        Dictionary containing metadata, issues, and pull requests.
    """
    ensure_data_dirs()
    owner, repo_name = parse_owner_repo(repo_identifier)

    target_dir = Path(output_dir) if output_dir else GITHUB_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_path = target_dir / f"{repo_name}.json"

    if cache_path.exists() and not force_refresh:
        logger.info("Loading cached GitHub metadata from %s", cache_path)
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    auth_token = token if token is not None else GITHUB_TOKEN
    headers: Dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DevGraph-Ingest/1.0",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    session = requests.Session()
    session.headers.update(headers)

    # 1. Fetch Pull Requests
    pull_requests: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while len(pull_requests) < max_prs:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        params = {"state": "all", "per_page": per_page, "page": page, "sort": "created", "direction": "desc"}
        resp = session.get(url, params=params, timeout=30)
        _check_rate_limit(resp)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise RuntimeError(
                f"GitHub API rate limit exceeded while fetching PRs. "
                f"Please provide a GITHUB_TOKEN in .env or pass token=...: {resp.text}"
            )
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub API error ({resp.status_code}) fetching PRs: {resp.text}")

        data = resp.json()
        if not data:
            break

        for item in data:
            if len(pull_requests) >= max_prs:
                break
            labels = [lb["name"] for lb in item.get("labels", []) if isinstance(lb, dict)]
            pull_requests.append({
                "number": item.get("number"),
                "title": item.get("title", ""),
                "body": item.get("body") or "",
                "created_at": item.get("created_at"),
                "closed_at": item.get("closed_at"),
                "merged_at": item.get("merged_at"),
                "state": item.get("state"),
                "labels": labels,
            })

        if len(data) < per_page:
            break
        page += 1

    # 2. Fetch Issues (excluding items that are PRs)
    issues: List[Dict[str, Any]] = []
    page = 1

    while len(issues) < max_issues:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
        params = {"state": "all", "per_page": per_page, "page": page, "sort": "created", "direction": "desc"}
        resp = session.get(url, params=params, timeout=30)
        _check_rate_limit(resp)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise RuntimeError(
                f"GitHub API rate limit exceeded while fetching issues. "
                f"Please provide a GITHUB_TOKEN in .env or pass token=...: {resp.text}"
            )
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub API error ({resp.status_code}) fetching issues: {resp.text}")

        data = resp.json()
        if not data:
            break

        for item in data:
            # GitHub issues endpoint includes pull requests; filter them out
            if "pull_request" in item:
                continue
            if len(issues) >= max_issues:
                break
            labels = [lb["name"] for lb in item.get("labels", []) if isinstance(lb, dict)]
            issues.append({
                "number": item.get("number"),
                "title": item.get("title", ""),
                "body": item.get("body") or "",
                "created_at": item.get("created_at"),
                "closed_at": item.get("closed_at"),
                "state": item.get("state"),
                "labels": labels,
            })

        if len(data) < per_page:
            break
        page += 1

    result_data: Dict[str, Any] = {
        "repo": f"{owner}/{repo_name}",
        "repo_name": repo_name,
        "owner": owner,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "issue_count": len(issues),
        "pr_count": len(pull_requests),
        "issues": issues,
        "pull_requests": pull_requests,
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    logger.info("Saved %d issues and %d PRs to %s", len(issues), len(pull_requests), cache_path)
    return result_data
