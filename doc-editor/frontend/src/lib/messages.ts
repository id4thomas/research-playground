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
  InteractionAction,
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

function editToAction(e: EditEntry, doc: DocumentT): InteractionAction {
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
    return { ...common, action: "REWRITE", block: rewriteBlock(e.ref, edit.value, doc) };
  }
  if (edit.action === "REPLACE") {
    return { ...common, action: "REPLACE", source: edit.source, target: edit.target };
  }
  return { ...common, action: "INSERT", block: edit.value };
}

function outlineToAction(e: OutlineEntry, doc: DocumentT): InteractionAction {
  const a = e.action;
  const common = {
    scope: "outline" as const,
    summary: "",
    status: e.status,
    instruction: e.instruction ?? null,
  };
  if (a.action === "RENAME") {
    return { ...common, action: "RENAME", ref: a.target, title: a.title,
      target_desc: `'${sectionTitle(doc, a.target)}' 섹션` };
  }
  if (a.action === "ADD") {
    return { ...common, action: "ADD", ref: a.target, title: a.title, level: a.level ?? null, position: a.position ?? null,
      target_desc: `'${sectionTitle(doc, a.target)}' 섹션` };
  }
  if (a.action === "REMOVE") {
    return { ...common, action: "REMOVE", ref: a.target,
      target_desc: `'${sectionTitle(doc, a.target)}' 섹션` };
  }
  // MERGE
  return { ...common, action: "MERGE", ref: a.targets[0] ?? null, targets: a.targets,
    title: a.title ?? null, level: a.level ?? null,
    target_desc: `'${sectionTitle(doc, a.targets[0])}' 섹션` };
}

export function serializeMessages(messages: MsgWithIntent[], doc: DocumentT): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      out.push({
        type: "base",
        role: "user",
        content: m.content,
        picked_option_index: m.pickedOptionIndex ?? null,
      });
    } else if (m.role === "assistant") {
      const actions: InteractionAction[] = [
        ...(m.outlineEntries ?? []).map((e) => outlineToAction(e, doc)),
        ...(m.editEntries ?? []).map((e) => editToAction(e, doc)),
      ];
      if (actions.length) {
        out.push({
          type: "interaction",
          role: "assistant",
          content: m.content,
          intent: m.intent ?? null,
          clarify_options: m.clarifyOptions ?? null,
          actions,
        });
      } else {
        out.push({
          type: "base",
          role: "assistant",
          content: m.content,
          intent: m.intent ?? null,
          clarify_options: m.clarifyOptions ?? null,
        });
      }
    } else {
      out.push({ type: "base", role: m.role, content: m.content });
    }
  }
  return out;
}

// ---------- 응답 message.actions → 내부 편집 모델 ----------

export function actionsToEntries(actions: InteractionAction[]): {
  editEntries: EditEntry[];
  outlineEntries: OutlineEntry[];
} {
  const editEntries: EditEntry[] = [];
  const outlineEntries: OutlineEntry[] = [];
  for (const a of actions) {
    const status = a.status ?? "pending";
    const instruction = a.instruction ?? undefined;
    if (a.scope === "block") {
      if (a.action === "REWRITE") {
        editEntries.push({ ref: a.ref, status, instruction,
          edit: { action: "REWRITE", value: a.block.content, summary: a.summary } });
      } else if (a.action === "REPLACE") {
        editEntries.push({ ref: a.ref, status, instruction,
          edit: { action: "REPLACE", source: a.source, target: a.target, summary: a.summary } });
      } else {
        editEntries.push({ ref: a.ref, status, instruction,
          edit: { action: "INSERT", value: a.block, summary: a.summary } });
      }
    } else {
      if (a.action === "RENAME") {
        outlineEntries.push({ status, instruction, action: { action: "RENAME", target: a.ref, title: a.title } });
      } else if (a.action === "ADD") {
        outlineEntries.push({ status, instruction,
          action: { action: "ADD", target: a.ref, title: a.title, level: a.level ?? null, position: a.position ?? null } });
      } else if (a.action === "REMOVE") {
        outlineEntries.push({ status, instruction, action: { action: "REMOVE", target: a.ref ?? "" } });
      } else {
        outlineEntries.push({ status, instruction,
          action: { action: "MERGE", targets: a.targets, title: a.title ?? null, level: a.level ?? null } });
      }
    }
  }
  return { editEntries, outlineEntries };
}
