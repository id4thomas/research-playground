import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Block, DocumentT } from "../types";
import { orderedBlocks } from "../types";

type Props = {
  doc: DocumentT;
  selected: Set<string>;
  onToggleSelect: (ref: string) => void;
  onEditBlock: (sectionCode: string, blockId: string, value: string) => void;
  onDeleteBlock: (sectionCode: string, blockId: string) => void;
  jumpTarget: string | null;
};

function BlockBody({ block, onChange }: { block: Block; onChange: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const rows = Math.max(1, Math.ceil(block.content.length / 60));
  const base = "flex-1 resize-none outline-none leading-snug text-sm";

  if (block.type === "text") {
    if (editing) {
      return (
        <textarea
          autoFocus
          className={`${base} bg-transparent`}
          rows={rows}
          value={block.content}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setEditing(false)}
        />
      );
    }
    return (
      <div
        className="flex-1 leading-snug text-sm prose-block cursor-text"
        onClick={() => setEditing(true)}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content}</ReactMarkdown>
      </div>
    );
  }
  return (
    <textarea
      className={`${base} bg-slate-50 rounded px-2 py-1 font-mono text-[12px]`}
      rows={rows}
      value={block.content}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function ResizeHandle({ onResize }: { onResize: (dy: number) => void }) {
  return (
    <div
      title="높이 조절"
      onPointerDown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        const startY = e.clientY;
        let lastY = startY;
        const onMove = (ev: PointerEvent) => {
          onResize(ev.clientY - lastY);
          lastY = ev.clientY;
        };
        const onUp = () => {
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
      }}
      className="absolute bottom-0 right-0 h-3 w-3 cursor-ns-resize opacity-0 group-hover:opacity-60 hover:!opacity-100"
      style={{
        background:
          "linear-gradient(135deg, transparent 0 45%, rgb(100 116 139) 45% 55%, transparent 55% 100%)",
      }}
    />
  );
}

export function Editor({ doc, selected, onToggleSelect, onEditBlock, onDeleteBlock, jumpTarget }: Props) {
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});
  const [heights, setHeights] = useState<Record<string, number>>({});

  // Scroll to section when jumpTarget changes
  const prevJump = useRef<string | null>(null);
  if (jumpTarget && jumpTarget !== prevJump.current) {
    prevJump.current = jumpTarget;
    setTimeout(() => {
      sectionRefs.current[jumpTarget]?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }

  const orderedCodes = doc.outline.map((m) => m.code);

  return (
    <div className="flex-1 min-w-0 overflow-y-auto bg-white">
      <div className="w-full p-6">
        <h1 className="text-lg font-bold tracking-wide text-slate-800 mb-6">DOCUMENT EDITOR</h1>
        {orderedCodes.map((code) => {
          const section = doc.sections[code];
          if (!section) return null;
          const { meta } = section;
          const blocks = orderedBlocks(section);
          const indent = (meta.level - 1) * 16;
          return (
            <section
              key={code}
              ref={(el) => { sectionRefs.current[code] = el; }}
              style={{ marginLeft: indent }}
              className="mb-6"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                  {code}
                </span>
                <h2
                  className={`font-semibold text-slate-700 ${
                    meta.level === 1 ? "text-sm" : "text-xs"
                  }`}
                >
                  {meta.title}
                </h2>
              </div>
              <div className="space-y-1.5">
                {blocks.map((b) => {
                  const ref = b.id;
                  const isSel = selected.has(ref);
                  const h = heights[ref];
                  return (
                    <div
                      key={ref}
                      style={h ? { height: h, overflow: "auto" } : undefined}
                      className={
                        "group relative rounded border px-3 py-2 transition " +
                        (isSel
                          ? "border-amber-400 bg-amber-50"
                          : "border-slate-200 hover:border-slate-300 bg-white")
                      }
                    >
                      <div className="flex items-start gap-2">
                        <button
                          title={`select ${ref}`}
                          className={
                            "mt-0.5 h-4 w-4 shrink-0 rounded border " +
                            (isSel
                              ? "bg-amber-400 border-amber-500"
                              : "border-slate-300 hover:border-slate-400")
                          }
                          onClick={() => onToggleSelect(ref)}
                        />
                        <BlockBody block={b} onChange={(v) => onEditBlock(code, ref, v)} />
                        <span title={ref} className="text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 shrink-0">
                          {b.type !== "text" ? `${b.type} ` : ""}{ref.slice(0, 6)}
                        </span>
                        <button
                          title="블록 삭제"
                          onClick={() => onDeleteBlock(code, ref)}
                          className="opacity-0 group-hover:opacity-100 shrink-0 h-5 w-5 flex items-center justify-center rounded text-red-600 hover:bg-red-100 transition"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                            <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                      <ResizeHandle
                        onResize={(dy) =>
                          setHeights((prev) => {
                            const cur = prev[ref] ?? 0;
                            const base = cur || 60;
                            const next = Math.max(32, base + dy);
                            return { ...prev, [ref]: next };
                          })
                        }
                      />
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
