"use client";

import { useEffect, useRef } from "react";

type Props = {
  lines: string[];
  iteration: number;
  maxIterations: number;
};

export function RunConsole({ lines, iteration, maxIterations }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="flex h-full min-h-[220px] flex-col overflow-hidden rounded-sm border border-slate-700/80 bg-[#07110d]">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-emerald-500/90">
          sandbox terminal
        </span>
        <span className="rounded border border-amber-700/50 bg-amber-950/40 px-2 py-0.5 font-mono text-[11px] text-amber-300">
          attempt {iteration}/{maxIterations}
        </span>
      </div>
      <pre className="flex-1 overflow-auto px-3 py-3 font-mono text-[12px] leading-5 text-emerald-300/90">
        {lines.length === 0 ? (
          <span className="text-slate-500">Waiting for Docker output…</span>
        ) : (
          lines.join("")
        )}
        <div ref={bottomRef} />
      </pre>
    </div>
  );
}
