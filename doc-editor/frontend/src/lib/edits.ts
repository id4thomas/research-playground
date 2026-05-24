import type { Block, DocumentT, Edit } from "../types";
import { parseRef } from "../types";

/**
 * 텍스트 콘텐츠를 화면상 별도 블록 단위로 분할한다.
 * - text: 개행(\n)으로 나뉜 각 라인을 별도 블록으로. 빈 줄은 제외.
 * - equation/table: 분할하지 않고 단일 블록 유지.
 */
function splitTextValue(value: Block): Block[] {
  if (value.type !== "text") return [value];
  const parts = value.content
    .split(/\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (parts.length <= 1) return [value];
  return parts.map((content) => ({ type: "text", content }));
}

/**
 * 섹션별 원본 인덱스 → 현재 인덱스 매핑.
 * 펜딩 edits가 도착했을 때의 블록 인덱스를 기준으로 ref가 만들어지므로,
 * 여러 edit을 순차적으로 accept할 때 이전 edit으로 밀린 위치를 보정한다.
 */
export type Anchors = Record<string, number[]>;

export function initAnchors(doc: DocumentT): Anchors {
  const out: Anchors = {};
  for (const [code, section] of Object.entries(doc.sections)) {
    out[code] = section.blocks.map((_, i) => i);
  }
  return out;
}

/**
 * edit을 적용하고, 영향받은 섹션의 anchor를 갱신한 새 anchors를 반환.
 * delta는 동일 섹션 내 origIdx > 적용 위치에 해당하는 anchor에만 더해진다.
 */
export function applyEditWithAnchors(
  doc: DocumentT,
  ref: string,
  edit: Edit,
  anchors: Anchors
): { doc: DocumentT; anchors: Anchors } {
  const parsed = parseRef(ref);
  if (!parsed) return { doc, anchors };
  const { sectionCode, idx: origIdx } = parsed;
  const section = doc.sections[sectionCode];
  if (!section) return { doc, anchors };

  const sectionAnchors = anchors[sectionCode] ?? section.blocks.map((_, i) => i);
  const curIdx = sectionAnchors[origIdx];

  const blocks = [...section.blocks];
  let delta = 0;
  // 빈 섹션(또는 잘못된 ref)에서 REWRITE/INSERT 들어오면 신규 블록 추가로 처리.
  const targetMissing = curIdx === undefined || blocks[curIdx] === undefined;

  switch (edit.action) {
    case "REPLACE": {
      if (targetMissing) return { doc, anchors };
      const target = blocks[curIdx as number];
      if (target.type !== "text") return { doc, anchors };
      blocks[curIdx as number] = { ...target, content: target.content.split(edit.source).join(edit.target) };
      break;
    }
    case "REWRITE": {
      if (targetMissing) {
        // 섹션에 블록이 없거나 ref가 유효치 않음 → 새 블록 삽입
        const parts = splitTextValue({ type: "text", content: edit.value });
        blocks.push(...parts);
        delta = parts.length;
      } else {
        const target = blocks[curIdx as number];
        const parts = splitTextValue({ ...target, content: edit.value });
        blocks.splice(curIdx as number, 1, ...parts);
        delta = parts.length - 1;
      }
      break;
    }
    case "INSERT": {
      const parts = splitTextValue(edit.value);
      if (targetMissing) {
        blocks.push(...parts);
      } else {
        blocks.splice((curIdx as number) + 1, 0, ...parts);
      }
      delta = parts.length;
      break;
    }
  }

  const nextSectionAnchors = sectionAnchors.map((cur, oi) =>
    oi > origIdx ? cur + delta : cur
  );

  return {
    doc: {
      ...doc,
      sections: {
        ...doc.sections,
        [sectionCode]: { ...section, blocks },
      },
    },
    anchors: { ...anchors, [sectionCode]: nextSectionAnchors },
  };
}

/** Backwards-compatible single-edit apply (no anchor tracking). */
export function applyEdit(doc: DocumentT, ref: string, edit: Edit): DocumentT {
  return applyEditWithAnchors(doc, ref, edit, initAnchors(doc)).doc;
}

export function previewBlock(
  doc: DocumentT,
  ref: string,
  edit: Edit
): { before: string; after: string; kind: "text" | "equation" | "table" | "new" } {
  const parsed = parseRef(ref);
  if (!parsed) return { before: "", after: "", kind: "text" };
  const { sectionCode, idx } = parsed;
  const section = doc.sections[sectionCode];
  const blocks: Block[] = section?.blocks ?? [];
  const target = blocks[idx];

  if (edit.action === "INSERT") {
    return { before: "", after: edit.value.content, kind: edit.value.type === "text" ? "new" : edit.value.type };
  }
  if (edit.action === "REPLACE") {
    if (!target) return { before: "", after: edit.target, kind: "new" };
    return {
      before: target.content,
      after: target.content.split(edit.source).join(edit.target),
      kind: target.type,
    };
  }
  // REWRITE
  if (!target) return { before: "", after: edit.value, kind: "new" };
  return { before: target.content, after: edit.value, kind: target.type };
}
