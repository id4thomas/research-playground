import type { Block, DocumentT, OutlineAction, Section, SectionMeta } from "../types";

// 섹션 본문(블록 dict + 순서)을 outline 변형 동안 통째로 들고 다닌다.
type Body = { blocks: Record<string, Block>; order: string[] };
type Flat = { meta: SectionMeta; body: Body };

const emptyBody = (): Body => ({ blocks: {}, order: [] });

/**
 * 각 섹션의 level 을 기준으로 S-코드를 다시 매기고, 그 코드를 키로 sections dict 를
 * 재구성한 새 Document 를 반환한다. flatSections 는 표시 순서(평탄 리스트).
 */
function recomputeCodes(flat: Flat[]): DocumentT {
  const counters: number[] = [];
  const newOutline: SectionMeta[] = [];
  const newSections: Record<string, Section> = {};

  const codes: string[] = flat.map(({ meta }) => {
    const level = meta.level;
    if (level > counters.length) {
      while (counters.length < level) counters.push(0);
    } else {
      counters.length = level;
    }
    counters[level - 1]++;
    return "S" + counters.slice(0, level).join("-");
  });

  for (let i = 0; i < flat.length; i++) {
    const { meta, body } = flat[i];
    const code = codes[i];
    const children: string[] = [];
    for (let j = i + 1; j < flat.length; j++) {
      if (flat[j].meta.level === meta.level + 1) {
        children.push(codes[j]);
      } else if (flat[j].meta.level <= meta.level) {
        break;
      }
    }
    const newMeta: SectionMeta = { ...meta, code, children };
    newOutline.push(newMeta);
    newSections[code] = { meta: newMeta, blocks: body.blocks, order: body.order };
  }

  return { sections: newSections, outline: newOutline };
}

function docToFlat(doc: DocumentT): Flat[] {
  return doc.outline.map((m) => {
    const s = doc.sections[m.code];
    return { meta: { ...m }, body: s ? { blocks: s.blocks, order: s.order } : emptyBody() };
  });
}

function indexOfCode(flat: Flat[], code: string): number {
  return flat.findIndex((s) => s.meta.code === code);
}

/** Index where a child of `parentCode` at sibling position `position` should be inserted. */
function insertionIndex(
  flat: Flat[],
  parentCode: string | null,
  position: number | null,
  newLevel: number
): number {
  if (!parentCode) {
    const rootCount = flat.filter((s) => s.meta.level === newLevel).length;
    const pos = position === null || position === undefined ? rootCount : position;
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
  const childLevel = parentLevel + 1;
  let seen = 0;
  let i = pIdx + 1;
  while (i < flat.length && flat[i].meta.level > parentLevel) {
    if (flat[i].meta.level === childLevel) {
      if (position !== null && position !== undefined && seen === position) return i;
      seen++;
    }
    i++;
  }
  return i;
}

/** Remove the section at `idx` and all of its descendants. */
function removeSubtree(flat: Flat[], idx: number): Flat[] {
  const level = flat[idx].meta.level;
  let end = idx + 1;
  while (end < flat.length && flat[end].meta.level > level) end++;
  return [...flat.slice(0, idx), ...flat.slice(end)];
}

/** 두 본문을 순서 보존하며 합친다. */
function concatBody(a: Body, b: Body): Body {
  return {
    blocks: { ...a.blocks, ...b.blocks },
    order: [...a.order, ...b.order],
  };
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
      const newMeta: SectionMeta = { code: "TBD", title: action.title, level, children: [] };
      flat = [...flat.slice(0, at), { meta: newMeta, body: emptyBody() }, ...flat.slice(at)];
    } else if (action.action === "MERGE") {
      flat = applyMerge(flat, action.targets, action.title ?? null, action.level ?? null);
    }
  }
  return recomputeCodes(flat);
}

/**
 * MERGE: targets[0]이 생존하고, [targets[0], targets[last]의 subtree-end) 범위의 모든
 * 다른 섹션 블록이 순서대로 생존 섹션 뒤에 이어붙는다.
 */
function applyMerge(
  flat: Flat[],
  targets: string[],
  newTitle: string | null,
  newLevel: number | null
): Flat[] {
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

  // survivor 본문 + 이후 ~ lastEnd 범위의 모든 섹션 본문을 순서대로 흡수.
  let mergedBody = flat[survivorIdx].body;
  for (const s of flat.slice(survivorIdx + 1, lastEnd)) {
    mergedBody = concatBody(mergedBody, s.body);
  }

  const survivor = flat[survivorIdx];
  const mergedSection: Flat = {
    meta: {
      ...survivor.meta,
      title: newTitle ?? survivor.meta.title,
      level: newLevel ?? survivor.meta.level,
    },
    body: mergedBody,
  };

  return [...flat.slice(0, survivorIdx), mergedSection, ...flat.slice(lastEnd)];
}
