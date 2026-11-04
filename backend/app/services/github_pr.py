"""Optional GitHub PR open after HITL approve — local commit still always happens."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx


def _git(workspace: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git failed")
    return result.stdout.strip()


def try_open_pull_request(
    workspace: Path,
    *,
    run_id: str,
    fixture_id: str,
    title: str,
    body: str,
    source_file: str,
) -> str | None:
    """Push a branch + open a PR when GITHUB_TOKEN + GITHUB_REPOSITORY are set.

    Returns the PR HTML URL, or None if we're staying local-only.
    """
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")  # owner/name
    if not token or not repo:
        return None

    base = os.getenv("GITHUB_PR_BASE", "main")
    branch = f"autopatch/{fixture_id}-{run_id}"

    # branch from current HEAD inside the run workspace
    _git(workspace, "checkout", "-B", branch)
    _git(workspace, "add", source_file)
    status = _git(workspace, "status", "--porcelain")
    if status:
        _git(workspace, "commit", "-m", title)

    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    # don't print the token if push fails — raise a scrubbed error
    push = subprocess.run(
        ["git", "push", "-u", remote, branch, "--force"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if push.returncode != 0:
        err = (push.stderr or push.stdout).replace(token, "***")
        raise RuntimeError(f"git push failed: {err.strip()}")

    api = f"https://api.github.com/repos/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"title": title, "head": branch, "base": base, "body": body}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(api, headers=headers, json=payload)
    if resp.status_code >= 300:
        raise RuntimeError(f"GitHub PR API {resp.status_code}: {resp.text[:400]}")
    return resp.json().get("html_url")
