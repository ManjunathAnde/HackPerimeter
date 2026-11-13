import type { ChatResponse, EmailDraft, Profile } from "./types";

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
