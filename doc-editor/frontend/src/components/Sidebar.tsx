import { useRef } from "react";
import type { DocumentT, SectionMeta } from "../types";

type Props = {
  doc: DocumentT | null;
  width: number;
  onUpload: (file: File) => void;
  onJumpSection: (code: string) => void;
  uploading: boolean;
};

function OutlineNode({
  meta,
  outline,
  onJump,
}: {
  meta: SectionMeta;
  outline: SectionMeta[];
  onJump: (code: string) => void;
}) {
  const children = outline.filter((m) => meta.children.includes(m.code));
  const indent = (meta.level - 1) * 12;

  return (
    <li>
      <button
        style={{ paddingLeft: indent + 8 }}
        className="w-full text-left flex items-center gap-1.5 py-1 pr-2 rounded hover:bg-slate-100 group"
        onClick={() => onJump(meta.code)}
      >
        <span className="font-mono text-[10px] bg-slate-200 text-slate-600 rounded px-1 shrink-0">
          {meta.code}
        </span>
        <span className="text-xs text-slate-700 truncate">{meta.title}</span>
      </button>
      {children.length > 0 && (
        <ul>
          {children.map((c) => (
            <OutlineNode key={c.code} meta={c} outline={outline} onJump={onJump} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function Sidebar({ doc, width, onUpload, onJumpSection, uploading }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const topLevel = doc?.outline.filter((m) => m.level === 1) ?? [];

  return (
    <aside
      style={{ width }}
      className="shrink-0 border-r border-slate-200 bg-white flex flex-col overflow-hidden"
    >
      <div className="p-4 border-b border-slate-100">
        <div className="text-[11px] font-semibold tracking-wider text-slate-500 mb-2">
          DOCUMENT
        </div>
        <button
          className="w-full rounded border border-dashed border-slate-300 py-2 text-xs text-slate-500 hover:border-blue-400 hover:text-blue-600 transition-colors disabled:opacity-50"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "파싱 중…" : doc ? "다른 문서 업로드" : "Markdown 파일 업로드"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".md,text/markdown"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
      </div>

      {doc && (
        <div className="flex-1 overflow-y-auto p-3">
          <div className="text-[11px] font-semibold tracking-wider text-slate-500 mb-2">
            OUTLINE
          </div>
          <ul className="space-y-0.5">
            {topLevel.map((m) => (
              <OutlineNode key={m.code} meta={m} outline={doc.outline} onJump={onJumpSection} />
            ))}
          </ul>
        </div>
      )}

      {!doc && (
        <div className="flex-1 flex items-center justify-center text-xs text-slate-400 italic p-4 text-center">
          Markdown 문서를 업로드하면<br />섹션 Outline이 표시됩니다
        </div>
      )}
    </aside>
  );
}
