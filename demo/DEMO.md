# AutoPatch — operational walkthrough

This document describes a standard validation path for the remediation service: environment checks, a Node remediation run, a Python remediation run, and CI failure ingestion.

## Preconditions

Confirm the following before starting:

- Docker Engine is running
- API is available at `http://127.0.0.1:8000`
- Dashboard is available at `http://localhost:3000`
- `GEMINI_API_KEY` is set in `backend/.env`
- Sandbox images exist:
  - `autopatch-sandbox:latest`
  - `autopatch-node-sandbox:latest`

Quick checks:

```bash
curl http://127.0.0.1:8000/api/health
docker images autopatch-sandbox
docker images autopatch-node-sandbox
```

If images are missing:

```bash
cd backend
docker build -t autopatch-sandbox:latest .\sandbox
docker build -t autopatch-node-sandbox:latest .\sandbox-node
```

## Walkthrough A — Node / Jest remediation

Target: `nextjs_pricing` (`samples/nextjs-cart`)

1. Open the dashboard and select **Next.js Cart Pricing**
2. Start remediation
3. Observe the graph advance through ingest, sandbox, evaluate, and patch
4. Confirm the sandbox terminal shows an initial Jest failure, then a green re-run after the patch
5. Review the diff for `lib/pricing.ts`
6. Approve to persist, or reject to discard

Expected outcome on approve:

- Run status becomes `committed`
- A local commit SHA is shown in the metrics panel
- If `GITHUB_TOKEN` and `GITHUB_REPOSITORY` are configured, a pull request URL may also appear

## Walkthrough B — Python / pytest remediation

Target: `off_by_one` or `fizzbuzz_bug`

1. Select the fixture in the dashboard
2. Start remediation
3. Confirm pytest output streams in the sandbox terminal
4. Review the `impl.py` diff
5. Approve or reject

This path validates the Python sandbox image and the same LangGraph control flow used by the Node runtime.

## Walkthrough C — CI failure ingestion

With the API running, submit a failure payload the same way a pipeline would:

```powershell
.\scripts\simulate-ci.ps1
```

The script executes Jest in `samples/nextjs-cart` and, on failure, posts to `/api/ci/failures`. The resulting run appears in the dashboard and follows the same approval gate.

Equivalent request shape:

```http
POST /api/ci/failures
Content-Type: application/json

{
  "fixture_id": "nextjs_pricing",
  "error_log": "<captured test output>",
  "repo": "owner/repo",
  "branch": "main",
  "commit_sha": "<sha>"
}
```

## Verification checklist

- [ ] Initial sandbox execution fails for the intentional defect
- [ ] Model produces a scoped patch to the registered source file
- [ ] Re-test in Docker passes
- [ ] Dashboard blocks on approval before commit
- [ ] Approve writes a commit; reject leaves no durable change
- [ ] CI simulation creates a run through `/api/ci/failures`

## Notes for operators

- Remediation is scoped to the registered source/test pair for a fixture. Large repositories should be attached by registering the failing module (or package) explicitly rather than sending an entire monorepo into the agent context.
- Generated code is never executed on the host; validation occurs only inside the sandbox.
- Production integration typically means: pipeline failure → `/api/ci/failures` → operator review → approve → commit/PR → merge and continue deploy.
