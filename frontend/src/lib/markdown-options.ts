import type { Options as MarkdownOptions } from "react-markdown";
import remarkGfm, { type Options as GfmOptions } from "remark-gfm";
import { remarkChatHeadings } from "@/lib/markdown-headings";

/**
 * 한국어 범위 표기("215~216", "1월~6월")가 한 문장에 두 번 나오면 기본 GFM 은 그 사이를
 * 취소선으로 바꾼다. 물결표 두 개(`~~삭제~~`)만 취소선으로 본다.
 */
export const GFM_OPTIONS: GfmOptions = { singleTilde: false };

/** 채팅 답변 Markdown 플러그인. */
export const CHAT_REMARK_PLUGINS: NonNullable<MarkdownOptions["remarkPlugins"]> = [
  [remarkGfm, GFM_OPTIONS],
  remarkChatHeadings,
];
