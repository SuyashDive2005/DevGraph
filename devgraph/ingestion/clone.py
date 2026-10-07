"""
Repository cloning and SHA pinning for DevGraph.

Why this module exists:
Implements deterministic ingestion of Git repositories with full commit history
(no shallow clones) and records the current HEAD commit SHA. Pinning the commit SHA
is essential for evaluation reproducibility and for preventing temporal leakage.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
import git

from devgraph.config import REPOS_DIR, ensure_data_dirs
from devgraph.models import RepoHandle


def normalize_repo_url(url: str) -> str:
    """
    Normalizes a repository URL or GitHub shorthand 'owner/repo' into a full clone URL.
    """
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://") or url.startswith("git@"):
        return url
    # Matches GitHub shorthand e.g. 'pallets/click'
    if re.match(r"^[\w-]+/[\w.-]+$", url):
        return f"https://github.com/{url}.git"
    return url


def extract_repo_name(url: str) -> str:
    """
    Extracts the canonical repository short name from a Git URL or GitHub shorthand.
    Example: 'https://github.com/pallets/click.git' -> 'click'
    """
    clean_url = url.strip().rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    parts = clean_url.split("/")
    return parts[-1]


def clone(
    url: str,
    dest_dir: Optional[Path] = None,
    target_sha: Optional[str] = None,
) -> RepoHandle:
    """
    Clones a Git repository with full history (no depth limit) or opens it if already present.

    Args:
        url: Remote repository URL or GitHub 'owner/repo' shorthand.
        dest_dir: Optional custom destination path. Defaults to data/repos/{repo_name}.
        target_sha: Optional commit SHA to checkout and pin to.

    Returns:
        RepoHandle with path, pinned HEAD SHA, repo name, and source URL.
    """
    ensure_data_dirs()
    normalized_url = normalize_repo_url(url)
    repo_name = extract_repo_name(url)

    if dest_dir is None:
        dest_dir = REPOS_DIR / repo_name
    dest_dir = Path(dest_dir).resolve()

    if (dest_dir / ".git").exists():
        repo = git.Repo(dest_dir)
    else:
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        # Clone full history (no depth) for evolution mining
        repo = git.Repo.clone_from(normalized_url, dest_dir)

    if target_sha:
        repo.git.checkout(target_sha)

    head_sha = repo.head.commit.hexsha

    return RepoHandle(
        path=dest_dir,
        head_sha=head_sha,
        name=repo_name,
        url=normalized_url,
    )
