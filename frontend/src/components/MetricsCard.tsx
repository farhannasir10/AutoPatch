"use client";

type Props = {
  status: string;
  iteration: number;
  maxIterations: number;
  startedAt?: number;
  finishedAt?: number;
  commitSha?: string;
  prUrl?: string;
  exitCode: number | null;
  runtime?: string;
};

function elapsedLabel(startedAt?: number, finishedAt?: number): string {
  if (!startedAt) return "—";
  const end = finishedAt || Date.now() / 1000;
  const secs = Math.max(0, end - startedAt);
  return `${secs.toFixed(1)}s`;
}

// short labels so the sidebar cards never clip mid-word
function statusLabel(status: string): string {
  const map: Record<string, string> = {
    awaiting_approval: "waiting",
    queued: "queued",
    running: "running",
    committed: "committed",
    rejected: "rejected",
    failed: "failed",
    idle: "idle",
    error: "error",
  };
  return map[status] || status.split("_").join(" ");
}

export function MetricsCard({
  status,
  iteration,
  maxIterations,
  startedAt,
  finishedAt,
  commitSha,
  prUrl,
  exitCode,
  runtime,
}: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 font-mono text-xs">
      <Metric label="status" value={statusLabel(status || "idle")} accent />
      <Metric label="wall time" value={elapsedLabel(startedAt, finishedAt)} />
      <Metric label="iterations" value={`${iteration}/${maxIterations}`} />
      <Metric
        label={runtime === "node" ? "jest" : "pytest"}
        value={exitCode === null || exitCode === undefined ? "—" : String(exitCode)}
      />
      {runtime && (
        <div className="col-span-2 rounded-sm border border-slate-700/70 bg-slate-900/50 px-3.5 py-3 text-slate-300">
          runtime · {runtime}
        </div>
      )}
      {commitSha && (
        <div className="col-span-2 rounded-sm border border-emerald-700/40 bg-emerald-950/30 px-3.5 py-3 text-emerald-300">
          committed · {commitSha}
        </div>
      )}
      {prUrl && (
        <a
          href={prUrl}
          target="_blank"
          rel="noreferrer"
          className="col-span-2 rounded-sm border border-sky-700/40 bg-sky-950/30 px-3.5 py-3 text-sky-300 underline-offset-2 hover:underline"
        >
          pull request · open
        </a>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-sm border border-slate-700/70 bg-slate-900/50 px-3.5 py-3">
      <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</div>
      <div
        className={[
          "mt-1.5 break-words leading-snug",
          accent ? "text-amber-300" : "text-slate-200",
        ].join(" ")}
      >
        {value}
      </div>
    </div>
  );
}
