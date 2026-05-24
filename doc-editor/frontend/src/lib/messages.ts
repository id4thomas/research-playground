/**
 * 백엔드(API)로 보낼 messages 페이로드를 생성하는 직렬화 레이어.
 *
 * 현재 채팅 히스토리는 단순한 텍스트 외에도 어시스턴트가 제안한 블록 수정
 * (editEntries) / 섹션 구조 변경(outlineEntries) 과 그에 대한 사용자 결정
 * (accepted / declined / instructed) 을 함께 보관한다. LLM이 이전 턴의 맥락을
 * 이해하려면 이 정보가 messages 배열에 텍스트로 녹아 들어야 한다.
 *
 * 직렬화 규칙:
 *  1) 사용자 메시지는 그대로 user role 로 emit.
 *  2) 어시스턴트 메시지는 본문 뒤에 "[블록 수정 제안 #N]" / "[섹션 구조 변경
 *     제안 #N]" 형식으로 모든 제안 요약을 덧붙인 뒤 assistant role 로 emit.
 *  3) 어시스턴트 메시지에 결정된 항목이 하나라도 있으면, 직후에 user role 의
 *     "[직전 제안 검토 결과]" 메시지를 추가해 수락/거절/직접지시 사실을 LLM에
 *     알려준다.
 */
import type { ChatMessage, DocumentT, Edit, EditEntry, OutlineAction, OutlineEntry } from "../types";
import { parseRef } from "../types";
import type { MsgWithIntent } from "../App";

const TRUNC = 200;

function shorten(s: string, n = TRUNC): string {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function sectionTitle(doc: DocumentT, code: string | null | undefined): string {
  if (!code) return "(루트)";
  return doc.sections[code]?.meta.title ?? code;
}

function describeEdit(ref: string, edit: Edit, doc: DocumentT): string {
  const p = parseRef(ref);
  const where = p ? `'${sectionTitle(doc, p.sectionCode)}' (${p.sectionCode}) ${p.idx + 1}번째 블록 (ref: ${ref})` : ref;
  if (edit.action === "REWRITE") return `${where} 전체 재작성 → "${shorten(edit.value)}"`;
  if (edit.action === "REPLACE")
    return `${where} 문자열 치환: "${shorten(edit.source, 60)}" → "${shorten(edit.target, 60)}"`;
  return `${where} 아래에 ${edit.value.type} 블록 삽입 → "${shorten(edit.value.content)}"`;
}

function describeOutline(action: OutlineAction, doc: DocumentT): string {
  if (action.action === "RENAME")
    return `'${sectionTitle(doc, action.target)}' (${action.target}) → '${action.title}'으로 이름 변경`;
  if (action.action === "ADD")
    return `'${sectionTitle(doc, action.target)}' (${action.target}) 아래에 '${action.title}' 섹션 추가 (level=${action.level ?? "auto"})`;
  if (action.action === "REMOVE")
    return `'${sectionTitle(doc, action.target)}' (${action.target}) 섹션 삭제 (본문 포함)`;
  // MERGE
  const list = action.targets.map((c) => `'${sectionTitle(doc, c)}' (${c})`).join(", ");
  const survivor = action.title ?? sectionTitle(doc, action.targets[0]);
  return `섹션 병합 [${list}] → '${survivor}'`;
}

function statusLabel(entry: { status: EditEntry["status"]; instruction?: string }): string | null {
  if (entry.status === "accepted") return "수락";
  if (entry.status === "declined") return "거절";
  if (entry.status === "instructed") return `직접 지시: "${shorten(entry.instruction ?? "", 200)}"`;
  return null; // pending
}

export function serializeMessages(messages: MsgWithIntent[], doc: DocumentT): ChatMessage[] {
  const out: ChatMessage[] = [];

  for (const m of messages) {
    if (m.role === "user") {
      out.push({ role: "user", content: m.content });
      continue;
    }

    // assistant: 본문 + 제안 요약
    let content = m.content || "";
    const proposals: string[] = [];
    m.editEntries?.forEach((e, i) => {
      proposals.push(`[블록 수정 제안 #${i + 1}] ${describeEdit(e.ref, e.edit, doc)}`);
    });
    m.outlineEntries?.forEach((e, i) => {
      proposals.push(`[섹션 구조 변경 제안 #${i + 1}] ${describeOutline(e.action, doc)}`);
    });
    if (proposals.length) {
      content = (content ? content + "\n\n" : "") + proposals.join("\n");
    }
    out.push({ role: "assistant", content });

    // 결정 결과: 별도 user 메시지로 덧붙여 LLM이 사용자 응답으로 인지하게 함
    const decisions: string[] = [];
    m.editEntries?.forEach((e, i) => {
      const label = statusLabel(e);
      if (label) decisions.push(`[블록 수정 제안 #${i + 1}] → ${label}`);
    });
    m.outlineEntries?.forEach((e, i) => {
      const label = statusLabel(e);
      if (label) decisions.push(`[섹션 구조 변경 제안 #${i + 1}] → ${label}`);
    });
    if (decisions.length) {
      out.push({
        role: "user",
        content: "[직전 제안 검토 결과]\n" + decisions.join("\n"),
      });
    }
  }

  return out;
}
