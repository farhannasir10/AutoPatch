# AutoPatch

AutoPatch is an autonomous code remediation service for failing automated tests. It ingests a failing implementation and its associated test suite, proposes a patch with a language model, validates the change inside an isolated Docker sandbox, and requires explicit human approval before committing or opening a pull request.

The system is designed for CI/CD integration: when a pipeline reports a test failure, AutoPatch can take over the remediation loop instead of leaving the failure idle until a developer picks it up.

## Capabilities

- Stateful remediation workflow (ingest → execute tests → patch → re-test → evaluate)
- Network-isolated Docker execution for untrusted generated code
- Python (pytest) and Node.js (Jest) runtimes
- Live run streaming over Server-Sent Events
- Side-by-side patch review in the dashboard
- Human-in-the-loop approval before persistence
- Optional GitHub pull request creation on approve
- CI failure ingestion endpoint for pipeline webhooks

## Architecture

```
CI failure / registered fixture
            │
            ▼
     FastAPI control plane
            │
            ▼
        LangGraph cycle
   ingest → sandbox → evaluate
              ↺ patch (on failure)
            │
            ▼ (tests pass)
     approval breakpoint
            │
     approve → commit / PR
     reject  → discard
```

| Component | Technology |
|-----------|------------|
| Model | Google Gemini (configurable via env) |
| Orchestration | LangGraph with checkpointed interrupts |
| Sandbox | Docker (`autopatch-sandbox`, `autopatch-node-sandbox`) |
| API | FastAPI, SSE |
| Dashboard | Next.js, Monaco diff viewer |
| VCS | Local git commit; optional GitHub Pulls API |

Remediation is intentionally scoped. The agent receives the failing source file, related tests, and the failure log—not an entire monorepo—so patches stay reviewable and sandboxed runs stay reproducible.

## Repository layout

```
Autopatch/
├── backend/           # API, LangGraph workflow, sandbox tooling
├── frontend/          # Operations dashboard
├── fixtures/          # Python remediation fixtures
├── samples/           # Node/Next-style sample project
├── demo/              # Operational walkthrough
├── scripts/           # Local CI simulation helpers
└── .github/workflows/ # Example CI bridge workflow
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Engine / Docker Desktop
- A Google AI Studio API key (`GEMINI_API_KEY`)

## Setup

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

Configure at minimum:

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-flash-lite-latest
DOCKER_IMAGE=autopatch-sandbox:latest
DOCKER_NODE_IMAGE=autopatch-node-sandbox:latest
```

Optional GitHub integration (enables PR creation on approve):

```env
GITHUB_TOKEN=...
GITHUB_REPOSITORY=owner/repo
GITHUB_PR_BASE=main
```

Build sandbox images:

```bash
docker build -t autopatch-sandbox:latest .\sandbox
docker build -t autopatch-node-sandbox:latest .\sandbox-node
```

Start the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npx next dev -p 3000
```

Dashboard: [http://localhost:3000](http://localhost:3000)

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Usage

### Dashboard

1. Select a registered fixture (for example **Next.js Cart Pricing**)
2. Start remediation
3. Monitor graph state, sandbox logs, and the generated diff
4. Approve to commit (and open a PR when GitHub env vars are configured), or reject to discard

### CI bridge

Pipelines can submit failure context directly:

```http
POST /api/ci/failures
Content-Type: application/json

{
  "fixture_id": "nextjs_pricing",
  "error_log": "<failing job output>",
  "repo": "owner/repo",
  "branch": "main",
  "commit_sha": "abc123"
}
```

Local simulation against the sample cart project:

```powershell
.\scripts\simulate-ci.ps1
```

Reference workflow: [`.github/workflows/autopatch-ci.yml`](.github/workflows/autopatch-ci.yml)  
(Manual `workflow_dispatch` only — keeps `main` green; the cart sample stays intentionally failing for local demos.)

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health and key configuration status |
| `GET` | `/api/fixtures` | Registered remediation targets |
| `POST` | `/api/runs` | Start a run from a fixture id |
| `POST` | `/api/ci/failures` | Start a run from CI failure payload |
| `GET` | `/api/runs/{id}` | Run snapshot |
| `GET` | `/api/runs/{id}/events` | SSE event stream |
| `POST` | `/api/runs/{id}/decision` | `{ "decision": "approve" \| "reject" }` |

## Registered fixtures

| ID | Runtime | Description |
|----|---------|-------------|
| `nextjs_pricing` | Node / Jest | Percent discount applied without scaling by 100 |
| `off_by_one` | Python / pytest | Inclusive sum off-by-one in `range` |
| `wrong_return` | Python / pytest | Palindrome check compares cleaned vs raw input |
| `missing_import` | Python / pytest | Uses `mean` without importing it |
| `type_coercion` | Python / pytest | Returns strings where ints are expected |
| `fizzbuzz_bug` | Python / pytest | `% 15` checked after `% 3` / `% 5` |

To attach an additional codebase, register a fixture/sample with a `fixture.json` (source file, test file, runtime, test command), ensure the matching sandbox image contains required dependencies, then point CI at `/api/ci/failures` with that `fixture_id`.

## Safety controls

- Sandbox containers run with networking disabled
- CPU, memory, and execution timeouts are enforced
- Workspace content is overlaid into ephemeral containers
- Persistence (commit / PR) occurs only after explicit approval

## Documentation

- Operational walkthrough: [`demo/DEMO.md`](demo/DEMO.md)

## License

MIT
