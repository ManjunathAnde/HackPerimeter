import { useState } from "react";
import type { ChatResponse } from "../types";

const STEP_STYLE: Record<string, string> = {
  plan: "bg-ink text-cream",
  search: "bg-cream-dark text-ink",
  freshness: "bg-cream-dark text-ink",
  refetch: "bg-accent text-white",
  answer: "bg-ink text-cream",
  verify: "bg-accent-soft text-accent-dark",
};

export default function TracePanel({ response }: { response: ChatResponse }) {
  const [open, setOpen] = useState(false);
  const total = response.trace.reduce((sum, t) => sum + t.ms, 0);
  const removed = response.verification.removed_sentences;

  return (
    <div className="rounded-xl border border-ink/20 bg-white/60 text-sm">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-4 py-2 text-left font-bold">
        <span>
          How I found this <span className="font-normal text-ink/60">· {response.trace.length} steps · {(total / 1000).toFixed(1)}s</span>
        </span>
        <span className="text-accent-dark">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <ol className="flex flex-col gap-1.5 border-t border-ink/10 px-4 py-3">
          {response.trace.map((t, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-bold uppercase ${STEP_STYLE[t.step] ?? "bg-cream-dark"}`}>
                {t.step}
              </span>
              <span className="flex-1 break-words text-ink/80">{t.detail}</span>
              <span className="shrink-0 font-mono text-xs text-ink/50">{t.ms} ms</span>
            </li>
          ))}
          {removed.length > 0 && (
            <li className="mt-1 rounded-lg bg-accent-soft p-2 text-accent-dark">
              <span className="font-bold">Removed as unsupported: </span>
              {removed.join(" ")}
            </li>
          )}
        </ol>
      )}
    </div>
  );
}
