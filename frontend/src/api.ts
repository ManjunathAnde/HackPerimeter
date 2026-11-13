import type { Alert, ChatResponse, EmailDraft, KbStats, Profile, Roadmap, RunResult, Source } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export const getProfile = () => request<Profile>("/profile");

export const sendChat = (message: string, history: { role: string; content: string }[]) =>
  request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message, history }) });

export const draftEmail = (resource_id: string) =>
  request<EmailDraft>("/draft-email", { method: "POST", body: JSON.stringify({ resource_id }) });

export const getAlerts = (unreadOnly = true) => request<Alert[]>(`/alerts${unreadOnly ? "?unread=1" : ""}`);

export const markAlertRead = (id: number) => request<{ ok: boolean }>(`/alerts/${id}/read`, { method: "POST" });

export const getSources = () => request<Source[]>("/sources");

export const runSource = (id: string) => request<RunResult>(`/sources/${id}/run`, { method: "POST" });

export const runAll = () => request<{ runs: RunResult["run"][]; alerts_created: number }>("/ingest/run-all", { method: "POST" });

export const getPathways = () => request<Roadmap["pathway"][]>("/pathways");

export const getRoadmap = (id: string) => request<Roadmap>(`/pathways/${id}/roadmap`);

export const getStats = () => request<KbStats>("/stats");
