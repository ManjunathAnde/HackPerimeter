import { useEffect, useState } from "react";
import { draftEmail } from "../api";
import type { EmailDraft, Resource } from "../types";

export default function EmailDraftModal({ resource, onClose }: { resource: Resource; onClose: () => void }) {
  const [draft, setDraft] = useState<EmailDraft | null>(null);
  const [body, setBody] = useState("");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    draftEmail(resource.id)
      .then((d) => {
        setDraft(d);
        setSubject(d.subject);
        setBody(d.body);
      })
      .catch((e) => setError(e.message));
  }, [resource.id]);

  async function copy() {
    await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-xl flex-col gap-3 overflow-y-auto rounded-2xl border-2 border-ink bg-cream p-5 shadow-[6px_6px_0_0_#1E2527]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-black text-ink">Email to {resource.name}</h2>
          <button onClick={onClose} className="text-2xl font-bold leading-none text-ink/60 hover:text-ink" aria-label="Close">
            ×
          </button>
        </div>

        {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-800">{error}</p>}
        {!draft && !error && <p className="animate-pulse font-semibold text-accent-dark">Drafting with your profile...</p>}

        {draft && (
          <>
            <div className="text-sm">
              <span className="font-bold">To: </span>
              {draft.to ? (
                <a href={`mailto:${draft.to}`} className="text-accent-dark underline">{draft.to}</a>
              ) : (
                <span>
                  No email listed. Use the{" "}
                  <a href={draft.contact_url} target="_blank" rel="noreferrer" className="font-semibold text-accent-dark underline">
                    contact page
                  </a>
                  .
                </span>
              )}
            </div>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="rounded-lg border-2 border-ink/20 bg-white px-3 py-2 font-semibold outline-none focus:border-accent"
            />
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={11}
              className="rounded-lg border-2 border-ink/20 bg-white px-3 py-2 text-sm leading-relaxed outline-none focus:border-accent"
            />
            <div className="flex justify-end gap-2">
              {draft.to && (
                <a
                  href={`mailto:${draft.to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`}
                  className="rounded-xl border-2 border-ink px-4 py-2 font-bold hover:bg-white"
                >
                  Open in mail
                </a>
              )}
              <button onClick={copy} className="rounded-xl bg-accent px-4 py-2 font-bold text-white hover:bg-accent-dark">
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
