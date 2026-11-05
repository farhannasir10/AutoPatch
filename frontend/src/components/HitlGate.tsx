"use client";

type Props = {
  visible: boolean;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
};

export function HitlGate({ visible, busy, onApprove, onReject }: Props) {
  if (!visible) return null;

  return (
    <div className="rounded-sm border border-amber-600/50 bg-amber-950/30 p-4 shadow-[inset_0_0_40px_rgba(245,158,11,0.08)]">
      <p className="font-display text-lg text-amber-100">Human-in-the-loop gate</p>
      <p className="mt-1 max-w-xl text-sm text-amber-100/70">
        Tests are green in the sandbox. Nothing is committed until you say so —
        review the diff, then approve or reject.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={onApprove}
          className="bg-emerald-500 px-5 py-2.5 font-mono text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-50"
        >
          Approve & Commit
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onReject}
          className="border border-rose-400 bg-rose-950/50 px-5 py-2.5 font-mono text-sm font-medium text-rose-200 transition hover:border-rose-300 hover:bg-rose-900/60 hover:text-rose-100 disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
