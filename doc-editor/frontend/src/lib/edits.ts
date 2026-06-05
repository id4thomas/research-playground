import type { Block, DocumentT, Edit, Section } from "../types";
import { findBlock, genId } from "../types";

/**
 * 텍스트 콘텐츠를 화면상 별도 블록 단위로 분할한다.
 * - text: 개행(\n)으로 나뉜 각 라인을 별도 블록으로. 빈 줄은 제외.
 * - equation/table: 분할하지 않고 단일 블록 유지.
 *
 * 첫 블록은 `keepId`(있으면)를 재사용하고, 나머지는 새 UUID를 부여한다.
 */
function splitTextValue(value: Block, keepId?: string): Block[] {
  const withId = (b: Omit<Block, "id">, first: boolean): Block => ({
    ...b,
    id: first && keepId ? keepId : genId(),
  });
  if (value.type !== "text") return [withId(value, true)];
  const parts = value.content
    .split(/\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (parts.length <= 1) return [withId(value, true)];
  return parts.map((content, i) => withId({ type: "text", content, format: value.format }, i === 0));
}

/** order 의 `at` 위치에 블록들을 끼워넣은 새 (blocks, order) 를 만든다. */
function spliceBlocks(section: Section, at: number, remove: number, insert: Block[]): Section {
  const order = [...section.order];
  const removedIds = order.splice(at, remove, ...insert.map((b) => b.id));
  const blocks: Record<string, Block> = { ...section.blocks };
  for (const id of removedIds) delete blocks[id];
  for (const b of insert) blocks[b.id] = b;
  return { ...section, blocks, order };
}

/**
 * edit 을 문서에 적용한 새 Document 를 반환한다. ref 는 대상 블록 UUID.
 * UUID 가 안정적이라 순서 보정(anchors)이 필요 없다 — 여러 edit 을 순차 accept 해도
 * 각자 자신의 블록 id 로 정확히 찾아간다.
 */
export function applyEdit(doc: DocumentT, ref: string, edit: Edit): DocumentT {
  const found = findBlock(doc, ref);

  // 대상 블록이 없으면(빈 섹션/이미 사라짐) REWRITE·INSERT 는 신규 블록 추가로 처리.
  if (!found) {
    if (edit.action === "REPLACE") return doc;
    const code = doc.outline[0]?.code;
    const section = code ? doc.sections[code] : undefined;
    if (!section || !code) return doc;
    const parts =
      edit.action === "REWRITE"
        ? splitTextValue({ id: ref, type: "text", content: edit.value, format: "markdown" })
        : splitTextValue(edit.value);
    const next = spliceBlocks(section, section.order.length, 0, parts);
    return { ...doc, sections: { ...doc.sections, [code]: next } };
  }

  const { code, section, index } = found;
  const target = section.blocks[ref];
  let next: Section;

  switch (edit.action) {
    case "REPLACE": {
      if (target.type !== "text") return doc;
      const replaced: Block = { ...target, content: target.content.split(edit.source).join(edit.target) };
      next = { ...section, blocks: { ...section.blocks, [ref]: replaced } };
      break;
    }
    case "REWRITE": {
      // 첫 블록은 ref id 유지, 분할되면 나머지는 새 id 로 뒤에 삽입.
      const parts = splitTextValue({ ...target, content: edit.value }, ref);
      next = spliceBlocks(section, index, 1, parts);
      break;
    }
    case "INSERT": {
      const parts = splitTextValue(edit.value);
      next = spliceBlocks(section, index + 1, 0, parts);
      break;
    }
  }

  return { ...doc, sections: { ...doc.sections, [code]: next } };
}

export type PreviewResult = {
  before: string;
  after: string;
  kind: "text" | "equation" | "table" | "new";
  // 적용 후 결과 블록 (렌더 미리보기용). format 분기 렌더링에 사용.
  afterBlock: Block;
};

export function previewBlock(doc: DocumentT, ref: string, edit: Edit): PreviewResult {
  const found = findBlock(doc, ref);
  const target = found ? found.section.blocks[ref] : undefined;
  const newText = (content: string): Block => ({ id: ref, type: "text", content, format: "markdown" });

  if (edit.action === "INSERT") {
    return {
      before: "",
      after: edit.value.content,
      kind: edit.value.type === "text" ? "new" : edit.value.type,
      afterBlock: edit.value,
    };
  }
  if (edit.action === "REPLACE") {
    if (!target) return { before: "", after: edit.target, kind: "new", afterBlock: newText(edit.target) };
    const after = target.content.split(edit.source).join(edit.target);
    return { before: target.content, after, kind: target.type, afterBlock: { ...target, content: after } };
  }
  // REWRITE
  if (!target) return { before: "", after: edit.value, kind: "new", afterBlock: newText(edit.value) };
  return { before: target.content, after: edit.value, kind: target.type, afterBlock: { ...target, content: edit.value } };
}
