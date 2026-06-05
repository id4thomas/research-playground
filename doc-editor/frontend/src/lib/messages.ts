/**
 * 백엔드(API)로 보낼 messages 페이로드(wire ChatMessage)를 생성한다.
 *
 * 어시스턴트 턴의 제안/사용자 결정은 구조화된 `actions[]`(블록 UUID 참조)로 그대로
 * 실어 보내고, 서버가 LLM용 직렬화를 담당한다. user 턴은 단순 base 메시지.
 */
import type {
  Block,
  ChatMessage,
  DocumentT,
  Edit,
  EditEntry,
  Interaction,
  OutlineEntry,
} from "../types";
import { findBlock, DEFAULT_FORMAT } from "../types";
import type { MsgWithIntent } from "../App";

function sectionTitle(doc: DocumentT, code: string | null | undefined): string {
  if (!code) return "(루트)";
  return doc.sections[code]?.meta.title ?? code;
}

function blockTargetDesc(ref: string, doc: DocumentT): string {
  const found = findBlock(doc, ref);
  if (!found) return "";
  return `'${found.section.meta.title}' 섹션 내 블록`;
}

/** REWRITE 시 wire 에 실을 Block 을 만든다 (원본 타입/format/id 보존). */
function rewriteBlock(ref: string, value: string, doc: DocumentT): Block {
  const found = findBlock(doc, ref);
  const orig = found?.section.blocks[ref];
  const type = orig?.type ?? "text";
  return { id: ref, type, content: value, format: orig?.format ?? DEFAULT_FORMAT[type] };
}

function editToInteraction(e: EditEntry, doc: DocumentT): Interaction {
  const common = {
    scope: "block" as const,
    ref: e.ref,
    summary: e.edit.summary ?? "",
    target_desc: blockTargetDesc(e.ref, doc),
    status: e.status,
    instruction: e.instruction ?? null,
  };
  const edit: Edit = e.edit;
  if (edit.action === "REWRITE") {
    return { ...common, edit: { action: "REWRITE", block: rewriteBlock(e.ref, edit.value, doc), summary: edit.summary } };
  }
  if (edit.action === "REPLACE") {
    return { ...common, edit: { action: "REPLACE", source: edit.source, target: edit.target, summary: edit.summary } };
  }
  return { ...common, edit: { action: "INSERT", block: edit.value, summary: edit.summary } };
}

function outlineToInteraction(e: OutlineEntry, doc: DocumentT): Interaction {
  const a = e.action;
  const ref = a.action === "MERGE" ? (a.targets[0] ?? null) : a.target;
  const common = {
    scope: "outline" as const,
    summary: "",
    status: e.status,
    instruction: e.instruction ?? null,
    target_desc: `'${sectionTitle(doc, ref)}' 섹션`,
  };
  if (a.action === "RENAME") {
    return { ...common, outline: { action: "RENAME", target: a.target, title: a.title } };
  }
  if (a.action === "ADD") {
    return { ...common, outline: { action: "ADD", target: a.target, title: a.title, level: a.level ?? null, position: a.position ?? null } };
  }
  if (a.action === "REMOVE") {
    return { ...common, outline: { action: "REMOVE", target: a.target } };
  }
  // MERGE
  return { ...common, outline: { action: "MERGE", targets: a.targets, title: a.title ?? null, level: a.level ?? null } };
}

export function serializeMessages(messages: MsgWithIntent[], doc: DocumentT): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      // 직전 clarify 선택지를 고른 경우 option_reply, 아니면 base.
      if (m.pickedOptionIndex != null) {
        out.push({ type: "option_reply", role: "user", content: m.content, picked_option_index: m.pickedOptionIndex });
      } else {
        out.push({ type: "base", role: "user", content: m.content });
      }
    } else if (m.role === "assistant") {
      const interactions: Interaction[] = [
        ...(m.outlineEntries ?? []).map((e) => outlineToInteraction(e, doc)),
        ...(m.editEntries ?? []).map((e) => editToInteraction(e, doc)),
      ];
      if (interactions.length) {
        out.push({ type: "interaction", role: "assistant", content: m.content, interactions });
      } else if (m.clarifyOptions?.length) {
        out.push({ type: "clarify", role: "assistant", content: m.content, clarify_options: m.clarifyOptions });
      } else {
        out.push({ type: "base", role: "assistant", content: m.content });
      }
    } else {
      out.push({ type: "base", role: m.role, content: m.content });
    }
  }
  return out;
}

// ---------- 응답 message.interactions → 내부 편집 모델 ----------

export function interactionsToEntries(interactions: Interaction[]): {
  editEntries: EditEntry[];
  outlineEntries: OutlineEntry[];
} {
  const editEntries: EditEntry[] = [];
  const outlineEntries: OutlineEntry[] = [];
  for (const i of interactions) {
    const status = i.status ?? "pending";
    const instruction = i.instruction ?? undefined;
    if (i.scope === "block") {
      const e = i.edit;
      if (e.action === "REWRITE") {
        editEntries.push({ ref: i.ref, status, instruction,
          edit: { action: "REWRITE", value: e.block.content, summary: e.summary } });
      } else if (e.action === "REPLACE") {
        editEntries.push({ ref: i.ref, status, instruction,
          edit: { action: "REPLACE", source: e.source, target: e.target, summary: e.summary } });
      } else {
        editEntries.push({ ref: i.ref, status, instruction,
          edit: { action: "INSERT", value: e.block, summary: e.summary } });
      }
    } else {
      const o = i.outline;
      if (o.action === "RENAME") {
        outlineEntries.push({ status, instruction, action: { action: "RENAME", target: o.target, title: o.title ?? "" } });
      } else if (o.action === "ADD") {
        outlineEntries.push({ status, instruction,
          action: { action: "ADD", target: o.target, title: o.title ?? "", level: o.level ?? null, position: o.position ?? null } });
      } else if (o.action === "REMOVE") {
        outlineEntries.push({ status, instruction, action: { action: "REMOVE", target: o.target } });
      } else {
        outlineEntries.push({ status, instruction,
          action: { action: "MERGE", targets: o.targets, title: o.title ?? null, level: o.level ?? null } });
      }
    }
  }
  return { editEntries, outlineEntries };
}
