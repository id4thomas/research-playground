import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Block, DocumentT } from "../types";
import { makeRef } from "../types";

type Props = {
  doc: DocumentT;
  selected: Set<string>;
  onToggleSelect: (ref: string) => void;
  onEditBlock: (sectionCode: string, idx: number, value: string) => void;
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

export function Editor({ doc, selected, onToggleSelect, onEditBlock, jumpTarget }: Props) {
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

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
          const { meta, blocks } = section;
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
                {blocks.map((b, i) => {
                  const ref = makeRef(code, i);
                  const isSel = selected.has(ref);
                  return (
                    <div
                      key={i}
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
                        <BlockBody block={b} onChange={(v) => onEditBlock(code, i, v)} />
                        <span className="text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 shrink-0">
                          {b.type !== "text" ? `${b.type} ` : ""}{ref}
                        </span>
                      </div>
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
