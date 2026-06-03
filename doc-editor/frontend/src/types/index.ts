// ---------- Document types (UUID 기반 블록) ----------

export type BlockType = "text" | "equation" | "table";
// 콘텐츠 표현 포맷. 허용값은 타입마다 다르다: text/table=markdown|html, equation=tex|html.
export type BlockFormat = "markdown" | "html" | "tex";
// 블록은 안정적인 UUID(`id`)로 식별된다. 편집/삽입/삭제가 누적돼도 id는 불변.
export type Block = { id: string; type: BlockType; content: string; format: BlockFormat };

/** 블록 타입별 기본 format (서버 _DEFAULT_FORMAT 과 일치). */
export const DEFAULT_FORMAT: Record<BlockType, BlockFormat> = {
  text: "markdown",
  table: "html",
  equation: "tex",
};

export type SectionMeta = {
  code: string;   // "S1", "S1-1", "S2-1-1"
  title: string;
  level: number;  // 1 = H1, 2 = H2, ...
  children: string[];
};

// 블록을 id로 보관(`blocks`)하고 표시 순서는 `order`로 분리한다 (서버 Section과 동일).
export type Section = {
  meta: SectionMeta;
  blocks: Record<string, Block>;
  order: string[];
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

// ---------- Wire 메시지 스펙 (서버 core/data/chat.py 와 1:1) ----------

type ActionBase = {
  status?: ItemStatus;
  summary?: string;
  target_desc?: string;
  instruction?: string | null;
};

export type RewriteBlockAction = ActionBase & {
  scope: "block"; action: "REWRITE"; ref: string; block: Block;
};
export type ReplaceBlockAction = ActionBase & {
  scope: "block"; action: "REPLACE"; ref: string; source: string; target: string;
};
export type InsertBlockAction = ActionBase & {
  scope: "block"; action: "INSERT"; ref: string; block: Block;
};
export type BlockAction = RewriteBlockAction | ReplaceBlockAction | InsertBlockAction;

export type AddOutlineAction = ActionBase & {
  scope: "outline"; action: "ADD"; ref: string | null; title: string; level?: number | null; position?: number | null;
};
export type MergeOutlineAction = ActionBase & {
  scope: "outline"; action: "MERGE"; ref: string | null; targets: string[]; title?: string | null; level?: number | null;
};
export type RenameOutlineAction = ActionBase & {
  scope: "outline"; action: "RENAME"; ref: string; title: string;
};
export type RemoveOutlineAction = ActionBase & {
  scope: "outline"; action: "REMOVE"; ref: string;
};
export type OutlineActionWire =
  | AddOutlineAction | MergeOutlineAction | RenameOutlineAction | RemoveOutlineAction;

export type InteractionAction = BlockAction | OutlineActionWire;

export type BaseChatMessage = {
  type: "base";
  role: "user" | "assistant" | "system";
  content: string;
  intent?: Intent | null;
  clarify_options?: string[] | null;
  picked_option_index?: number | null;
};
export type InteractionChatMessage = Omit<BaseChatMessage, "type"> & {
  type: "interaction";
  actions: InteractionAction[];
};
export type ChatMessage = BaseChatMessage | InteractionChatMessage;

// ---------- 내부 편집 모델 (컴포넌트에서 사용) ----------

export type RewriteEdit = { action: "REWRITE"; value: string; summary?: string };
export type ReplaceEdit = { action: "REPLACE"; source: string; target: string; summary?: string };
export type InsertEdit  = { action: "INSERT"; value: Block; summary?: string };
export type Edit = RewriteEdit | ReplaceEdit | InsertEdit;

export type EditsMap = Record<string, Edit[]>;
export type EditItem = { ref: string; edit: Edit };

// 내부에서 다루기 쉬운 outline 표현 (target/targets 기반). wire 와는 messages.ts 에서 변환.
export type OutlineAction =
  | { action: "RENAME"; target: string; title: string }
  | { action: "ADD"; target: string | null; title: string; level?: number | null; position?: number | null }
  | { action: "REMOVE"; target: string }
  | { action: "MERGE"; targets: string[]; title?: string | null; level?: number | null };

export type EditEntry = {
  ref: string;            // 대상 블록 UUID (INSERT 는 앵커 블록 UUID)
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
  message: InteractionChatMessage;
  intent?: Intent;
  suggest_new_session?: boolean;
  suggest_new_session_reason?: string | null;
  token_usage?: TokenUsage;
};

// ---------- Helpers ----------

/** 블록 UUID 생성 (서버 hex 형식과 맞춤). */
export function genId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

/** 블록 UUID 로 (섹션 코드, 섹션, order 내 위치) 를 찾는다. */
export function findBlock(
  doc: DocumentT,
  id: string
): { code: string; section: Section; index: number } | null {
  for (const [code, section] of Object.entries(doc.sections)) {
    const index = section.order.indexOf(id);
    if (index !== -1) return { code, section, index };
  }
  return null;
}

/** 표시 순서대로 블록을 반환. */
export function orderedBlocks(section: Section): Block[] {
  return section.order.map((id) => section.blocks[id]).filter(Boolean);
}

export function flattenEdits(map: EditsMap): EditItem[] {
  const out: EditItem[] = [];
  for (const [ref, edits] of Object.entries(map)) {
    for (const edit of edits) out.push({ ref, edit });
  }
  return out;
}
