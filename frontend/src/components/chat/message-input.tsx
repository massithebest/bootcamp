/**
 * 사용자 입력.  텍스트 입력 · Enter 전송 · Shift+Enter 줄바꿈 · 빈 메시지 방지 ·
 * 실행 중 중복 전송 방지.
 */

"use client";

import { useRef, useState, type KeyboardEvent } from "react";

export function MessageInput({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (message: string) => void;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement | null>(null);

  const resize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 176)}px`;
  };

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    requestAnimationFrame(resize);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-line bg-canvas px-4 py-3">
      <div className="mx-auto flex max-w-reading items-end gap-2">
        <div className="flex flex-1 flex-col rounded border border-line-strong bg-canvas focus-within:border-accent">
          <textarea
            ref={ref}
            rows={1}
            value={value}
            disabled={disabled}
            placeholder="생산계획에 대해 질문하세요. 예: 9월 A라인에서 KRA-1180 1,000개 가능한가?"
            onChange={(e) => {
              setValue(e.target.value);
              resize();
            }}
            onKeyDown={handleKeyDown}
            className="max-h-44 resize-none bg-transparent px-3 py-2 text-ui text-ink outline-none placeholder:text-ink-3 disabled:opacity-60"
          />
          <div className="px-3 pb-1.5 text-[0.625rem] text-ink-3">
            Enter 전송 · Shift+Enter 줄바꿈
          </div>
        </div>
        <button
          type="button"
          onClick={submit}
          disabled={disabled || value.trim().length === 0}
          className="h-9 shrink-0 rounded bg-accent px-3.5 text-ui font-medium text-accent-ink transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-3"
        >
          전송
        </button>
      </div>
    </div>
  );
}
