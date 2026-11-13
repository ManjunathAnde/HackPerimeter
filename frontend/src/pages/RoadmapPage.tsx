import { useEffect, useState } from "react";
import { getPathways, getRoadmap, getStats } from "../api";
import type { KbStats, Resource, Roadmap } from "../types";

const TYPE_LABEL: Record<string, string> = {
  event: "events",
  program: "programs",
  office: "offices",
  service: "services",
  opportunity: "opportunities",
  org: "clubs",
  center: "centers",
};

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function stepMeta(r: Resource) {
  const when = r.event_start ? `${shortDate(r.event_start)} · ` : "";
  return `${when}${r.name}`;
}

function RoadmapCard({ roadmap }: { roadmap: Roadmap }) {
  const { pathway, steps } = roadmap;
  const highlights = steps.slice(0, 3).map((s) => s.resources[0].name);

  return (
    <section className="rounded-[28px] border-[3px] border-ink bg-paper p-5 shadow-[8px_8px_0_0_#1E2527] sm:p-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl leading-none sm:text-3xl">{pathway.name}</h2>
          <p className="mt-2 text-ink/70">
            {pathway.focus} · {pathway.start}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-ink px-3 py-1 text-sm font-bold text-paper">{steps.length} steps</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {highlights.map((h) => (
          <span key={h} className="rounded-full border-2 border-ink px-3 py-1 text-xs font-bold">
            {h}
          </span>
        ))}
      </div>

      <ol className="mt-5 flex flex-col">
        {steps.map((step, i) => {
          const r = step.resources[0];
          return (
            <li key={step.title} className="flex flex-col">
              {i > 0 && <span className="ml-9 h-4 border-l-2 border-dashed border-ink" />}
              <div className="flex items-center gap-4 rounded-2xl border-2 border-dashed border-ink/60 px-4 py-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-[3px] border-ink bg-accent font-black text-paper">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-bold leading-snug">{step.title}</p>
                  <p className="truncate text-sm text-ink/70">{stepMeta(r)}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-0.5 text-xs">
                  <a href={r.source_url} target="_blank" rel="noreferrer" className="font-bold text-accent-dark underline underline-offset-2 hover:text-accent">
                    Source
                  </a>
                  <span className="text-ink/60">Verified {shortDate(r.fetched_at)}</span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export default function RoadmapPage() {
  const [roadmaps, setRoadmaps] = useState<Roadmap[]>([]);
  const [stats, setStats] = useState<KbStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
    getPathways()
      .then((ps) => Promise.all(ps.map((p) => getRoadmap(p.id))))
      .then(setRoadmaps)
      .catch((e) => setError(e.message));
  }, []);

  const counts = stats
    ? Object.entries(stats.by_type)
        .sort((a, b) => b[1] - a[1])
        .map(([type, n]) => `${n} ${TYPE_LABEL[type] ?? type}`)
        .join(" · ")
    : null;

  return (
    <div className="mx-auto max-w-4xl px-4 pb-12 sm:px-6">
      <h2 className="font-display pt-8 text-5xl leading-[0.9] sm:text-7xl">My roadmaps.</h2>
      <p className="mt-3 text-lg text-ink/80">Every step is a real GSU resource, with its source and the date we last checked it.</p>

      {counts && (
        <p className="mt-6 inline-block rounded-full border-2 border-dashed border-ink bg-paper px-4 py-1.5 text-sm">
          Pulled from the GSU database: {counts}
        </p>
      )}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>}

      <div className="mt-8 flex flex-col gap-10">
        {roadmaps.map((r) => (
          <RoadmapCard key={r.pathway.id} roadmap={r} />
        ))}
      </div>
    </div>
  );
}
