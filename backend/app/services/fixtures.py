"""Load canned buggy samples — Python toys + the Next.js CI-style sample."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = ROOT / "fixtures"
SAMPLES_DIR = ROOT / "samples"


@dataclass
class FixtureSpec:
    id: str
    label: str
    description: str
    runtime: str  # python | node
    source_file: str
    test_file: str
    language: str
    root: Path
    test_command: list[str]


def _python_blurb(fixture_id: str) -> str:
    blurbs = {
        "off_by_one": "sum_to_n misses the last integer — classic range bug",
        "wrong_return": "palindrome check compares cleaned vs raw string",
        "missing_import": "uses statistics.mean without importing it",
        "type_coercion": "parse_ints returns strings instead of ints",
        "fizzbuzz_bug": "FizzBuzz checks %15 after %3/%5 so FizzBuzz never wins",
    }
    return blurbs.get(fixture_id, "Intentionally broken Python sample")


def _load_sample_specs() -> list[FixtureSpec]:
    specs: list[FixtureSpec] = []
    if not SAMPLES_DIR.exists():
        return specs
    for meta in sorted(SAMPLES_DIR.glob("*/fixture.json")):
        data = json.loads(meta.read_text(encoding="utf-8"))
        root = meta.parent
        specs.append(
            FixtureSpec(
                id=data["id"],
                label=data.get("label", data["id"]),
                description=data.get("description", ""),
                runtime=data.get("runtime", "node"),
                source_file=data["source_file"],
                test_file=data.get("test_file", ""),
                language=data.get("language", "typescript"),
                root=root,
                test_command=list(data.get("test_command") or ["npm", "test"]),
            )
        )
    return specs


def _load_python_specs() -> list[FixtureSpec]:
    specs: list[FixtureSpec] = []
    if not FIXTURES_DIR.exists():
        return specs
    for path in sorted(FIXTURES_DIR.iterdir()):
        if path.is_dir() and (path / "impl.py").exists() and (path / "test_impl.py").exists():
            specs.append(
                FixtureSpec(
                    id=path.name,
                    label=path.name.replace("_", " ").title(),
                    description=_python_blurb(path.name),
                    runtime="python",
                    source_file="impl.py",
                    test_file="test_impl.py",
                    language="python",
                    root=path,
                    test_command=["python", "-m", "pytest", "-q", "--tb=short"],
                )
            )
    return specs


def all_specs() -> list[FixtureSpec]:
    # Next.js sample first — that's the "real codebase" talking point
    return _load_sample_specs() + _load_python_specs()


def get_spec(fixture_id: str) -> FixtureSpec:
    for spec in all_specs():
        if spec.id == fixture_id:
            return spec
    raise FileNotFoundError(f"Unknown fixture: {fixture_id}")


def list_fixtures() -> list[dict[str, str]]:
    return [
        {
            "id": s.id,
            "label": s.label,
            "description": s.description,
            "runtime": s.runtime,
            "language": s.language,
        }
        for s in all_specs()
    ]


def load_fixture(fixture_id: str) -> tuple[str, str, Path]:
    """Back-compat: return source, tests, folder for simple callers."""
    spec = get_spec(fixture_id)
    source = (spec.root / spec.source_file).read_text(encoding="utf-8")
    tests = (spec.root / spec.test_file).read_text(encoding="utf-8") if spec.test_file else ""
    return source, tests, spec.root


def materialize_workspace(spec: FixtureSpec, workspace: Path) -> None:
    """Copy the sample/fixture tree into an isolated run workspace."""
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    if spec.runtime == "python":
        shutil.copy2(spec.root / "impl.py", workspace / "impl.py")
        shutil.copy2(spec.root / "test_impl.py", workspace / "test_impl.py")
        return

    # node/Next-style sample — copy sources, skip junk
    skip = {".git", "node_modules", "dist", ".next", "coverage"}
    for path in spec.root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.is_file():
            rel = path.relative_to(spec.root)
            dest = workspace / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
