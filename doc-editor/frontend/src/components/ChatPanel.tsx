import { useRef, useState } from "react";
import type { DocumentT } from "../types";
import type { MsgWithIntent } from "../App";
import { DiffPopup } from "./DiffPopup";
import { OutlinePreview } from "./OutlinePreview";
import { DebugModal, type TraceEntry } from "./DebugModal";

const INTENT_META: Record<
  string,
  { label: string; cls: string }
> = {
  edit:          { label: "편집",      cls: "bg-blue-100 text-blue-800" },
  restructure:   { label: "구조 변경", cls: "bg-emerald-100 text-emerald-800" },
  clarify:       { label: "질문",      cls: "bg-amber-100 text-amber-800" },
  answer:        { label: "답변",      cls: "bg-slate-100 text-slate-700" },
};

type Props = {
  messages: MsgWithIntent[];
  traces: Record<string, TraceEntry>;
  selected: string[];
  doc: DocumentT | null;
  busy: boolean;
  width: number;
  onSend: (text: string) => void;
  onAcceptEdit: (msgIdx: number, entryIdx: number) => void;
  onDeclineEdit: (msgIdx: number, entryIdx: number) => void;
  onInstructEdit: (msgIdx: number, entryIdx: number, text: string) => void;
  onAcceptOutline: (msgIdx: number, entryIdx: number) => void;
  onDeclineOutline: (msgIdx: number, entryIdx: number) => void;
  onInstructOutline: (msgIdx: number, entryIdx: number, text: string) => void;
  onClearSelection: () => void;
  sessionSuggestion: { active: boolean; reason?: string | null };
  onStartNewSession: () => void;
  onDismissSessionSuggestion: () => void;
};

export function ChatPanel({
  messages,
  traces,
  selected,
  doc,
  busy,
  width,
  onSend,
  onAcceptEdit,
  onDeclineEdit,
  onInstructEdit,
  onAcceptOutline,
  onDeclineOutline,
  onInstructOutline,
  onClearSelection,
  sessionSuggestion,
  onStartNewSession,
  onDismissSessionSuggestion,
}: Props) {
  const [draft, setDraft] = useState("");
  const [openTrace, setOpenTrace] = useState<TraceEntry | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function submit() {
    const t = draft.trim();
    if (!t || busy) return;
    onSend(t);
    setDraft("");
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  return (
    <aside
      style={{ width }}
      className="shrink-0 border-l border-slate-200 bg-slate-50 flex flex-col"
    >
      <div className="px-4 py-3 border-b border-slate-200 bg-white">
        <div className="text-[11px] font-semibold tracking-wider text-slate-500">
          PROJECT CHAT
        </div>
        {selected.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <span className="text-[10px] text-slate-500">선택됨:</span>
            {selected.map((s) => (
              <span
                key={s}
                className="font-mono text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded"
              >
                {s}
              </span>
            ))}
            <button
              className="text-[10px] text-slate-500 underline ml-1"
              onClick={onClearSelection}
            >
              clear
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-xs text-slate-400 italic">
            메시지를 입력하거나 블록을 선택 후 수정을 요청하세요.
          </div>
        )}
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          return (
            <div key={i}>
              {m.role === "user" ? (
                <div className="rounded-lg px-3 py-2 text-sm max-w-[90%] ml-auto bg-blue-600 text-white">
                  {m.content}
                </div>
              ) : (
                <div className="mr-auto max-w-[95%] space-y-1">
                  <div className="flex items-center gap-1">
                    {m.intent && INTENT_META[m.intent] && (
                      <span
                        className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${INTENT_META[m.intent].cls}`}
                      >
                        {INTENT_META[m.intent].label}
                      </span>
                    )}
                    {m.turnId && traces[m.turnId] && (
                      <button
                        title="요청/응답 디버그"
                        onClick={() => setOpenTrace(traces[m.turnId!])}
                        className="text-[10px] px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-slate-600"
                      >
                        🐞
                      </button>
                    )}
                  </div>
                  <div className="rounded-lg px-3 py-2 text-sm bg-white border border-slate-200 text-slate-800">
                    {m.content}
                  </div>
                  {m.clarifyOptions && m.clarifyOptions.length > 0 && (
                    <div className="flex flex-col gap-1 pt-1">
                      {m.clarifyOptions.map((opt, k) => (
                        <button
                          key={k}
                          disabled={!isLast || busy}
                          onClick={() => onSend(opt)}
                          className="text-left text-xs px-2.5 py-1.5 rounded border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          {opt}
                        </button>
                      ))}
                      {isLast && (
                        <ClarifyDirectInput onSubmit={onSend} disabled={busy} />
                      )}
                    </div>
                  )}
                  {doc && m.outlineEntries && m.outlineEntries.length > 0 && (
                    <OutlinePreview
                      doc={doc}
                      entries={m.outlineEntries}
                      onAccept={(j) => onAcceptOutline(i, j)}
                      onDecline={(j) => onDeclineOutline(i, j)}
                      onInstruct={(j, text) => onInstructOutline(i, j, text)}
                    />
                  )}
                  {doc && m.editEntries && m.editEntries.length > 0 && (
                    <DiffPopup
                      doc={doc}
                      entries={m.editEntries}
                      onAccept={(j) => onAcceptEdit(i, j)}
                      onDecline={(j) => onDeclineEdit(i, j)}
                      onInstruct={(j, text) => onInstructEdit(i, j, text)}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
        {busy && (
          <div className="text-xs text-slate-400 italic">생성 중…</div>
        )}
        {sessionSuggestion.active && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900 space-y-2">
            <div className="font-semibold">새 대화로 시작할까요?</div>
            {sessionSuggestion.reason && (
              <div className="text-emerald-800">{sessionSuggestion.reason}</div>
            )}
            <div className="flex gap-2">
              <button
                className="rounded bg-emerald-600 text-white text-xs px-2 py-1"
                onClick={onStartNewSession}
              >
                새 대화 시작
              </button>
              <button
                className="rounded border border-emerald-300 text-emerald-800 text-xs px-2 py-1"
                onClick={onDismissSessionSuggestion}
              >
                계속하기
              </button>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-200 bg-white p-2 flex gap-2">
        <input
          className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-50"
          placeholder={doc ? "메시지 입력 (\\edit, \\restructure, \\answer, \\clarify 로 직접 지정 가능)" : "문서를 먼저 업로드하세요"}
          value={draft}
          disabled={!doc || busy}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button
          className="rounded bg-blue-600 text-white text-sm px-3 disabled:opacity-50"
          onClick={submit}
          disabled={!doc || busy}
        >
          Enter
        </button>
      </div>
      {openTrace && <DebugModal trace={openTrace} onClose={() => setOpenTrace(null)} />}
    </aside>
  );
}

function ClarifyDirectInput({ onSubmit, disabled }: { onSubmit: (text: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");
  const [active, setActive] = useState(false);

  function submit() {
    const t = text.trim();
    if (!t) return;
    onSubmit(t);
    setText("");
    setActive(false);
  }

  if (!active) {
    return (
      <button
        disabled={disabled}
        onClick={() => setActive(true)}
        className="text-left text-xs px-2.5 py-1.5 rounded border border-dashed border-amber-400 bg-amber-50/30 hover:bg-amber-50 text-amber-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium italic"
      >
        + 직접 입력...
      </button>
    );
  }

  return (
    <div className="flex gap-1 mt-1">
      <input
        className="flex-1 rounded border border-amber-300 px-2.5 py-1.5 text-xs bg-amber-50/50 text-amber-950 focus:outline-none focus:ring-1 focus:ring-amber-500 placeholder:text-amber-700/50 placeholder:italic"
        placeholder="질문이나 수정을 직접 입력하세요..."
        value={text}
        disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        autoFocus
      />
      <button
        className="rounded bg-amber-600 text-white text-xs px-3 hover:bg-amber-700 disabled:opacity-50 transition-colors shrink-0 font-medium"
        onClick={submit}
        disabled={disabled || !text.trim()}
      >
        보내기
      </button>
      <button
        className="rounded border border-slate-300 bg-white text-slate-600 text-xs px-2.5 hover:bg-slate-50 transition-colors shrink-0 font-medium"
        onClick={() => {
          setText("");
          setActive(false);
        }}
        disabled={disabled}
      >
        취소
      </button>
    </div>
  );
}
