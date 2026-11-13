import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loadDemoProfile, saveProfile } from "../api";
import { CAMPUSES, HOLDS, INTERESTS, PATHWAYS, markOnboarded } from "../profileOptions";

const chip = (on: boolean) =>
  `rounded-full border-2 border-ink px-4 py-1.5 text-sm font-bold transition ${on ? "bg-ink text-paper" : "bg-paper hover:bg-cream-dark"}`;
const field = "w-full rounded-2xl border-[3px] border-ink bg-white px-4 py-3 outline-none focus:border-accent";
const labelCls = "mb-1.5 block text-sm font-bold";

function Stepper({ step }: { step: 1 | 2 }) {
  const items = ["About you", "What I'm into", "My roadmaps"];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((t, i) => (
        <span key={t} className={`rounded-full border-2 border-ink px-3 py-1.5 text-sm font-bold ${i + 1 === step ? "bg-ink text-paper" : ""}`}>
          {i + 1} · {t}
        </span>
      ))}
    </div>
  );
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [campus, setCampus] = useState("clarkston");
  const [pathway, setPathway] = useState("business_admin");
  const [credits, setCredits] = useState(0);
  const [workHours, setWorkHours] = useState(0);
  const [holds, setHolds] = useState<string[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [interests, setInterests] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  async function finish(save: () => Promise<unknown>) {
    setSaving(true);
    setError(null);
    try {
      await save();
      markOnboarded();
      navigate("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
      setSaving(false);
    }
  }

  function submit() {
    const topics = [...new Set(INTERESTS.filter((i) => picked.includes(i.label)).flatMap((i) => i.topics))];
    return finish(() =>
      saveProfile({
        name: name.trim() || "Student",
        campus,
        pathway_id: pathway,
        credits,
        work_hours: workHours,
        holds,
        interests: interests.trim(),
        topics,
      }),
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 pb-12 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3 py-6">
        <p className="font-bold">Pathfinder · Georgia State</p>
        <Stepper step={step} />
      </div>

      {step === 1 ? (
        <div className="grid items-start gap-10 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-6xl leading-[0.88] sm:text-8xl">Let's map your next move.</h2>
            <p className="mt-6 max-w-md text-lg">Two quick things. Then tell me what you want, and I'll find the GSU resources that fit.</p>
            <button
              onClick={() => finish(loadDemoProfile)}
              disabled={saving}
              className="mt-6 rounded-full border-2 border-ink px-5 py-2 font-bold hover:bg-paper disabled:opacity-40"
            >
              Use demo student (Jordan)
            </button>
          </div>

          <div className="rounded-[28px] border-[3px] border-ink bg-paper p-6 shadow-[10px_10px_0_0_#1E2527]">
            <label className={labelCls}>Your name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="First name" className={field} />

            <p className={`${labelCls} mt-5`}>Your GSU campus</p>
            <div className="flex flex-wrap gap-2">
              {CAMPUSES.map((c) => (
                <button key={c.id} type="button" onClick={() => setCampus(c.id)} className={chip(campus === c.id)}>
                  {c.label}
                </button>
              ))}
            </div>

            <label className={`${labelCls} mt-5`}>Pathway</label>
            <select value={pathway} onChange={(e) => setPathway(e.target.value)} className={field}>
              {PATHWAYS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>

            <div className="mt-5 grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Credits so far</label>
                <input type="number" min={0} value={credits} onChange={(e) => setCredits(Math.max(0, Number(e.target.value)))} className={field} />
              </div>
              <div>
                <label className={labelCls}>Work hours / week</label>
                <input type="number" min={0} value={workHours} onChange={(e) => setWorkHours(Math.max(0, Number(e.target.value)))} className={field} />
              </div>
            </div>

            <p className={`${labelCls} mt-5`}>Any holds on your account?</p>
            <div className="flex flex-wrap gap-4">
              {HOLDS.map((h) => (
                <label key={h.id} className="flex items-center gap-2 text-sm font-semibold">
                  <input type="checkbox" checked={holds.includes(h.id)} onChange={() => toggle(holds, setHolds, h.id)} className="h-4 w-4 accent-[#C9622B]" />
                  {h.label}
                </label>
              ))}
            </div>

            <button onClick={() => setStep(2)} className="mt-7 w-full rounded-full bg-ink py-3.5 text-lg font-black text-paper hover:bg-ink/85">
              Next: what I'm into
            </button>
          </div>
        </div>
      ) : (
        <div>
          <h2 className="font-display text-center text-6xl leading-none sm:text-8xl">Hey, {name.trim() || "friend"}.</h2>
          <p className="mt-3 text-center text-lg">What are you into, and what do you want to get done?</p>

          <div className="mt-8 grid items-start gap-8 lg:grid-cols-2">
            <div className="rounded-[28px] border-[3px] border-ink bg-paper p-6 shadow-[10px_10px_0_0_#1E2527]">
              <h3 className="text-lg font-black">Tell me</h3>
              <p className="mt-3 rounded-2xl border-2 border-ink bg-note p-4 text-sm">
                Tell me what you're into and what you want: a job, better classes, starting something, friends, anything. I'll use it to find what
                fits.
              </p>
              <input
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="I want to turn my side hustle into a real business"
                className="mt-5 w-full rounded-full border-[3px] border-ink bg-white px-5 py-3 outline-none focus:border-accent"
              />
            </div>

            <div>
              <p className="mb-2 text-sm">What you're into</p>
              <div className="flex flex-wrap gap-3">
                {INTERESTS.map((i) => (
                  <button
                    key={i.label}
                    type="button"
                    onClick={() => toggle(picked, setPicked, i.label)}
                    className={`${chip(picked.includes(i.label))} rounded-2xl border-[3px] px-4 py-2.5`}
                  >
                    {i.label}
                  </button>
                ))}
              </div>
              <div className="mt-8 flex gap-3">
                <button onClick={() => setStep(1)} className="rounded-full border-2 border-ink px-5 py-3 font-bold hover:bg-paper">
                  Back
                </button>
                <button
                  onClick={submit}
                  disabled={saving || picked.length === 0}
                  className="flex-1 rounded-full bg-ink py-3 text-lg font-black text-paper hover:bg-ink/85 disabled:opacity-40"
                >
                  {saving ? "Saving..." : "Show me what fits"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>}
    </div>
  );
}
