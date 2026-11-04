"""Write the approved patch and make a local commit inside the run workspace."""

from __future__ import annotations

import subprocess
from pathlib import Path


def commit_patch(workspace: Path, message: str, paths: list[str] | None = None) -> str:
    """Init a tiny git repo if needed, then commit. Returns the short SHA."""
    workspace.mkdir(parents=True, exist_ok=True)
    paths = paths or ["impl.py", "test_impl.py"]

    def git(*args: str) -> str:
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

    if not (workspace / ".git").exists():
        git("init")
        # identity only for this throwaway repo — don't touch global git config
        git("config", "user.email", "autopatch@local.dev")
        git("config", "user.name", "AutoPatch")

    existing = [p for p in paths if (workspace / p).exists()]
    if existing:
        git("add", *existing)
    else:
        git("add", "-A")

    status = git("status", "--porcelain")
    if not status:
        return "no-change"

    git("commit", "-m", message)
    return git("rev-parse", "--short", "HEAD")
