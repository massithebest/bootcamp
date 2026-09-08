/**
 * 최소 Markdown 뷰어.  외부 Markdown 라이브러리를 쓰지 않고 직접 작성한다
 * (스캐폴딩 27항: Markdown Renderer 임의 추가 금지 · 폐쇄망).
 *
 * 지원: 제목(#~######), 굵게/기울임/인라인코드, 순서 없는/있는 목록,
 *       표(| ... |), 인용(>), 수평선(---), 코드블록(```), 문단.
 * 그 외 문법은 원문 텍스트로 그대로 보여준다.
 */

import {
  Fragment,
  type ReactNode,
} from "react";

import { DataTable } from "./primitives";

export function Markdown({ text }: { text: string }) {
  return <div className="flex flex-col gap-2">{parseBlocks(text)}</div>;
}

function parseBlocks(src: string): ReactNode[] {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;
  const push = (node: ReactNode) => out.push(<Fragment key={key++}>{node}</Fragment>);

  while (i < lines.length) {
    const line = lines[i];

    // 빈 줄
    if (line.trim() === "") {
      i++;
      continue;
    }

    // 코드블록 ```
    const fence = line.match(/^```(.*)$/);
    if (fence) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; // 닫는 ```
      push(
        <pre className="thin-scroll overflow-x-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed text-[#d7dce4]">
          {buf.join("\n")}
        </pre>,
      );
      continue;
    }

    // 수평선
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      push(<hr className="border-0 border-t border-line" />);
      i++;
      continue;
    }

    // 제목
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      push(renderHeading(level, heading[2]));
      i++;
      continue;
    }

    // 표:  | ... |  다음 줄이 | --- | 형태
    if (
      line.trim().startsWith("|") &&
      i + 1 < lines.length &&
      /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) &&
      lines[i + 1].includes("-")
    ) {
      const header = splitRow(line);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      push(<MarkdownTable header={header} rows={rows} />);
      continue;
    }

    // 인용
    if (/^>\s?/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      push(
        <blockquote className="border-l-2 border-line-strong pl-3 text-ink-2">
          {buf.map((b, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {renderInline(b)}
            </Fragment>
          ))}
        </blockquote>,
      );
      continue;
    }

    // 순서 있는 목록
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      push(
        <ol className="flex list-decimal flex-col gap-1 pl-5 marker:text-ink-3">
          {items.map((it, j) => (
            <li key={j}>{renderInline(it)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // 순서 없는 목록  (-, *, ·)
    if (/^\s*([-*]|·)\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*([-*]|·)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*]|·)\s+/, ""));
        i++;
      }
      push(
        <ul className="flex list-disc flex-col gap-1 pl-5 marker:text-ink-3">
          {items.map((it, j) => (
            <li key={j}>{renderInline(it)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // 문단 (빈 줄 / 블록 시작 전까지)
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,6}\s|```|>\s?|\s*([-*]|·)\s+|\s*\d+\.\s+)/.test(lines[i]) &&
      !/^(-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim()) &&
      !(lines[i].trim().startsWith("|") && lines[i].includes("|"))
    ) {
      para.push(lines[i]);
      i++;
    }
    if (para.length > 0) {
      push(
        <p className="leading-[1.6]">
          {para.map((b, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {renderInline(b)}
            </Fragment>
          ))}
        </p>,
      );
      continue;
    }

    // 어느 규칙에도 안 걸리면 원문 그대로
    push(<p className="leading-[1.6]">{renderInline(line)}</p>);
    i++;
  }

  return out;
}

function renderHeading(level: number, raw: string): ReactNode {
  const content = renderInline(raw);
  if (level <= 2)
    return <h3 className="text-ui-lg font-semibold text-ink">{content}</h3>;
  if (level === 3)
    return <h4 className="text-ui font-semibold text-ink">{content}</h4>;
  return (
    <h5 className="text-ui font-semibold text-ink-2">{content}</h5>
  );
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

function MarkdownTable({
  header,
  rows,
}: {
  header: string[];
  rows: string[][];
}) {
  // 셀 안의 인라인 문법(굵게 등)은 텍스트로만 정규화하여 DataTable 에 넘긴다.
  const clean = (s: string) => s.replace(/\*\*|`|\*/g, "");
  return (
    <DataTable
      columns={header.map(clean)}
      rows={rows.map((r) => r.map(clean))}
    />
  );
}

/** 인라인: **굵게**, *기울임*, `코드`. */
function renderInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.9em] text-ink"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={i} className="italic">
          {part.slice(1, -1)}
        </em>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}
