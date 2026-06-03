import { useState } from "react";
import type { DocumentT, EditEntry } from "../types";
import { previewBlock } from "../lib/edits";
import { diffWords } from "../lib/diff";
import { BlockRender } from "./BlockView";

type Props = {
  doc: DocumentT;
  entries: EditEntry[];
  onAccept: (i: number) => void;
  onDecline: (i: number) => void;
  onInstruct: (i: number, text: string) => void;
};

function isValidEdit(edit: EditEntry["edit"]): boolean {
  if (edit.action === "REWRITE") return !!edit.value?.trim();
  if (edit.action === "REPLACE") return !!edit.target?.trim();
  if (edit.action === "INSERT") return !!edit.value?.content?.trim();
  return true;
}

export function DiffPopup({ doc, entries, onAccept, onDecline, onInstruct }: Props) {
  if (entries.length === 0) return null;
  const validIndices = entries
    .map((entry, i) => ({ entry, i }))
    .filter(({ entry }) => isValidEdit(entry.edit));
  if (validIndices.length === 0) return null;

  return (
    <div className="border border-slate-300 rounded-md bg-white shadow-sm p-3 space-y-3">
      <div className="text-xs font-semibold text-slate-700">
        DIFF &amp; EDIT — {validIndices.length}개 제안
      </div>
      {validIndices.map(({ entry, i }) => {
        const { ref, edit, status } = entry;
        const { before, after, kind, afterBlock } = previewBlock(doc, ref, edit);
        const parts = diffWords(before, after);
        // 일반 텍스트(markdown)는 word-diff 로 충분 — 표/수식/html 은 렌더 미리보기를 덧붙인다.
        const showRendered = !(afterBlock.type === "text" && afterBlock.format === "markdown");

        const wrapperCls =
          status === "accepted"
            ? "border-emerald-400 bg-emerald-50/30"
            : status === "declined"
            ? "border-rose-400 bg-rose-50/30"
            : status === "instructed"
            ? "border-sky-400 bg-sky-50/30"
            : "border-slate-200";

        return (
          <div key={i} className={`border rounded p-2 text-xs space-y-2 ${wrapperCls}`}>
            <div className="flex items-center justify-between">
              <span className="font-mono text-slate-500">
                {ref}
                {kind !== "text" && kind !== "new" ? ` · ${kind}` : ""}
              </span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                {edit.action}
                {edit.action === "INSERT" ? " (after)" : ""}
              </span>
            </div>
            {edit.summary && (
              <div className="text-[11px] text-slate-700 bg-amber-50/70 border border-amber-200 rounded px-2 py-1">
                <span className="text-amber-700 font-semibold mr-1">의도</span>
                {edit.summary}
              </div>
            )}
            {before !== "" && (
              <div>
                <div className="text-[10px] text-slate-500 mb-0.5">Before</div>
                <div className="bg-red-50/40 border border-red-100 rounded px-2 py-1 whitespace-pre-wrap leading-relaxed text-slate-800">
                  {parts
                    .filter((p) => p.type !== "ins")
                    .map((p, k) =>
                      p.type === "del" ? (
                        <span key={k} className="bg-red-200/70 text-red-900 rounded-sm">{p.text}</span>
                      ) : (
                        <span key={k}>{p.text}</span>
                      )
                    )}
                </div>
              </div>
            )}
            <div>
              <div className="text-[10px] text-slate-500 mb-0.5">After</div>
              <div className="bg-emerald-50/40 border border-emerald-100 rounded px-2 py-1 whitespace-pre-wrap leading-relaxed text-slate-800">
                {parts
                  .filter((p) => p.type !== "del")
                  .map((p, k) =>
                    p.type === "ins" ? (
                      <span key={k} className="bg-emerald-200/70 text-emerald-900 rounded-sm">{p.text}</span>
                    ) : (
                      <span key={k}>{p.text}</span>
                    )
                  )}
              </div>
            </div>
            {showRendered && (
              <div>
                <div className="text-[10px] text-slate-500 mb-0.5">렌더 미리보기 · {afterBlock.type}:{afterBlock.format}</div>
                <div className="bg-white border border-slate-200 rounded px-2 py-1 overflow-x-auto">
                  <BlockRender block={afterBlock} />
                </div>
              </div>
            )}
            <StatusFooter
              status={status}
              instruction={entry.instruction}
              onAccept={() => onAccept(i)}
              onDecline={() => onDecline(i)}
              onInstruct={(text) => onInstruct(i, text)}
            />
          </div>
        );
      })}
    </div>
  );
}

function StatusFooter({
  status,
  instruction,
  onAccept,
  onDecline,
  onInstruct,
}: {
  status: EditEntry["status"];
  instruction?: string;
  onAccept: () => void;
  onDecline: () => void;
  onInstruct: (text: string) => void;
}) {
  if (status === "accepted") {
    return (
      <div className="pt-1">
        <span className="inline-block rounded bg-emerald-100 text-emerald-800 px-2 py-1 text-[11px] font-semibold">
          ✓ ACCEPTED
        </span>
      </div>
    );
  }
  if (status === "declined") {
    return (
      <div className="pt-1">
        <span className="inline-block rounded bg-rose-100 text-rose-800 px-2 py-1 text-[11px] font-semibold">
          ✕ DECLINED
        </span>
      </div>
    );
  }
  if (status === "instructed") {
    return (
      <div className="pt-1 space-y-1">
        <span className="inline-block rounded bg-sky-100 text-sky-800 px-2 py-1 text-[11px] font-semibold">
          ✎ INSTRUCTED
        </span>
        {instruction && (
          <div className="text-[11px] text-sky-900 bg-sky-50 border border-sky-200 rounded px-2 py-1">
            {instruction}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-1 pt-1">
      <div className="flex gap-2">
        <button
          className="flex-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 py-1 text-[11px] font-semibold"
          onClick={onAccept}
        >
          ✓ ACCEPT
        </button>
        <button
          className="flex-1 rounded bg-rose-600 text-white hover:bg-rose-700 py-1 text-[11px] font-semibold"
          onClick={onDecline}
        >
          ✕ DECLINE
        </button>
      </div>
      <InstructInput onSubmit={onInstruct} />
    </div>
  );
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
