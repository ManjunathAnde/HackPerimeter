import { useState } from "react";
import type { Match } from "../types";
import EmailDraftModal from "./EmailDraftModal";

const CAMPUS_LABEL: Record<string, string> = {
  clarkston: "Clarkston",
  perimeter_all: "All Perimeter campuses",
  online: "Online",
  gsu_wide: "All of GSU",
  atlanta_only: "Atlanta campus",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatEvent(iso: string) {
  return new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function MatchCard({ match }: { match: Match }) {
  const r = match.resource;
  const [emailOpen, setEmailOpen] = useState(false);
  const contact = [r.contact_office, r.contact_email, r.contact_phone].filter(Boolean).join(" · ");
  const place = [r.location_building, r.location_room].filter(Boolean).join(", ");

  return (
    <article className="flex flex-col gap-3 rounded-2xl border-2 border-ink bg-white p-5 shadow-[4px_4px_0_0_#111]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-accent-dark">
          {r.type}
        </span>
        <span className="text-xs text-ink/60">{CAMPUS_LABEL[r.campus] ?? r.campus}</span>
      </div>

      <h3 className="text-lg font-extrabold leading-tight text-ink">{r.name}</h3>
      {r.event_start && <p className="text-sm font-semibold text-accent-dark">{formatEvent(r.event_start)}{place && ` · ${place}`}</p>}

      <p className="text-sm text-ink/80">
        <span className="font-bold text-ink">Why it fits: </span>
        {match.why}
      </p>

      <div className="rounded-xl bg-cream p-3 text-sm">
        <span className="font-bold text-ink">First step: </span>
        {match.first_step}
      </div>

      <p className="text-sm text-ink/80">
        <span className="font-bold text-ink">Contact: </span>
        {contact || "No contact listed. Use the source page."}
      </p>

      <button
        onClick={() => setEmailOpen(true)}
        className="mt-auto rounded-xl border-2 border-ink px-3 py-1.5 text-sm font-bold hover:bg-accent hover:text-white"
      >
        Draft email
      </button>

      <div className="flex items-center justify-between border-t border-ink/10 pt-3 text-xs">
        <a href={r.source_url} target="_blank" rel="noreferrer" className="font-semibold text-accent-dark underline underline-offset-2 hover:text-accent">
          Source
        </a>
        <span className="text-ink/60">Verified {formatDate(r.fetched_at)}</span>
      </div>
      {emailOpen && <EmailDraftModal resource={r} onClose={() => setEmailOpen(false)} />}
    </article>
  );
}
