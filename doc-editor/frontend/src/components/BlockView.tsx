import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import katex from "katex";
import type { Block } from "../types";

/** equation 콘텐츠에서 $$..$$ / $..$ 구분자를 떼어 순수 tex 를 얻는다. */
export function stripTexDelimiters(s: string): string {
  const t = s.trim();
  if (t.startsWith("$$") && t.endsWith("$$")) return t.slice(2, -2).trim();
  if (t.startsWith("$") && t.endsWith("$")) return t.slice(1, -1).trim();
  return t;
}

/** 블록을 (type, format) 에 맞춰 렌더한다. text/table=markdown|html, equation=tex|html. */
export function BlockRender({ block, className = "" }: { block: Block; className?: string }) {
  const { type, format, content } = block;

  if (format === "html") {
    return <div className={`prose-block text-sm ${className}`} dangerouslySetInnerHTML={{ __html: content }} />;
  }
  if (type === "equation") {
    try {
      const html = katex.renderToString(stripTexDelimiters(content), {
        displayMode: true,
        throwOnError: false,
      });
      return <div className={`overflow-x-auto text-sm ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
    } catch {
      return <pre className={`font-mono text-[12px] whitespace-pre-wrap ${className}`}>{content}</pre>;
    }
  }
  // text/table + markdown (remark-gfm 가 표를 처리)
  return (
    <div className={`leading-snug text-sm prose-block ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
