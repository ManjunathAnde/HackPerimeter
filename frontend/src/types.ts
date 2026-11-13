export interface Profile {
  name: string;
  campus: string;
  pathway_id: string;
  credits: number;
  work_hours: number;
  holds: string[];
  interests: string;
  topics: string[];
}

export interface Resource {
  id: string;
  source_id: string;
  name: string;
  type: string;
  campus: string;
  topics: string[];
  summary: string;
  how_to_start: string | null;
  contact_office: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  location_building: string | null;
  location_room: string | null;
  event_start: string | null;
  source_url: string;
  fetched_at: string;
}

export interface Match {
  resource: Resource;
  why: string;
  first_step: string;
}

export interface TraceStep {
  step: string;
  detail: string;
  ms: number;
}

export interface ChatResponse {
  answer: string;
  first_step: string;
  matches: Match[];
  trace: TraceStep[];
  verification: { checker: string | null; removed_sentences: string[] };
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

export interface EmailDraft {
  to: string | null;
  subject: string;
  body: string;
  contact_url: string;
}

export interface Alert {
  id: number;
  resource_id: string;
  message: string;
  created_at: string;
  read: number;
  resource_name: string | null;
  source_url: string | null;
}

export interface Source {
  id: string;
  url: string;
  kind: string;
  campus: string;
  last_run_at: string | null;
  last_changed_at: string | null;
  last_status: string | null;
  last_error: string | null;
  rows_new: number | null;
  rows_changed: number | null;
  rows_dropped: number | null;
  rows_total: number;
}

export interface RunResult {
  run: { source_id: string; rows_new: number; rows_changed: number; rows_unchanged: number; rows_dropped: number; error: string | null };
  alerts_created: number;
}
