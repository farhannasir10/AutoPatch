"""Talk to Gemini Flash — free tier via Google AI Studio.

Uses plain REST + httpx. The google-genai / LangChain clients either hung
or buried useful errors for this key; REST stays predictable for demos.
"""

from __future__ import annotations

import os
import time

import httpx

from app.services.diff_utils import extract_code_block


def generate_patch(
    *,
    source_code: str,
    test_code: str,
    error_log: str,
    iteration: int,
    source_file: str = "impl.py",
    language: str = "python",
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing — grab one free from Google AI Studio")

    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    fence = "typescript" if language in {"typescript", "ts", "tsx"} else (
        "javascript" if language in {"javascript", "js"} else "python"
    )

    prompt = f"""You are AutoPatch, an autonomous code remediation agent.
You fix bugs so unit tests pass.
Rules:
- Return ONLY the full corrected contents of {source_file}
- Do not rewrite the test file
- Prefer the smallest correct change
- No markdown commentary outside a single ```{fence} block

Iteration: {iteration}

## {source_file} (current)
```{fence}
{source_code}
```

## tests (do not modify)
```{fence}
{test_code}
```

## Latest test failure
```
{error_log or "(no log yet — tests have not been run)"}
```

Return the fixed {source_file} now.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    last_err = ""
    for attempt in range(4):
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                if not text:
                    raise RuntimeError(f"Empty Gemini response: {data!r}")
                return extract_code_block(text, language)
            last_err = f"{resp.status_code} {resp.text[:300]}"
            if resp.status_code in {429, 503} and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini error: {last_err}")
        except httpx.HTTPError as exc:
            last_err = str(exc)
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini request failed: {last_err}") from exc

    raise RuntimeError(f"Gemini failed after retries: {last_err}")
