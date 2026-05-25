/**
 * 백엔드(API)로 보낼 messages 페이로드를 생성한다.
 *
 * 이전엔 모든 메타데이터(어시스턴트 인텐트, 제안 목록, 사용자 결정)를 텍스트로
 * 본문에 펴 발랐지만, 이제는 ChatMessage 의 정식 필드(intent, clarify_options,
 * edit_proposals, outline_proposals, picked_option_index)로 그대로 넘겨 서버가
 * LLM용 포맷팅을 담당한다.
 */
import type {
  ChatMessage,
  DocumentT,
  Edit,
  EditEntry,
  EditProposalMeta,
  OutlineEntry,
  OutlineProposalMeta,
} from "../types";
import { parseRef } from "../types";
import type { MsgWithIntent } from "../App";

function sectionTitle(doc: DocumentT, code: string | null | undefined): string {
  if (!code) return "(루트)";
  return doc.sections[code]?.meta.title ?? code;
}

function editContent(edit: Edit): string {
  if (edit.action === "REWRITE") return edit.value;
  if (edit.action === "REPLACE") return `"${edit.source}" → "${edit.target}"`;
  return edit.value.content;
}

function editTargetDesc(ref: string, doc: DocumentT): string {
  const p = parseRef(ref);
  if (!p) return ref;
  return `'${sectionTitle(doc, p.sectionCode)}' 섹션 ${p.idx + 1}번째 블록 (${ref})`;
}

function toEditProposal(e: EditEntry, doc: DocumentT): EditProposalMeta {
  return {
    ref: e.ref,
    action: e.edit.action,
    target_desc: editTargetDesc(e.ref, doc),
    summary: e.edit.summary ?? "",
    content: editContent(e.edit),
    status: e.status,
    instruction: e.instruction ?? null,
  };
}

function outlineTargetDesc(entry: OutlineEntry, doc: DocumentT): string {
  const a = entry.action;
  if (a.action === "RENAME") return `'${sectionTitle(doc, a.target)}' (${a.target}) → '${a.title}'`;
  if (a.action === "ADD")
    return `'${sectionTitle(doc, a.target)}' (${a.target ?? "루트"}) 아래에 '${a.title}' 추가`;
  if (a.action === "REMOVE") return `'${sectionTitle(doc, a.target)}' (${a.target}) 섹션 삭제`;
  // MERGE
  const list = a.targets.map((c) => `'${sectionTitle(doc, c)}'`).join(", ");
  const survivor = a.title ?? sectionTitle(doc, a.targets[0]);
  return `[${list}] → '${survivor}' 병합`;
}

function toOutlineProposal(e: OutlineEntry, doc: DocumentT): OutlineProposalMeta {
  return {
    action: e.action.action,
    target_desc: outlineTargetDesc(e, doc),
    summary: "",
    status: e.status,
    instruction: e.instruction ?? null,
  };
}

export function serializeMessages(messages: MsgWithIntent[], doc: DocumentT): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      out.push({
        role: "user",
        content: m.content,
        picked_option_index: m.pickedOptionIndex ?? null,
      });
    } else if (m.role === "assistant") {
      out.push({
        role: "assistant",
        content: m.content,
        intent: m.intent ?? null,
        clarify_options: m.clarifyOptions ?? null,
        edit_proposals: m.editEntries?.length
          ? m.editEntries.map((e) => toEditProposal(e, doc))
          : null,
        outline_proposals: m.outlineEntries?.length
          ? m.outlineEntries.map((e) => toOutlineProposal(e, doc))
          : null,
      });
    } else {
      out.push({ role: m.role, content: m.content });
    }
  }
  return out;
}
