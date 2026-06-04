import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Editor } from "./components/Editor";
import { ChatPanel } from "./components/ChatPanel";
import { Resizer } from "./components/Resizer";
import type { DocumentT, EditEntry, Intent, OutlineEntry, TokenUsage } from "./types";
import { deriveIntent } from "./types";
import * as api from "./lib/api";
import { applyEdit } from "./lib/edits";
import { applyOutlineAction } from "./lib/outline";
import { serializeMessages, actionsToEntries } from "./lib/messages";
import type { TraceEntry } from "./components/DebugModal";

export type MsgWithIntent = {
  role: "user" | "assistant" | "system";
  content: string;
  intent?: Intent;
  clarifyOptions?: string[];
  editEntries?: EditEntry[];
  outlineEntries?: OutlineEntry[];
  turnId?: string;
  // user 메시지가 직전 어시스턴트의 clarify 보기 중 몇 번째를 클릭해서 만들어졌는지.
  pickedOptionIndex?: number;
  // assistant 메시지에 한해, 이 턴 호출이 소비한 토큰 수.
  tokenUsage?: TokenUsage;
};

const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

export default function App() {
  const [doc, setDoc] = useState<DocumentT | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const [messages, setMessages] = useState<MsgWithIntent[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // 백엔드가 새 대화 추천을 보냈을 때 보관. pending entry가 모두 해소되면 노출.
  const [pendingSessionReason, setPendingSessionReason] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [traces, setTraces] = useState<Record<string, TraceEntry>>({});

  const [sidebarW, setSidebarW] = useState(260);
  const [chatW, setChatW] = useState(380);
  const [jumpTarget, setJumpTarget] = useState<string | null>(null);

  async function onUpload(file: File) {
    setUploading(true);
    try {
      const loaded = await api.uploadMarkdown(file);
      const newDocId = `p_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
      setDoc(loaded);
      setDocId(newDocId);
      setMessages([]);
      setSelected(new Set());
      setPendingSessionReason(null);
    } catch (e) {
      alert(`업로드 실패: ${e}`);
    } finally {
      setUploading(false);
    }
  }

  function onToggleSelect(ref: string) {
    setSelected((s) => {
      const n = new Set(s);
      n.has(ref) ? n.delete(ref) : n.add(ref);
      return n;
    });
  }

  async function onSend(text: string, baseMessages?: MsgWithIntent[], opts?: { pickedOptionIndex?: number }) {
    if (!doc || !docId) return;
    const slash = api.parseSlashDirective(text);
    const visibleText = text;
    const apiText = slash ? slash.body || text : text;

    const base = baseMessages ?? messages;
    const userMsg: MsgWithIntent = {
      role: "user",
      content: visibleText,
      pickedOptionIndex: opts?.pickedOptionIndex,
    };
    const next = [...base, userMsg];
    setMessages(next);
    setBusy(true);
    try {
      // 직렬화: next 의 마지막 user 메시지까지 포함해서 보냄.
      // slash 인 경우 마지막 user 의 content 를 본문(body) 로 치환.
      const serialized = serializeMessages(next, doc);
      if (slash) {
        const last = serialized[serialized.length - 1];
        if (last?.role === "user") last.content = apiText;
      }
      const args = {
        project_id: docId,
        messages: serialized,
        document: doc,
        selected: selected.size ? Array.from(selected) : undefined,
      };
      const endpoint = slash ? api.endpointForIntent(slash.intent) : "/api/chat";
      const t0 = performance.now();
      const res = slash ? await api.callForIntent(slash.intent, args) : await api.chat(args);
      const durationMs = Math.round(performance.now() - t0);
      const turnId = `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
      setTraces((prev) => ({
        ...prev,
        [turnId]: { turnId, endpoint, request: args, response: res, ts: Date.now(), durationMs },
      }));

      // 응답 메시지 타입에 따라 페이로드를 꺼낸다 (interaction=actions, clarify=options).
      const msg = res.message;
      const actions = msg?.type === "interaction" ? msg.actions : [];
      const clarifyOptions = msg?.type === "clarify" ? msg.clarify_options : undefined;
      const { editEntries, outlineEntries } = actionsToEntries(actions);

      const assistantMsg: MsgWithIntent = {
        role: "assistant",
        content: msg?.content ?? "",
        intent: deriveIntent(msg),
        clarifyOptions,
        editEntries: editEntries.length ? editEntries : undefined,
        outlineEntries: outlineEntries.length ? outlineEntries : undefined,
        turnId,
        tokenUsage: res.token_usage,
      };
      setMessages((m) => [...m, assistantMsg]);

      if (res.suggest_new_session) {
        setPendingSessionReason(res.suggest_new_session_reason ?? "");
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `오류: ${e}` }]);
    } finally {
      setBusy(false);
    }
  }

  function updateEditEntry(msgIdx: number, entryIdx: number, status: "accepted" | "declined") {
    setMessages((ms) =>
      ms.map((m, i) => {
        if (i !== msgIdx || !m.editEntries) return m;
        const entries = m.editEntries.map((e, j) => (j === entryIdx ? { ...e, status } : e));
        return { ...m, editEntries: entries };
      })
    );
  }

  function updateOutlineEntry(msgIdx: number, entryIdx: number, status: "accepted" | "declined") {
    setMessages((ms) =>
      ms.map((m, i) => {
        if (i !== msgIdx || !m.outlineEntries) return m;
        const entries = m.outlineEntries.map((e, j) => (j === entryIdx ? { ...e, status } : e));
        return { ...m, outlineEntries: entries };
      })
    );
  }

  function onAcceptEdit(msgIdx: number, entryIdx: number) {
    if (!doc) return;
    const msg = messages[msgIdx];
    const entry = msg?.editEntries?.[entryIdx];
    if (!entry || entry.status !== "pending") return;
    setDoc(applyEdit(doc, entry.ref, entry.edit));
    updateEditEntry(msgIdx, entryIdx, "accepted");
  }

  function onDeclineEdit(msgIdx: number, entryIdx: number) {
    updateEditEntry(msgIdx, entryIdx, "declined");
  }

  function onAcceptOutline(msgIdx: number, entryIdx: number) {
    if (!doc) return;
    const msg = messages[msgIdx];
    const entry = msg?.outlineEntries?.[entryIdx];
    if (!entry || entry.status !== "pending") return;
    setDoc(applyOutlineAction(doc, entry.action));
    updateOutlineEntry(msgIdx, entryIdx, "accepted");
  }

  function onDeclineOutline(msgIdx: number, entryIdx: number) {
    updateOutlineEntry(msgIdx, entryIdx, "declined");
  }

  // 보강 지시: 해당 entry 의 status 를 "instructed" 로 바꾸고, 그 텍스트를
  // 새로운 user 메시지로 백엔드에 전송한다. setMessages 의 비동기성 때문에
  // 직접 갱신된 messages 사본을 onSend 에 넘긴다.
  function onInstructEdit(msgIdx: number, entryIdx: number, text: string) {
    const newMessages = messages.map((m, i) => {
      if (i !== msgIdx || !m.editEntries) return m;
      const entries = m.editEntries.map((e, j) =>
        j === entryIdx ? { ...e, status: "instructed" as const, instruction: text } : e
      );
      return { ...m, editEntries: entries };
    });
    setMessages(newMessages);
    onSend(text, newMessages);
  }

  function onInstructOutline(msgIdx: number, entryIdx: number, text: string) {
    const newMessages = messages.map((m, i) => {
      if (i !== msgIdx || !m.outlineEntries) return m;
      const entries = m.outlineEntries.map((e, j) =>
        j === entryIdx ? { ...e, status: "instructed" as const, instruction: text } : e
      );
      return { ...m, outlineEntries: entries };
    });
    setMessages(newMessages);
    onSend(text, newMessages);
  }

  function onStartNewSession() {
    setMessages([]);
    setPendingSessionReason(null);
  }

  function onDismissSessionSuggestion() {
    setPendingSessionReason(null);
  }

  // 메시지 전체에 걸쳐 미결(pending) 항목이 남아있는지 확인.
  // accepted/declined/instructed 는 모두 사용자가 결정한 상태이므로 OK.
  const hasPending = messages.some(
    (m) =>
      m.editEntries?.some((e) => e.status === "pending") ||
      m.outlineEntries?.some((e) => e.status === "pending")
  );

  const sessionSuggestion = {
    active: pendingSessionReason !== null && !hasPending,
    reason: pendingSessionReason,
  };

  // 토큰 사용량: 누적 출력/리즈닝 + 가장 최근 어시스턴트 호출이 본 입력(=대화 컨텍스트 크기).
  const tokenSummary = (() => {
    let cumulativeOutput = 0;
    let cumulativeReasoning = 0;
    let lastInput = 0;
    for (const m of messages) {
      const u = m.tokenUsage;
      if (!u) continue;
      cumulativeOutput += u.output;
      cumulativeReasoning += u.reasoning;
      lastInput = u.input;
    }
    return { context: lastInput, reasoning: cumulativeReasoning, output: cumulativeOutput };
  })();

  function onDeleteBlock(sectionCode: string, blockId: string) {
    if (!doc) return;
    const section = doc.sections[sectionCode];
    if (!section) return;
    const blocks = { ...section.blocks };
    delete blocks[blockId];
    const order = section.order.filter((id) => id !== blockId);
    setDoc({
      ...doc,
      sections: { ...doc.sections, [sectionCode]: { ...section, blocks, order } },
    });
    if (selected.has(blockId)) {
      setSelected((s) => {
        const n = new Set(s);
        n.delete(blockId);
        return n;
      });
    }
  }

  function onEditBlock(sectionCode: string, blockId: string, value: string) {
    if (!doc) return;
    const section = doc.sections[sectionCode];
    if (!section || !section.blocks[blockId]) return;
    const blocks = { ...section.blocks, [blockId]: { ...section.blocks[blockId], content: value } };
    setDoc({
      ...doc,
      sections: { ...doc.sections, [sectionCode]: { ...section, blocks } },
    });
  }

  return (
    <div className="flex h-full">
      <Sidebar
        doc={doc}
        width={sidebarW}
        onUpload={onUpload}
        onJumpSection={(code) => setJumpTarget(code)}
        uploading={uploading}
      />
      <Resizer onDrag={(dx) => setSidebarW((w) => clamp(w + dx, 180, 500))} />

      {doc ? (
        <Editor
          doc={doc}
          selected={selected}
          onToggleSelect={onToggleSelect}
          onEditBlock={onEditBlock}
          onDeleteBlock={onDeleteBlock}
          jumpTarget={jumpTarget}
        />
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-3">
          <div className="text-5xl">📄</div>
          <div className="text-sm">좌측 사이드바에서 Markdown 문서를 업로드하세요</div>
        </div>
      )}

      <Resizer onDrag={(dx) => setChatW((w) => clamp(w - dx, 260, 700))} />
      <ChatPanel
        messages={messages}
        traces={traces}
        selected={Array.from(selected)}
        doc={doc}
        busy={busy}
        width={chatW}
        onSend={(t, pickedIdx) => onSend(t, undefined, { pickedOptionIndex: pickedIdx })}
        tokenSummary={tokenSummary}
        onAcceptEdit={onAcceptEdit}
        onDeclineEdit={onDeclineEdit}
        onInstructEdit={onInstructEdit}
        onAcceptOutline={onAcceptOutline}
        onDeclineOutline={onDeclineOutline}
        onInstructOutline={onInstructOutline}
        onClearSelection={() => setSelected(new Set())}
        sessionSuggestion={sessionSuggestion}
        onStartNewSession={onStartNewSession}
        onDismissSessionSuggestion={onDismissSessionSuggestion}
      />
    </div>
  );
}
