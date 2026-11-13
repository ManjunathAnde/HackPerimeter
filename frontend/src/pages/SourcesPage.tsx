import { useEffect, useState } from "react";
import { getSources, runAll, runSource } from "../api";
import type { Source } from "../types";

const STATUS_STYLE: Record<string, string> = {
  ok: "bg-green-100 text-green-800",
  unchanged: "bg-cream-dark text-ink/70",
  error: "bg-red-100 text-red-800",
};

function ago(iso: string | null) {
  if (!iso) return "never";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  return `${Math.round(min / 60)} h ago`;
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => getSources().then(setSources).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function run(id: string) {
    setRunning((r) => new Set(r).add(id));
    setMessage(null);
    try {
      const { run, alerts_created } = await runSource(id);
      setMessage(
        run.error
          ? `${id}: fetch failed, keeping the stored copy (${run.error.slice(0, 80)})`
          : `${id}: ${run.rows_new} new, ${run.rows_changed} changed, ${run.rows_unchanged} unchanged · ${alerts_created} alert${alerts_created === 1 ? "" : "s"}`,
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning((r) => {
        const next = new Set(r);
        next.delete(id);
        return next;
      });
    }
  }

  async function all() {
    setRunning(new Set(sources.map((s) => s.id)));
    setMessage("Running every source. This can take a couple of minutes.");
    try {
      const res = await runAll();
      setMessage(`Ran ${res.runs.length} sources · ${res.alerts_created} new alerts`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run all failed");
    } finally {
      setRunning(new Set());
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-3 py-6">
        <div>
          <h2 className="text-3xl font-black text-ink">Sources</h2>
          <p className="text-ink/70">Official GSU pages and feeds the agents read. Nothing else gets into answers.</p>
        </div>
        <button onClick={all} disabled={running.size > 0} className="rounded-xl bg-ink px-5 py-2 font-bold text-cream hover:bg-ink/80 disabled:opacity-40">
          Run all
        </button>
      </div>

      {message && <p className="mb-4 rounded-xl border-2 border-ink bg-accent-soft px-4 py-2 font-semibold text-accent-dark">{message}</p>}
      {error && <p className="mb-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>}

      <div className="overflow-x-auto rounded-2xl border-2 border-ink bg-white shadow-[4px_4px_0_0_#111]">
        <table className="w-full text-left text-sm">
          <thead className="border-b-2 border-ink bg-cream-dark text-xs uppercase tracking-wide">
            <tr>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Campus</th>
              <th className="px-3 py-2">Last run</th>
              <th className="px-3 py-2">Last changed</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2 text-right">Rows</th>
              <th className="px-3 py-2 text-right">New / chg / drop</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id} className="border-b border-ink/10 last:border-0">
                <td className="px-3 py-2">
                  <a href={s.url} target="_blank" rel="noreferrer" className="font-bold hover:text-accent-dark" title={s.url}>
                    {s.id}
                  </a>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{s.kind}</td>
                <td className="px-3 py-2">{s.campus}</td>
                <td className="whitespace-nowrap px-3 py-2">{ago(s.last_run_at)}</td>
                <td className="whitespace-nowrap px-3 py-2">{ago(s.last_changed_at)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_STYLE[s.last_status ?? ""] ?? "bg-cream-dark"}`} title={s.last_error ?? ""}>
                    {s.last_status ?? "never run"}
                  </span>
                </td>
                <td className="px-3 py-2 text-right font-mono">{s.rows_total}</td>
                <td className="px-3 py-2 text-right font-mono">
                  {s.rows_new ?? 0} / {s.rows_changed ?? 0} / {s.rows_dropped ?? 0}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => run(s.id)}
                    disabled={running.has(s.id)}
                    className="whitespace-nowrap rounded-lg bg-accent px-3 py-1 text-xs font-bold text-white hover:bg-accent-dark disabled:opacity-40"
                  >
                    {running.has(s.id) ? "Running..." : "Run now"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
