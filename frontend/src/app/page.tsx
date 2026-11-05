"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { DiffViewer } from "../components/DiffViewer";
import { HitlGate } from "../components/HitlGate";
import { MetricsCard } from "../components/MetricsCard";
import { RunConsole } from "../components/RunConsole";
import { StateMachine } from "../components/StateMachine";
import {
  decide,
  eventsUrl,
  fetchFixtures,
  startRun,
  type Fixture,
  type RunEvent,
  type RunSummary,
} from "../lib/api";

export default function HomePage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [fixtureId, setFixtureId] = useState("nextjs_pricing");
  const [run, setRun] = useState<RunSummary | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [statusMsg, setStatusMsg] = useState("Select a fixture and start a remediation run.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    fetchFixtures()
      .then((items) => {
        setFixtures(items);
        const preferred =
          items.find((f) => f.id === "nextjs_pricing") || items[0];
        if (preferred) setFixtureId(preferred.id);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  // tick the wall-clock while a run is live
  useEffect(() => {
    if (!run || run.finished_at) return;
    const id = window.setInterval(() => setNow(Date.now() / 1000), 250);
    return () => window.clearInterval(id);
  }, [run]);

  const applyEvent = useCallback((event: RunEvent) => {
    if (event.message && event.type !== "log") {
      setStatusMsg(event.message);
    }
    if (event.type === "log" && event.message) {
      setLogs((prev) => [...prev, event.message!]);
    }
    setRun((prev) => {
      if (!prev) return prev;
      const statusFromType =
        event.type === "hitl"
          ? "awaiting_approval"
          : event.type === "committed"
            ? "committed"
            : event.type === "rejected"
              ? "rejected"
              : event.type === "failed" || event.type === "error"
                ? "failed"
                : undefined;
      return {
        ...prev,
        status: event.status || statusFromType || prev.status,
        active_node: event.active_node || prev.active_node,
        iteration: event.iteration ?? prev.iteration,
        patch_diff: event.patch_diff ?? prev.patch_diff,
        patched_source: event.patched_source ?? prev.patched_source,
        original_source: event.original_source ?? prev.original_source,
        error_log: event.error_log ?? prev.error_log,
        test_exit_code:
          event.exit_code !== undefined ? event.exit_code : prev.test_exit_code,
        commit_sha: event.commit_sha ?? prev.commit_sha,
        pr_url: event.pr_url ?? prev.pr_url,
        runtime: event.runtime ?? prev.runtime,
        source_file: event.source_file ?? prev.source_file,
        finished_at:
          event.type === "committed" ||
          event.type === "rejected" ||
          event.type === "failed" ||
          event.type === "error"
            ? event.ts || Date.now() / 1000
            : prev.finished_at,
      };
    });
  }, []);

  const subscribe = useCallback(
    (runId: string) => {
      const source = new EventSource(eventsUrl(runId));
      source.onmessage = (msg) => {
        try {
          applyEvent(JSON.parse(msg.data) as RunEvent);
        } catch {
          /* ignore malformed keepalive payloads */
        }
      };
      // named SSE events from the backend
      for (const name of [
        "status",
        "node",
        "log",
        "patch",
        "sandbox_result",
        "hitl",
        "committed",
        "rejected",
        "failed",
        "error",
        "ping",
      ]) {
        source.addEventListener(name, (msg) => {
          if (name === "ping") return;
          try {
            applyEvent(JSON.parse((msg as MessageEvent).data) as RunEvent);
          } catch {
            /* noop */
          }
        });
      }
      source.onerror = () => {
        source.close();
      };
      return source;
    },
    [applyEvent],
  );

  async function onStart() {
    setBusy(true);
    setError(null);
    setLogs([]);
    setStatusMsg("Booting remediation run…");
    try {
      const created = await startRun(fixtureId);
      setRun({ ...created, started_at: created.started_at || Date.now() / 1000 });
      subscribe(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
    } finally {
      setBusy(false);
    }
  }

  async function onDecision(decision: "approve" | "reject") {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await decide(run.id, decision);
      setRun((prev) => ({ ...(prev || updated), ...updated }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  const selected = useMemo(
    () => fixtures.find((f) => f.id === fixtureId),
    [fixtures, fixtureId],
  );

  const awaiting = run?.status === "awaiting_approval";

  return (
    <main className="app-shell min-h-screen px-4 py-6 text-slate-100 md:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-4 border-b border-slate-700/50 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-emerald-400/80">
              self-healing ci remediation
            </p>
            <h1 className="font-display text-5xl font-extrabold text-white md:text-6xl">
              AutoPatch
            </h1>
            <p className="mt-2 max-w-xl text-sm text-slate-400">
              Diagnose failing tests, patch in a network-isolated Docker sandbox, stream
              every retry live — then wait for a human before anything lands.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <select
              value={fixtureId}
              onChange={(e) => setFixtureId(e.target.value)}
              className="min-w-[220px] border border-slate-600 bg-slate-950/80 px-3 py-2.5 font-mono text-sm text-slate-200 outline-none focus:border-emerald-500"
            >
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onStart}
              disabled={busy || !fixtureId}
              className="bg-emerald-400 px-5 py-2.5 font-mono text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:opacity-50"
            >
              Start remediation
            </button>
          </div>
        </header>

        {selected && (
          <p className="font-mono text-xs text-slate-500">{selected.description}</p>
        )}
        {error && (
          <div className="border border-rose-700/50 bg-rose-950/40 px-3 py-2 font-mono text-sm text-rose-300">
            {error}
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          <aside className="space-y-5 rounded-sm border border-slate-700/70 bg-slate-950/40 p-5">
            <StateMachine
              activeNode={run?.active_node || "idle"}
              status={run?.status || "idle"}
            />
            <MetricsCard
              status={run?.status || "idle"}
              iteration={run?.iteration || 0}
              maxIterations={run?.max_iterations || 5}
              startedAt={run?.started_at}
              finishedAt={run?.finished_at || (run && !run.finished_at ? now : undefined)}
              commitSha={run?.commit_sha}
              prUrl={run?.pr_url}
              exitCode={run?.test_exit_code ?? null}
              runtime={run?.runtime || selected?.runtime}
            />
            <p className="font-mono text-[11px] leading-5 text-slate-500">{statusMsg}</p>
          </aside>

          <section className="space-y-4">
            <HitlGate
              visible={!!awaiting}
              busy={busy}
              onApprove={() => onDecision("approve")}
              onReject={() => onDecision("reject")}
            />
            <div className="h-[360px]">
              <DiffViewer
                original={run?.original_source || ""}
                modified={run?.patched_source || run?.original_source || ""}
                fileLabel={run?.source_file || selected?.id || "source"}
                language={
                  selected?.language === "typescript" || selected?.runtime === "node"
                    ? "typescript"
                    : "python"
                }
              />
            </div>
            <div className="h-[260px]">
              <RunConsole
                lines={logs}
                iteration={run?.iteration || 0}
                maxIterations={run?.max_iterations || 5}
              />
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
