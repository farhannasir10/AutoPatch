"""Tiny diff helpers — keep the Monaco pane honest."""

from __future__ import annotations

import difflib
import re


def unified_diff(before: str, after: str, path: str = "impl.py") -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    # make sure trailing newline doesn't create noisy diffs
    if before_lines and not before_lines[-1].endswith("\n"):
        before_lines[-1] += "\n"
    if after_lines and not after_lines[-1].endswith("\n"):
        after_lines[-1] += "\n"
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def extract_code_block(text: str, language: str | None = None) -> str:
    """Pull a fenced code block out of a model reply if present."""
    fence = "```"
    if fence not in text:
        return text.strip()

    parts = text.split(fence)
    preferred = (language or "").lower()
    aliases = {
        "python": ("python", "py"),
        "typescript": ("typescript", "ts", "tsx"),
        "javascript": ("javascript", "js", "jsx"),
    }
    want = aliases.get(preferred, (preferred,) if preferred else ())

    fallback = None
    for i, chunk in enumerate(parts):
        if i % 2 != 1:
            continue
        body = chunk
        header = body.lstrip().split("\n", 1)[0].strip().lower()
        rest = body
        if re.match(r"^[a-z0-9_+-]+\s*$", header.split()[0] if header else ""):
            lang_tag = header.split()[0] if header else ""
            rest = body.lstrip()[len(lang_tag) :] if lang_tag else body
            if want and lang_tag in want:
                return rest.strip("\n").strip()
            if not want and lang_tag:
                fallback = rest.strip("\n").strip()
                continue
        candidate = rest.strip("\n").strip()
        if want:
            fallback = fallback or candidate
        else:
            return candidate
    return fallback or text.strip()


# backwards-compatible name used by older call sites
def extract_python_block(text: str) -> str:
    return extract_code_block(text, "python")
