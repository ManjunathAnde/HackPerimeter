import { FormEvent, useEffect, useRef, useState } from "react";
import { getProfile, sendChat } from "../api";
import MatchCard from "../components/MatchCard";
import TracePanel from "../components/TracePanel";
import type { ChatTurn, Profile } from "../types";

const CAMPUS = { clarkston: "Clarkston" } as Record<string, string>;
const PATHWAY = { business_admin: "Business Administration" } as Record<string, string>;

function ProfileChip({ profile }: { profile: Profile }) {
  return (
    <div className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-full border-2 border-ink bg-white px-4 py-1.5 text-sm">
      <span className="font-extrabold">{profile.name}</span>
      <span className="text-ink/40">·</span>
      <span>{CAMPUS[profile.campus] ?? profile.campus}</span>
      <span className="text-ink/40">·</span>
      <span>{PATHWAY[profile.pathway_id] ?? profile.pathway_id}</span>
      <span className="text-ink/40">·</span>
      <span>{profile.credits} credits</span>
      <span className="text-ink/40">·</span>
      <span className="text-accent-dark">interests: {profile.topics.join(", ")}</span>
    </div>
  );
}

export default function ChatPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getProfile().then(setProfile).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || loading) return;
    const history = turns.map(({ role, content }) => ({ role, content }));
    setTurns((t) => [...t, { role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const response = await sendChat(message, history);
      setTurns((t) => [...t, { role: "assistant", content: response.answer, response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 pb-6 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3 py-5">
        <h1 className="text-3xl font-black tracking-tight text-ink">
          Path<span className="text-accent">finder</span>
        </h1>
        {profile && <ProfileChip profile={profile} />}
      </header>

      <main className="flex flex-1 flex-col gap-6 py-4">
        {turns.length === 0 && !loading && (
          <section className="rounded-2xl border-2 border-dashed border-ink/30 p-8 text-center">
            <h2 className="text-2xl font-black text-ink">What are you working toward?</h2>
            <p className="mt-2 text-ink/70">
              Tell me what's going on. I'll find GSU programs, people and events that fit, with sources.
            </p>
          </section>
        )}

        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-ink px-4 py-3 text-cream">
              {turn.content}
            </div>
          ) : (
            <div key={i} className="flex flex-col gap-4">
              <div className="max-w-[85%] rounded-2xl rounded-bl-sm border-2 border-ink bg-white px-4 py-3">
                <p>{turn.content}</p>
                {turn.response?.first_step && (
                  <p className="mt-2 text-sm">
                    <span className="font-bold text-accent-dark">Start here: </span>
                    {turn.response.first_step}
                  </p>
                )}
              </div>
              {turn.response && turn.response.matches.length > 0 && (
                <div className="grid gap-4 md:grid-cols-3">
                  {turn.response.matches.map((m) => (
                    <MatchCard key={m.resource.id} match={m} />
                  ))}
                </div>
              )}
              {turn.response && <TracePanel response={turn.response} />}
            </div>
          ),
        )}

        {loading && <p className="animate-pulse font-semibold text-accent-dark">Searching GSU sources...</p>}
        {error && <p className="rounded-xl border-2 border-red-700 bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>}
        <div ref={bottomRef} />
      </main>

      <form onSubmit={onSubmit} className="sticky bottom-4 flex gap-2 rounded-2xl border-2 border-ink bg-white p-2 shadow-[4px_4px_0_0_#111]">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about programs, holds, events, next steps..."
          className="flex-1 bg-transparent px-3 py-2 outline-none placeholder:text-ink/40"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-accent px-5 py-2 font-bold text-white hover:bg-accent-dark disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
