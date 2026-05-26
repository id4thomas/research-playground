import type { ChatMessage, ChatResponse, DocumentT } from "../types";

const BASE = "";

type ApiResponse<T> = { code: number; message: string; data: T | null };

async function unwrap<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await r.text());
  const body = (await r.json()) as ApiResponse<T>;
  if (body.code !== 0 || body.data === null) {
    throw new Error(body.message || `API error (code=${body.code})`);
  }
  return body.data;
}

export async function uploadMarkdown(file: File): Promise<DocumentT> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`${BASE}/api/parse`, { method: "POST", body: form });
  return unwrap<DocumentT>(r);
}

type ChatArgs = {
  project_id: string;
  messages: ChatMessage[];
  document: DocumentT;
  selected?: string[];
};

async function post(path: string, args: ChatArgs): Promise<ChatResponse> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ data: args }),
  });
  return unwrap<ChatResponse>(r);
}

export const chat        = (args: ChatArgs) => post("/api/chat", args);
export const edit        = (args: ChatArgs) => post("/api/chat/edit", args);
export const restructure = (args: ChatArgs) => post("/api/chat/restructure", args);
export const answer      = (args: ChatArgs) => post("/api/chat/answer", args);
export const clarify     = (args: ChatArgs) => post("/api/chat/clarify", args);

export type IntentSlash = "edit" | "restructure" | "answer" | "clarify";

/** Parse `\edit ...`, `\restructure ...`, etc. Returns null if no slash directive. */
export function parseSlashDirective(text: string): { intent: IntentSlash; body: string } | null {
  const m = text.match(/^\\(edit|restructure|answer|clarify)\b\s*(.*)$/s);
  if (!m) return null;
  return { intent: m[1] as IntentSlash, body: m[2].trim() };
}

export function endpointForIntent(intent: IntentSlash): string {
  return `/api/chat/${intent}`;
}

export function callForIntent(intent: IntentSlash, args: ChatArgs): Promise<ChatResponse> {
  switch (intent) {
    case "edit":        return edit(args);
    case "restructure": return restructure(args);
    case "answer":      return answer(args);
    case "clarify":     return clarify(args);
  }
}
