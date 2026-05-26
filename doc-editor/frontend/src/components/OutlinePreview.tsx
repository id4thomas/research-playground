import { useState } from "react";
import type { DocumentT, OutlineAction, OutlineEntry, SectionMeta } from "../types";

const ACTION_STYLE: Record<OutlineAction["action"], { label: string; headerCls: string; badgeCls: string }> = {
  RENAME: { label: "이름 변경", headerCls: "border-sky-300 bg-sky-50",     badgeCls: "bg-sky-500 text-white" },
  ADD:    { label: "추가",      headerCls: "border-emerald-300 bg-emerald-50", badgeCls: "bg-emerald-500 text-white" },
  REMOVE: { label: "삭제",      headerCls: "border-rose-300 bg-rose-50",    badgeCls: "bg-rose-500 text-white" },
  MERGE:  { label: "병합",      headerCls: "border-violet-300 bg-violet-50", badgeCls: "bg-violet-500 text-white" },
};

/** Render a single tree node row */
function TreeNode({
  title,
  level,
  variant,
}: {
  title: string;
  level: number;
  variant: "normal" | "highlight" | "faded" | "new" | "removed";
}) {
  const indent = (level - 1) * 14;
  const prefix = level === 1 ? "■" : level === 2 ? "▸" : "·";

  const textCls =
    variant === "highlight"
      ? "text-sky-700 font-semibold"
      : variant === "new"
      ? "text-emerald-700 font-semibold"
      : variant === "removed"
      ? "text-rose-500 line-through"
      : variant === "faded"
      ? "text-slate-400"
      : "text-slate-700";

  const bgCls =
    variant === "highlight"
      ? "bg-sky-100 rounded"
      : variant === "new"
      ? "bg-emerald-100 rounded"
      : variant === "removed"
      ? "bg-rose-50 rounded"
      : "";

  return (
    <div className={`flex items-baseline gap-1 py-0.5 px-1 ${bgCls}`} style={{ paddingLeft: indent + 4 }}>
      <span className="text-[10px] text-slate-400 w-3 shrink-0">{prefix}</span>
      <span className={`text-[11px] leading-tight ${textCls}`}>{title}</span>
    </div>
  );
}

/** Collect subtree of `code` from outline (code + all descendants) */
function collectSubtree(outline: SectionMeta[], code: string): SectionMeta[] {
  const idx = outline.findIndex((m) => m.code === code);
  if (idx === -1) return [];
  const level = outline[idx].level;
  const result = [outline[idx]];
  for (let i = idx + 1; i < outline.length; i++) {
    if (outline[i].level > level) result.push(outline[i]);
    else break;
  }
  return result;
}

type Props = {
  doc: DocumentT;
  entries: OutlineEntry[];
  onAccept: (i: number) => void;
  onDecline: (i: number) => void;
  onInstruct: (i: number, text: string) => void;
};

export function OutlinePreview({ doc, entries, onAccept, onDecline, onInstruct }: Props) {
  if (entries.length === 0) return null;

  return (
    <div className="rounded border border-slate-200 bg-white p-2 space-y-2">
      <div className="text-[11px] font-semibold tracking-wider text-slate-500">
        섹션 구조 변경 ({entries.length})
      </div>

      {entries.map((entry, i) => {
        const { action: a, status, instruction } = entry;
        const style = ACTION_STYLE[a.action];
        const statusRing =
          status === "accepted"
            ? "ring-2 ring-emerald-400"
            : status === "declined"
            ? "ring-2 ring-rose-400 opacity-70"
            : status === "instructed"
            ? "ring-2 ring-sky-400"
            : "";
        return (
          <div key={i} className={`rounded border ${style.headerCls} overflow-hidden ${statusRing}`}>
            {/* Header */}
            <div className="flex items-center gap-2 px-2 py-1.5">
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${style.badgeCls}`}>
                {style.label}
              </span>
              {a.action === "REMOVE" && (
                <span className="text-[10px] text-rose-600 font-semibold">⚠ 본문 손실</span>
              )}
            </div>

            {/* Visual diff */}
            <div className="mx-2 mb-2 rounded border border-slate-200 bg-white overflow-hidden text-[11px]">
              <ActionDiff doc={doc} action={a} />
            </div>

            {/* Buttons / status */}
            <div className="px-2 pb-2 space-y-1">
              {status === "pending" && (
                <>
                  <div className="flex gap-2">
                    <button
                      className="rounded bg-emerald-600 text-white hover:bg-emerald-700 text-[11px] px-2 py-1 font-semibold"
                      onClick={() => onAccept(i)}
                    >
                      ✓ ACCEPT
                    </button>
                    <button
                      className="rounded bg-rose-600 text-white hover:bg-rose-700 text-[11px] px-2 py-1 font-semibold"
                      onClick={() => onDecline(i)}
                    >
                      ✕ DECLINE
                    </button>
                  </div>
                  <InstructInput onSubmit={(text) => onInstruct(i, text)} />
                </>
              )}
              {status === "accepted" && (
                <span className="inline-block rounded bg-emerald-100 text-emerald-800 px-2 py-1 text-[11px] font-semibold">
                  ✓ ACCEPTED
                </span>
              )}
              {status === "declined" && (
                <span className="inline-block rounded bg-rose-100 text-rose-800 px-2 py-1 text-[11px] font-semibold">
                  ✕ DECLINED
                </span>
              )}
              {status === "instructed" && (
                <div className="space-y-1">
                  <span className="inline-block rounded bg-sky-100 text-sky-800 px-2 py-1 text-[11px] font-semibold">
                    ✎ INSTRUCTED
                  </span>
                  {instruction && (
                    <div className="text-[11px] text-sky-900 bg-sky-50 border border-sky-200 rounded px-2 py-1">
                      {instruction}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActionDiff({ doc, action }: { doc: DocumentT; action: OutlineAction }) {
  const outline = doc.outline;

  if (action.action === "RENAME") {
    const node = outline.find((m) => m.code === action.target);
    if (!node) return <NoTarget />;
    return (
      <div className="divide-y divide-slate-100">
        <DiffPane label="Before" arrow={false}>
          <TreeNode title={node.title} level={node.level} variant="highlight" />
        </DiffPane>
        <DiffPane label="After" arrow>
          <TreeNode title={action.title} level={node.level} variant="new" />
        </DiffPane>
      </div>
    );
  }

  if (action.action === "REMOVE") {
    const subtree = collectSubtree(outline, action.target);
    if (!subtree.length) return <NoTarget />;
    return (
      <DiffPane label="삭제될 섹션" arrow={false}>
        {subtree.map((m) => (
          <TreeNode key={m.code} title={m.title} level={m.level} variant="removed" />
        ))}
      </DiffPane>
    );
  }

  if (action.action === "ADD") {
    const parent = action.target ? outline.find((m) => m.code === action.target) : null;
    const newLevel = action.level ?? (parent ? parent.level + 1 : 1);
    return (
      <div className="divide-y divide-slate-100">
        {parent && (
          <DiffPane label="상위 섹션" arrow={false}>
            <TreeNode title={parent.title} level={parent.level} variant="normal" />
          </DiffPane>
        )}
        <DiffPane label="추가될 섹션" arrow>
          <TreeNode title={action.title} level={newLevel} variant="new" />
        </DiffPane>
      </div>
    );
  }

  if (action.action === "MERGE") {
    // Show each target's subtree in "before", collapsed into one node in "after"
    const allNodes: SectionMeta[] = [];
    for (const code of action.targets) {
      const sub = collectSubtree(outline, code);
      sub.forEach((m) => {
        if (!allNodes.find((x) => x.code === m.code)) allNodes.push(m);
      });
    }
    const survivor = outline.find((m) => m.code === action.targets[0]);
    const newTitle = action.title ?? survivor?.title ?? action.targets[0];
    const newLevel = action.level ?? survivor?.level ?? 1;

    return (
      <div className="divide-y divide-slate-100">
        <DiffPane label="Before" arrow={false}>
          {allNodes.map((m) => {
            const isTarget = action.targets.includes(m.code);
            return (
              <TreeNode
                key={m.code}
                title={m.title}
                level={m.level}
                variant={isTarget ? "highlight" : "faded"}
              />
            );
          })}
        </DiffPane>
        <DiffPane label="After" arrow>
          <TreeNode title={newTitle} level={newLevel} variant="new" />
        </DiffPane>
      </div>
    );
  }

  return null;
}

function DiffPane({ label, arrow, children }: { label: string; arrow: boolean; children: React.ReactNode }) {
  return (
    <div className="p-1.5">
      <div className="flex items-center gap-1 mb-1">
        {arrow && <span className="text-emerald-500 text-[10px]">▶</span>}
        <span className="text-[9px] font-bold tracking-wider text-slate-400 uppercase">{label}</span>
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function NoTarget() {
  return <div className="p-2 text-[11px] text-slate-400 italic">섹션을 찾을 수 없습니다</div>;
}

function InstructInput({ onSubmit }: { onSubmit: (text: string) => void }) {
  const [text, setText] = useState("");
  function submit() {
    const t = text.trim();
    if (!t) return;
    onSubmit(t);
    setText("");
  }
  return (
    <div className="flex gap-1">
      <input
        className="flex-1 rounded border border-slate-300 px-2 py-1 text-[11px] placeholder:text-slate-400"
        placeholder="대신 이렇게 해줘 (보강 지시)…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button
        className="rounded bg-slate-700 text-white text-[11px] px-2 hover:bg-slate-800 disabled:opacity-40"
        onClick={submit}
        disabled={!text.trim()}
      >
        보내기
      </button>
    </div>
  );
}
