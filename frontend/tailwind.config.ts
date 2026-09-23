import type { Config } from "tailwindcss";

/**
 * 디자인 토큰. "계획 검토 워크벤치" 성격 — 무채색 표면 + 액센트 1개 + 상태 3색.
 * 색은 CSS 변수(globals.css)로 정의하고 여기서 semantic 이름에 매핑한다.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 표면 3단계
        canvas: "var(--canvas)", // 중앙 대화 영역 (가장 밝음)
        surface: "var(--surface)", // 사이드바 / 인스펙터
        "surface-2": "var(--surface-2)", // hover / 중첩 영역
        // 선
        line: "var(--line)",
        "line-strong": "var(--line-strong)",
        // 텍스트
        ink: "var(--ink)",
        "ink-2": "var(--ink-2)",
        "ink-3": "var(--ink-3)",
        // 액센트 (live 상태 전용: streaming/running/connected/selected/focus)
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-weak": "var(--accent-weak)",
        "accent-ink": "var(--accent-ink)",
        // 상태 3색 (저채도)
        "ok-ink": "var(--ok-ink)",
        "ok-weak": "var(--ok-weak)",
        "warn-ink": "var(--warn-ink)",
        "warn-weak": "var(--warn-weak)",
        "block-ink": "var(--block-ink)",
        "block-weak": "var(--block-weak)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }], // 11px 메타/표식
        data: ["0.75rem", { lineHeight: "1.15rem" }], // 12px mono 데이터 행
        ui: ["0.8125rem", { lineHeight: "1.35rem" }], // 13px 본문 기본
        "ui-lg": ["0.875rem", { lineHeight: "1.5rem" }], // 14px 살짝 큰 본문
      },
      borderRadius: {
        // document 계층(6px): 패널·경고·툴 카드 등 bare `rounded` 기본값.
        DEFAULT: "0.375rem",
      },
      transitionTimingFunction: {
        panel: "cubic-bezier(0.22, 0.61, 0.36, 1)",
      },
      maxWidth: {
        reading: "47.5rem", // 760px 대화 읽기 컬럼
      },
    },
  },
  plugins: [],
};

export default config;
