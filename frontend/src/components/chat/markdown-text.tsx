/**
 * `@assistant-ui/react-markdown` 기반 마크다운 렌더러.
 *
 * 자체 구현(`markdown.tsx`, 241줄)을 대체한다. `remark-gfm`으로 표·취소선·
 * 자동링크를 지원하고(자체 파서는 CommonMark 서브셋만 지원했다), 컴포넌트
 * 슬롯으로 기존 시각 스타일(제목 강등·표·코드블록·인용 등)을 그대로 재현한다.
 *
 * 하이라이팅 라이브러리(shiki 등)는 쓰지 않는다 — `code-block` AI Elements
 * 컴포넌트가 애초에 도입되지 않았고(폐쇄망 원칙, docs/decisions.md), 현재도
 * 하이라이팅 없는 단색 코드블록이 기존 동작이다. `pre`/`code` 슬롯에서 순수
 * CSS로만 스타일링하고 런타임 외부 리소스를 불러오지 않는다.
 */

import type { ComponentPropsWithoutRef } from "react";
import remarkGfm from "remark-gfm";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";

/**
 * 자체 파서가 지원하던 `· item` 불릿을 remark 가 인식하는 `- item` 으로
 * 정규화한다. remark-gfm 은 CommonMark 표준 불릿(`-`/`*`/`+`)만 인식한다.
 */
function preprocess(text: string): string {
  return text.replace(/^([ \t]*)·[ \t]+/gm, "$1- ");
}

function Heading1or2(props: ComponentPropsWithoutRef<"h1">) {
  return <h3 className="text-ui-lg font-semibold text-ink">{props.children}</h3>;
}

function Heading3(props: ComponentPropsWithoutRef<"h3">) {
  return <h4 className="text-ui font-semibold text-ink">{props.children}</h4>;
}

function Heading4to6(props: ComponentPropsWithoutRef<"h4">) {
  return <h5 className="text-ui font-semibold text-ink-2">{props.children}</h5>;
}

function Paragraph(props: ComponentPropsWithoutRef<"p">) {
  return <p className="leading-[1.6]">{props.children}</p>;
}

function Strong(props: ComponentPropsWithoutRef<"strong">) {
  return <strong className="font-semibold text-ink">{props.children}</strong>;
}

function Em(props: ComponentPropsWithoutRef<"em">) {
  return <em className="italic">{props.children}</em>;
}

function Blockquote(props: ComponentPropsWithoutRef<"blockquote">) {
  return (
    <blockquote className="border-l-2 border-line-strong pl-3 text-ink-2">
      {props.children}
    </blockquote>
  );
}

function Hr() {
  return <hr className="border-0 border-t border-line" />;
}

function UnorderedList(props: ComponentPropsWithoutRef<"ul">) {
  return (
    <ul className="flex list-disc flex-col gap-1 pl-5 marker:text-ink-3">
      {props.children}
    </ul>
  );
}

function OrderedList(props: ComponentPropsWithoutRef<"ol">) {
  return (
    <ol className="flex list-decimal flex-col gap-1 pl-5 marker:text-ink-3">
      {props.children}
    </ol>
  );
}

function ListItem(props: ComponentPropsWithoutRef<"li">) {
  return <li>{props.children}</li>;
}

function Anchor(props: ComponentPropsWithoutRef<"a">) {
  return (
    <a
      {...props}
      target="_blank"
      rel="noreferrer"
      className="text-accent underline underline-offset-2 hover:text-accent-hover"
    >
      {props.children}
    </a>
  );
}

/** 표 컨테이너 — `primitives.tsx` `DataTable` 과 동일한 스크롤 래퍼. */
function Table(props: ComponentPropsWithoutRef<"table">) {
  return (
    <div className="thin-scroll overflow-x-auto">
      <table className="w-full border-collapse font-mono text-data tabular-nums">
        {props.children}
      </table>
    </div>
  );
}

function TableHead(props: ComponentPropsWithoutRef<"thead">) {
  return <thead>{props.children}</thead>;
}

function TableRow(props: ComponentPropsWithoutRef<"tr">) {
  // thead 안의 tr 은 DataTable 과 같은 헤더 룰(진한 구분선, last 에도 룰 유지),
  // tbody 안의 tr 은 얇은 구분선(last 는 없음). react-markdown 은 부모 태그를
  // props 로 넘기지 않으므로 `thead &` 조상 선택자로 갈라서 색은 상속시킨다.
  return (
    <tr className="border-b border-line last:border-0 [thead_&]:border-line-strong [thead_&]:text-ink-3 [thead_&]:last:border-b">
      {props.children}
    </tr>
  );
}

function TableHeaderCell(props: ComponentPropsWithoutRef<"th">) {
  return (
    <th className="whitespace-nowrap px-2 py-1.5 text-left font-medium">
      {props.children}
    </th>
  );
}

function TableCell(props: ComponentPropsWithoutRef<"td">) {
  return (
    <td className="whitespace-nowrap px-2 py-1.5 text-ink first:text-ink-2">
      {props.children}
    </td>
  );
}

/** 인라인 코드. 언어 클래스(`language-*`)가 없으면 코드 펜스가 아니라 인라인이다. */
function Code(props: ComponentPropsWithoutRef<"code">) {
  const isBlock = /\blanguage-/.test(props.className ?? "");
  if (isBlock) return <code className={props.className}>{props.children}</code>;
  return (
    <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.9em] text-ink">
      {props.children}
    </code>
  );
}

/** 코드 펜스 블록. 하이라이팅 없음(현행과 동일) — 단색 배경 + mono. */
function Pre(props: ComponentPropsWithoutRef<"pre">) {
  return (
    <pre className="thin-scroll overflow-x-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed text-[#d7dce4]">
      {props.children}
    </pre>
  );
}

export function MarkdownText() {
  return (
    <MarkdownTextPrimitive
      remarkPlugins={[remarkGfm]}
      preprocess={preprocess}
      className="flex flex-col gap-2"
      components={{
        h1: Heading1or2,
        h2: Heading1or2,
        h3: Heading3,
        h4: Heading4to6,
        h5: Heading4to6,
        h6: Heading4to6,
        p: Paragraph,
        strong: Strong,
        em: Em,
        blockquote: Blockquote,
        hr: Hr,
        ul: UnorderedList,
        ol: OrderedList,
        li: ListItem,
        a: Anchor,
        table: Table,
        thead: TableHead,
        tr: TableRow,
        th: TableHeaderCell,
        td: TableCell,
        code: Code,
        pre: Pre,
      }}
    />
  );
}
