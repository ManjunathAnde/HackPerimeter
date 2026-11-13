import { useEffect, useRef, useState } from "react";
import { getAlerts, markAlertRead } from "../api";
import type { Alert } from "../types";

const POLL_MS = 5000;
const TOAST_MS = 6000;

export default function AlertsBell() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<Alert | null>(null);
  // null until the first poll, so alerts that already exist on page load don't all pop as toasts
  const seen = useRef<Set<number> | null>(null);

  useEffect(() => {
    let timer: number | undefined;
    async function poll() {
      try {
        const unread = await getAlerts(true);
        if (seen.current) {
          const fresh = unread.filter((a) => !seen.current!.has(a.id));
          if (fresh.length > 0) setToast(fresh[0]);
        }
        seen.current = new Set([...(seen.current ?? []), ...unread.map((a) => a.id)]);
        setAlerts(unread);
      } catch {
        // Backend restarting: keep the last known alerts and try again next tick
      }
    }
    poll();
    timer = window.setInterval(poll, POLL_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), TOAST_MS);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function read(alert: Alert) {
    await markAlertRead(alert.id);
    setAlerts((a) => a.filter((x) => x.id !== alert.id));
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-full border-2 border-ink bg-white p-2 hover:bg-accent-soft"
        aria-label={`${alerts.length} unread alerts`}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {alerts.length > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-black text-white">
            {alerts.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-2xl border-2 border-ink bg-white p-2 shadow-[4px_4px_0_0_#111]">
          <h3 className="px-2 py-1 text-sm font-black">Alerts</h3>
          {alerts.length === 0 && <p className="px-2 py-3 text-sm text-ink/60">Nothing new. I'll tell you when something fits.</p>}
          {alerts.map((a) => (
            <div key={a.id} className="flex items-start gap-2 rounded-xl px-2 py-2 hover:bg-cream">
              <div className="flex-1 text-sm">
                <p>{a.message}</p>
                {a.source_url && (
                  <a href={a.source_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-accent-dark underline">
                    Source
                  </a>
                )}
              </div>
              <button onClick={() => read(a)} className="text-xs font-bold text-ink/50 hover:text-ink">
                Dismiss
              </button>
            </div>
          ))}
        </div>
      )}

      {toast && (
        <div className="fixed bottom-24 right-6 z-50 max-w-sm rounded-2xl border-2 border-ink bg-accent p-4 text-white shadow-[4px_4px_0_0_#111]">
          <p className="text-xs font-black uppercase tracking-wide">New for you</p>
          <p className="mt-1 font-semibold">{toast.message}</p>
        </div>
      )}
    </div>
  );
}
