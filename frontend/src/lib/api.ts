const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

export type Fixture = {
  id: string;
  label: string;
  description: string;
  runtime?: string;
  language?: string;
};

export type RunSummary = {
  id: string;
  fixture_id: string;
  status: string;
  active_node: string;
  iteration: number;
  max_iterations: number;
  patch_diff: string;
  original_source: string;
  patched_source: string;
  error_log: string;
  test_exit_code: number | null;
  commit_sha?: string;
  pr_url?: string;
  runtime?: string;
  source_file?: string;
  started_at?: number;
  finished_at?: number;
  workspace?: string;
};

export type RunEvent = {
  type: string;
  run_id?: string;
  ts?: number;
  iteration?: number;
  active_node?: string;
  status?: string;
  message?: string;
  patch_diff?: string;
  patched_source?: string;
  original_source?: string;
  error_log?: string;
  exit_code?: number;
  duration_ms?: number;
  commit_sha?: string;
  pr_url?: string;
  source_code?: string;
  test_code?: string;
  runtime?: string;
  source_file?: string;
};

export async function fetchFixtures(): Promise<Fixture[]> {
  const res = await fetch(`${API_BASE}/fixtures`);
  if (!res.ok) throw new Error("Failed to load fixtures");
  return res.json();
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    return JSON.stringify(data);
  } catch {
    return fallback;
  }
}

export async function startRun(fixtureId: string): Promise<RunSummary> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fixture_id: fixtureId }),
  });
  if (!res.ok) {
    throw new Error(await readError(res, "Failed to start run"));
  }
  return res.json();
}

export async function decide(
  runId: string,
  decision: "approve" | "reject",
): Promise<RunSummary> {
  const res = await fetch(`${API_BASE}/runs/${runId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  if (!res.ok) {
    throw new Error(await readError(res, "Decision failed"));
  }
  return res.json();
}

export function eventsUrl(runId: string): string {
  return `${API_BASE}/runs/${runId}/events`;
}
