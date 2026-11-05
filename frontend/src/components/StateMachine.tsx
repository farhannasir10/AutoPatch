"use client";

const NODES = [
  { id: "ingest", label: "Ingest" },
  { id: "generate_patch", label: "Patch" },
  { id: "run_sandbox", label: "Sandbox" },
  { id: "evaluate", label: "Evaluate" },
  { id: "await_approval", label: "HITL" },
  { id: "commit_patch", label: "Commit" },
] as const;

type Props = {
  activeNode: string;
  status: string;
};

export function StateMachine({ activeNode, status }: Props) {
  const failed = status === "failed" || status === "error";
  const rejected = status === "rejected";
  const committed = status === "committed";

  return (
    <div className="space-y-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-500/80">
        remediation graph
      </p>
      <ol className="space-y-2">
        {NODES.map((node, index) => {
          const isActive =
            activeNode === node.id ||
            (committed && node.id === "commit_patch") ||
            (rejected && node.id === "await_approval");
          const isPast =
            NODES.findIndex((n) => n.id === activeNode) > index ||
            committed ||
            (rejected && index < NODES.findIndex((n) => n.id === "await_approval"));

          return (
            <li key={node.id} className="flex items-center gap-3">
              <span
                className={[
                  "relative flex h-2.5 w-2.5 rounded-full",
                  isActive
                    ? "bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.85)] animate-pulse"
                    : isPast
                      ? "bg-emerald-700"
                      : "bg-slate-600",
                ].join(" ")}
              />
              <span
                className={[
                  "font-mono text-sm",
                  isActive ? "text-emerald-300" : isPast ? "text-slate-300" : "text-slate-500",
                ].join(" ")}
              >
                {node.label}
              </span>
            </li>
          );
        })}
        {failed && (
          <li className="flex items-center gap-3 pt-1">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
            <span className="font-mono text-sm text-rose-400">Failed</span>
          </li>
        )}
      </ol>
    </div>
  );
}
