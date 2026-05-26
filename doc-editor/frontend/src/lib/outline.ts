import type { DocumentT, OutlineAction, Section, SectionMeta } from "../types";

/**
 * Recompute S-codes for the outline based on each section's level.
 * Rebuilds the sections dict keyed by new codes and returns a fresh Document.
 * Sections must be in display order (flat list); levels define hierarchy.
 */
function recomputeCodes(
  flatSections: { meta: SectionMeta; blocks: Section["blocks"] }[]
): DocumentT {
  const counters: number[] = [];
  const newOutline: SectionMeta[] = [];
  const newSections: Record<string, Section> = {};

  // First pass: assign codes
  const codes: string[] = flatSections.map(({ meta }) => {
    const level = meta.level;
    if (level > counters.length) {
      while (counters.length < level) counters.push(0);
    } else {
      counters.length = level;
    }
    counters[level - 1]++;
    return "S" + counters.slice(0, level).join("-");
  });

  // Second pass: build outline & section dict (children populated via lookahead)
  for (let i = 0; i < flatSections.length; i++) {
    const { meta, blocks } = flatSections[i];
    const code = codes[i];
    const children: string[] = [];
    for (let j = i + 1; j < flatSections.length; j++) {
      if (flatSections[j].meta.level === meta.level + 1) {
        children.push(codes[j]);
      } else if (flatSections[j].meta.level <= meta.level) {
        break;
      }
    }
    const newMeta: SectionMeta = { ...meta, code, children };
    newOutline.push(newMeta);
    newSections[code] = { meta: newMeta, blocks };
  }

  return { sections: newSections, outline: newOutline };
}

function docToFlat(doc: DocumentT): { meta: SectionMeta; blocks: Section["blocks"] }[] {
  // outline already holds the display order
  return doc.outline.map((m) => {
    const s = doc.sections[m.code];
    return { meta: { ...m }, blocks: s ? s.blocks : [] };
  });
}

/** Index of `target` in the flat list, or -1. */
function indexOfCode(
  flat: { meta: SectionMeta }[],
  code: string
): number {
  return flat.findIndex((s) => s.meta.code === code);
}

/** Index where a child of `parentCode` at sibling position `position` should be inserted. */
function insertionIndex(
  flat: { meta: SectionMeta }[],
  parentCode: string | null,
  position: number | null,
  newLevel: number
): number {
  if (!parentCode) {
    // Root-level insertion: among sections with level === newLevel
    const rootCount = flat.filter((s) => s.meta.level === newLevel).length;
    const pos = position === null || position === undefined ? rootCount : position;
    // Find the n-th level==newLevel section; insert before it (or end)
    let seen = 0;
    for (let i = 0; i < flat.length; i++) {
      if (flat[i].meta.level === newLevel) {
        if (seen === pos) return i;
        seen++;
      }
    }
    return flat.length;
  }

  const pIdx = indexOfCode(flat, parentCode);
  if (pIdx === -1) return flat.length;
  const parentLevel = flat[pIdx].meta.level;

  // Walk through subtree, count direct children (level == parentLevel+1)
  const childLevel = parentLevel + 1;
  let seen = 0;
  let i = pIdx + 1;
  let insertAt = flat.length;
  // Default: append after entire subtree
  while (i < flat.length && flat[i].meta.level > parentLevel) {
    if (flat[i].meta.level === childLevel) {
      if (position !== null && position !== undefined && seen === position) {
        return i;
      }
      seen++;
    }
    i++;
  }
  insertAt = i;
  return insertAt;
}

/** Remove the section at `idx` and all of its descendants (deeper-level following entries). */
function removeSubtree(
  flat: { meta: SectionMeta; blocks: Section["blocks"] }[],
  idx: number
): { meta: SectionMeta; blocks: Section["blocks"] }[] {
  const level = flat[idx].meta.level;
  let end = idx + 1;
  while (end < flat.length && flat[end].meta.level > level) end++;
  return [...flat.slice(0, idx), ...flat.slice(end)];
}

/** 사용자에게 보여줄 한국어 설명. 섹션 제목으로 지칭. */
export function describeOutlineAction(doc: DocumentT, action: OutlineAction): string {
  const titleOf = (code: string) => doc.sections[code]?.meta.title ?? code;
  if (action.action === "RENAME") {
    return `'${titleOf(action.target)}' 섹션의 제목을 '${action.title}'(으)로 변경`;
  }
  if (action.action === "ADD") {
    const parent = action.target ? titleOf(action.target) : "(루트)";
    const level = action.level ?? 0;
    return `'${parent}' 아래에 '${action.title}' 섹션 추가 (level ${level || "auto"})`;
  }
  if (action.action === "REMOVE") {
    return `'${titleOf(action.target)}' 섹션과 그 하위 블록 모두 삭제 ⚠ 본문 손실`;
  }
  if (action.action === "MERGE") {
    const titles = action.targets.map(titleOf).join(", ");
    const survivor = action.title ?? titleOf(action.targets[0]);
    return `[${titles}] 섹션을 '${survivor}'(으)로 병합 (본문 보존)`;
  }
  return JSON.stringify(action);
}

export function applyOutlineAction(doc: DocumentT, action: OutlineAction): DocumentT {
  return applyOutlineActions(doc, [action]);
}

export function applyOutlineActions(doc: DocumentT, actions: OutlineAction[]): DocumentT {
  let flat = docToFlat(doc);
  for (const action of actions) {
    if (action.action === "RENAME") {
      const i = indexOfCode(flat, action.target);
      if (i === -1) continue;
      flat[i] = { ...flat[i], meta: { ...flat[i].meta, title: action.title } };
    } else if (action.action === "REMOVE") {
      const i = indexOfCode(flat, action.target);
      if (i === -1) continue;
      flat = removeSubtree(flat, i);
    } else if (action.action === "ADD") {
      const parent = action.target;
      const level =
        action.level ?? (parent ? (flat.find((s) => s.meta.code === parent)?.meta.level ?? 0) + 1 : 1);
      const at = insertionIndex(flat, parent, action.position ?? null, level);
      const newMeta: SectionMeta = {
        code: "TBD",
        title: action.title,
        level,
        children: [],
      };
      flat = [...flat.slice(0, at), { meta: newMeta, blocks: [] }, ...flat.slice(at)];
    } else if (action.action === "MERGE") {
      flat = applyMerge(flat, action.targets, action.title ?? null, action.level ?? null);
    }
  }
  return recomputeCodes(flat);
}

/**
 * MERGE: targets[0]이 생존하고, [targets[0], targets[last]의 subtree-end) 범위의 모든
 * 다른 섹션 블록이 순서대로 생존 섹션 뒤에 이어붙는다.
 * - targets는 outline 표시 순서상 오름차순이어야 한다 (위반 시 거부).
 * - 범위 내에 targets에 없는 섹션이 있더라도 함께 흡수된다 (LLM이 의도한 병합 범위로 간주).
 * - 부모+자식 형태(S2-1, S2-1-1, S2-1-2 …)도 정상 처리.
 */
function applyMerge(
  flat: { meta: SectionMeta; blocks: Section["blocks"] }[],
  targets: string[],
  newTitle: string | null,
  newLevel: number | null
): { meta: SectionMeta; blocks: Section["blocks"] }[] {
  if (!targets || targets.length < 2) return flat;

  const indices = targets.map((t) => indexOfCode(flat, t));
  if (indices.some((i) => i === -1)) {
    console.warn("MERGE: target not found, skipping", targets);
    return flat;
  }
  for (let k = 0; k < indices.length - 1; k++) {
    if (indices[k] >= indices[k + 1]) {
      console.warn("MERGE: targets not in display order, skipping", targets);
      return flat;
    }
  }

  const subtreeEnd = (i: number): number => {
    const level = flat[i].meta.level;
    let e = i + 1;
    while (e < flat.length && flat[e].meta.level > level) e++;
    return e;
  };

  const survivorIdx = indices[0];
  const lastEnd = subtreeEnd(indices[indices.length - 1]);

  // survivor 자체의 블록은 유지하고, 그 이후 ~ lastEnd 범위의 모든 섹션 블록을 흡수.
  const absorbedBlocks = flat
    .slice(survivorIdx + 1, lastEnd)
    .flatMap((s) => s.blocks);

  const survivor = flat[survivorIdx];
  const mergedSection = {
    meta: {
      ...survivor.meta,
      title: newTitle ?? survivor.meta.title,
      level: newLevel ?? survivor.meta.level,
    } as SectionMeta,
    blocks: [...survivor.blocks, ...absorbedBlocks],
  };

  return [
    ...flat.slice(0, survivorIdx),
    mergedSection,
    ...flat.slice(lastEnd),
  ];
}
