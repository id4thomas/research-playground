import { useState } from "react";

export type TraceEntry = {
  turnId: string;
  endpoint: string;
  request: unknown;
  response: unknown;
  ts: number;
  durationMs: number;
};

type Props = {
  trace: TraceEntry;
  onClose: () => void;
};

export function DebugModal({ trace, onClose }: Props) {
  const [tab, setTab] = useState<"request" | "response" | "both">("both");

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">디버그 — {trace.endpoint}</div>
            <div className="text-[10px] text-slate-500 font-mono">
              turn={trace.turnId} · {trace.durationMs}ms · {new Date(trace.ts).toLocaleTimeString()}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {(["request", "response", "both"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`text-xs px-2 py-1 rounded ${
                  tab === t
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {t}
              </button>
            ))}
            <button
              onClick={onClose}
              className="ml-2 text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
            >
              닫기
            </button>
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-auto p-3">
          <div className={tab === "both" ? "grid grid-cols-2 gap-3" : "flex flex-col gap-3"}>
            {(tab === "request" || tab === "both") && (
              <Pane title="Request" data={trace.request} />
            )}
            {(tab === "response" || tab === "both") && (
              <Pane title="Response" data={trace.response} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Pane({ title, data }: { title: string; data: unknown }) {
  return (
    <div className="border border-slate-200 rounded overflow-hidden flex flex-col min-h-0">
      <div className="px-2 py-1 bg-slate-100 text-[11px] font-semibold text-slate-600">
        {title}
      </div>
      <pre className="text-[11px] font-mono p-2 overflow-auto bg-slate-50 whitespace-pre-wrap break-words">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
