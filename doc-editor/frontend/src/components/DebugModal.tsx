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
      <div className="text-[11px] font-mono p-2 overflow-auto bg-slate-50">
        <JsonNode value={data} defaultOpen depth={0} />
      </div>
    </div>
  );
}

function JsonNode({
  name,
  value,
  defaultOpen = false,
  depth,
}: {
  name?: string;
  value: unknown;
  defaultOpen?: boolean;
  depth: number;
}) {
  const [open, setOpen] = useState(defaultOpen || depth < 1);

  const isObject = value !== null && typeof value === "object";
  const label = name !== undefined ? <span className="text-slate-700">"{name}"</span> : null;

  if (!isObject) {
    return (
      <div style={{ paddingLeft: depth * 12 }} className="leading-5">
        {label}
        {label && <span className="text-slate-500">: </span>}
        <span className={valueColor(value)}>{formatPrimitive(value)}</span>
      </div>
    );
  }

  const isArray = Array.isArray(value);
  const entries: [string, unknown][] = isArray
    ? (value as unknown[]).map((v, i) => [String(i), v])
    : Object.entries(value as Record<string, unknown>);
  const open_b = isArray ? "[" : "{";
  const close_b = isArray ? "]" : "}";

  if (entries.length === 0) {
    return (
      <div style={{ paddingLeft: depth * 12 }} className="leading-5">
        {label}
        {label && <span className="text-slate-500">: </span>}
        <span className="text-slate-500">{open_b}{close_b}</span>
      </div>
    );
  }

  return (
    <div style={{ paddingLeft: depth * 12 }} className="leading-5">
      <div
        className="cursor-pointer select-none hover:bg-slate-100 rounded"
        onClick={() => setOpen(!open)}
      >
        <span className="inline-block w-3 text-slate-500">{open ? "▾" : "▸"}</span>
        {label}
        {label && <span className="text-slate-500">: </span>}
        <span className="text-slate-500">
          {open ? open_b : `${open_b} … ${close_b}`}
          {!open && <span className="text-slate-400"> {entries.length} {isArray ? "items" : "keys"}</span>}
        </span>
      </div>
      {open && (
        <>
          {entries.map(([k, v]) => (
            <JsonNode key={k} name={isArray ? undefined : k} value={v} depth={depth + 1} />
          ))}
          <div style={{ paddingLeft: 12 }} className="text-slate-500 leading-5">
            {close_b}
          </div>
        </>
      )}
    </div>
  );
}

function formatPrimitive(v: unknown): string {
  if (v === null) return "null";
  if (typeof v === "string") return `"${v}"`;
  return String(v);
}

function valueColor(v: unknown): string {
  if (v === null) return "text-slate-400";
  if (typeof v === "string") return "text-emerald-700";
  if (typeof v === "number") return "text-blue-700";
  if (typeof v === "boolean") return "text-purple-700";
  return "text-slate-700";
}
