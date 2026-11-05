"use client";

import dynamic from "next/dynamic";

// Monaco pulls a lot of workers — load it only in the browser
const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center font-mono text-xs text-slate-500">
        loading diff editor…
      </div>
    ),
  },
);

type Props = {
  original: string;
  modified: string;
  fileLabel?: string;
  language?: string;
};

export function DiffViewer({
  original,
  modified,
  fileLabel = "impl.py",
  language = "python",
}: Props) {
  return (
    <div className="flex h-full min-h-[320px] flex-col overflow-hidden rounded-sm border border-slate-700/80 bg-[#0b1220]">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-sky-400/90">
          patch diff · {fileLabel}
        </span>
        <span className="font-mono text-[11px] text-slate-500">before → after</span>
      </div>
      <div className="min-h-0 flex-1 animate-[fadeIn_0.35s_ease]">
        <DiffEditor
          original={original || "// waiting for source…"}
          modified={modified || original || "// waiting for patch…"}
          language={language}
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: "JetBrains Mono, ui-monospace, monospace",
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
