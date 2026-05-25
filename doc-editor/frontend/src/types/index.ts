// ---------- Document types (dynamic sections, S1/S1-1/... codes) ----------

export type BlockType = "text" | "equation" | "table";
export type Block = { type: BlockType; content: string };

export type SectionMeta = {
  code: string;   // "S1", "S1-1", "S2-1-1"
  title: string;
  level: number;  // 1 = H1, 2 = H2, ...
  children: string[];
};

export type Section = {
  meta: SectionMeta;
  blocks: Block[];
};

export type DocumentT = {
  sections: Record<string, Section>;
  outline: SectionMeta[];
};

// ---------- Chat / Edits ----------

export type Intent =
  | "edit"
  | "restructure"
  | "clarify"
  | "answer"
  | "";

export type ItemStatus = "pending" | "accepted" | "declined" | "instructed";

export type TokenUsage = { input: number; output: number; reasoning: number };

export type EditProposalMeta = {
  ref: string;
  action: "REWRITE" | "REPLACE" | "INSERT";
  target_desc?: string;
  summary?: string;
  content?: string;
  status?: ItemStatus;
  instruction?: string | null;
};

export type OutlineProposalMeta = {
  action: "RENAME" | "ADD" | "REMOVE" | "MERGE";
  target_desc?: string;
  summary?: string;
  status?: ItemStatus;
  instruction?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
  intent?: Intent | null;
  clarify_options?: string[] | null;
  edit_proposals?: EditProposalMeta[] | null;
  outline_proposals?: OutlineProposalMeta[] | null;
  picked_option_index?: number | null;
};

export type RewriteEdit = { action: "REWRITE"; value: string; summary?: string };
export type ReplaceEdit = { action: "REPLACE"; source: string; target: string; summary?: string };
export type InsertEdit  = { action: "INSERT"; value: Block; summary?: string };
export type Edit = RewriteEdit | ReplaceEdit | InsertEdit;

export type EditsMap = Record<string, Edit[]>;
export type EditItem = { ref: string; edit: Edit };

export type OutlineAction =
  | { action: "RENAME"; target: string; title: string }
  | { action: "ADD"; target: string | null; title: string; level?: number | null; position?: number | null }
  | { action: "REMOVE"; target: string }
  | { action: "MERGE"; targets: string[]; title?: string | null; level?: number | null };

export type EditEntry = {
  ref: string;
  edit: Edit;
  status: ItemStatus;
  instruction?: string;
};
export type OutlineEntry = {
  action: OutlineAction;
  status: ItemStatus;
  instruction?: string;
};

export type ChatResponse = {
  message: ChatMessage;
  edits: EditsMap;
  outline_actions?: OutlineAction[];
  intent?: Intent;
  suggest_new_session?: boolean;
  suggest_new_session_reason?: string | null;
  clarify_options?: string[];
  token_usage?: TokenUsage;
};

// ---------- Helpers ----------

export function parseRef(ref: string): { sectionCode: string; idx: number } | null {
  const semi = ref.lastIndexOf(";");
  if (semi === -1) return null;
  const sectionCode = ref.slice(0, semi);
  const idx = parseInt(ref.slice(semi + 1), 10);
  if (Number.isNaN(idx)) return null;
  return { sectionCode, idx };
}

export function makeRef(sectionCode: string, idx: number): string {
  return `${sectionCode};${idx}`;
}

export function flattenEdits(map: EditsMap): EditItem[] {
  const out: EditItem[] = [];
  for (const [ref, edits] of Object.entries(map)) {
    for (const edit of edits) out.push({ ref, edit });
  }
  return out;
}
