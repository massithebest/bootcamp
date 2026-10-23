import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GFM_OPTIONS } from "@/lib/markdown-options";

function Heading4(props: ComponentPropsWithoutRef<"h4">) {
  return <h4 className="pt-1 text-ui-lg font-semibold leading-relaxed text-ink">{props.children}</h4>;
}

function Heading5(props: ComponentPropsWithoutRef<"h5">) {
  return <h5 className="pt-1 text-ui font-semibold leading-relaxed text-ink">{props.children}</h5>;
}

function Heading6(props: ComponentPropsWithoutRef<"h6">) {
  return <h6 className="pt-1 text-ui font-semibold leading-relaxed text-ink-2">{props.children}</h6>;
}

function Paragraph(props: ComponentPropsWithoutRef<"p">) {
  return <p className="min-w-0 [overflow-wrap:anywhere] text-ui leading-[1.7] text-ink-2">{props.children}</p>;
}

function Code(props: ComponentPropsWithoutRef<"code">) {
  const isBlock = /\blanguage-/.test(props.className ?? "");
  if (isBlock) return <code className={props.className}>{props.children}</code>;
  return <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.9em] text-ink">{props.children}</code>;
}

/** Static Skill instructions. Headings are nested below the Skill item h3. */
export function SkillMarkdown({ content }: { content: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-3 [overflow-wrap:anywhere] [&_pre]:[overflow-wrap:normal]">
      <ReactMarkdown
        skipHtml
        remarkPlugins={[[remarkGfm, GFM_OPTIONS]]}
        components={{
          h1: Heading4,
          h2: Heading5,
          h3: Heading6,
          h4: Heading6,
          h5: Heading6,
          h6: Heading6,
          p: Paragraph,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="flex list-disc flex-col gap-2 pl-5 marker:text-ink-3">{children}</ul>,
          ol: ({ children }) => <ol className="flex list-decimal flex-col gap-2 pl-5 marker:font-mono marker:text-ink-3">{children}</ol>,
          li: ({ children }) => <li className="min-w-0 pl-0.5 text-ui leading-[1.7] text-ink-2">{children}</li>,
          blockquote: ({ children }) => <blockquote className="border-l-2 border-line-strong pl-3 text-ink-2">{children}</blockquote>,
          a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2 hover:text-accent-hover">{children}</a>,
          code: Code,
          pre: ({ children }) => <pre className="thin-scroll max-h-96 overflow-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed text-[#d7dce4]">{children}</pre>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
