/**
 * 우측 컨텍스트 인스펙터 — Skills / Metadata / Prompt.
 * 모든 값은 더미. 향후 Skills API / Session Metadata / Prompt 편집 API 와 연결.
 */

"use client";

import { useState, type ReactNode } from "react";

import {
  SESSION_METADATA,
  SKILLS,
  SYSTEM_PROMPT,
} from "@/lib/dummy";
import { Disclosure, StatusDot, type Tone } from "./primitives";
import type { Skill } from "@/types/workspace";

type Tab = "skills" | "metadata" | "prompt";

const TABS: { id: Tab; label: string }[] = [
  { id: "skills", label: "Skills" },
  { id: "metadata", label: "메타" },
  { id: "prompt", label: "프롬프트" },
];

export function ContextInspector({ onCollapse }: { onCollapse: () => void }) {
  const [tab, setTab] = useState<Tab>("skills");

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center gap-1 border-b border-line px-2 py-2">
        <div className="flex flex-1 gap-0.5">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded px-2 py-1 text-2xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-accent-weak text-accent"
                  : "text-ink-3 hover:bg-surface-2 hover:text-ink-2"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onCollapse}
          aria-label="인스펙터 접기"
          className="rounded p-1 text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <svg viewBox="0 0 12 12" width="13" height="13" aria-hidden>
            <path
              d="M4.5 2.5 8 6l-3.5 3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto p-3">
        {tab === "skills" && <SkillsPanel />}
        {tab === "metadata" && <MetadataPanel />}
        {tab === "prompt" && <PromptPanel />}
      </div>
    </div>
  );
}

function SkillsPanel() {
  const [skills, setSkills] = useState<Skill[]>(SKILLS);
  const toggle = (toolName: string) =>
    setSkills((prev) =>
      prev.map((s) =>
        s.toolName === toolName ? { ...s, enabled: !s.enabled } : s,
      ),
    );

  return (
    <ul className="flex flex-col gap-2.5">
      {skills.map((s) => (
        <li key={s.toolName} className="flex gap-2.5">
          <button
            type="button"
            role="switch"
            aria-checked={s.enabled}
            aria-label={`${s.label} ${s.enabled ? "비활성화" : "활성화"}`}
            onClick={() => toggle(s.toolName)}
            className={`mt-0.5 flex h-4 w-7 shrink-0 items-center rounded-full px-0.5 transition-colors ${
              s.enabled ? "justify-end bg-accent" : "justify-start bg-line-strong"
            }`}
          >
            <span className="h-3 w-3 rounded-full bg-canvas" />
          </button>
          <div className="min-w-0 flex-1">
            <p
              className={`text-ui font-medium ${
                s.enabled ? "text-ink" : "text-ink-3"
              }`}
            >
              {s.label}
            </p>
            <p className="text-2xs leading-snug text-ink-3">{s.description}</p>
            <p className="mt-0.5 font-mono text-[0.625rem] text-ink-3">
              {s.toolName}
              {s.lastCalledAt ? ` · 마지막 호출 ${s.lastCalledAt}` : " · 호출 없음"}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function MetadataPanel() {
  const m = SESSION_METADATA;
  const rows: [string, ReactNode][] = [
    ["사용 모델", <span key="m" className="font-mono">{m.model}</span>],
    ["호출된 도구", `${m.toolCallCount}회`],
    [
      "응답 시간",
      m.lastResponseSeconds !== null
        ? `${m.lastResponseSeconds}초 (평균 ${m.avgResponseSeconds}초)`
        : "—",
    ],
    ["데이터 기준일자", m.dataAsOf],
  ];

  return (
    <div className="flex flex-col gap-3">
      <dl className="flex flex-col gap-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-ui">
            <dt className="shrink-0 text-ink-3">{k}</dt>
            <dd className="text-right tabular-nums text-ink">{v}</dd>
          </div>
        ))}
      </dl>

      <div className="flex items-center justify-between gap-3 border-t border-line pt-3 text-ui">
        <span className="text-ink-3">시뮬레이션 서버</span>
        <span className="flex items-center gap-1.5 text-ink">
          <StatusDot tone={m.simulationServer.status as Tone} />
          {m.simulationServer.label}
        </span>
      </div>
    </div>
  );
}

function PromptPanel() {
  const [content, setContent] = useState(SYSTEM_PROMPT.content);
  const dirty = content !== SYSTEM_PROMPT.content;
  const latest = SYSTEM_PROMPT.revisions[0];

  return (
    <div className="flex flex-col gap-2">
      <p className="text-2xs text-ink-3">
        마지막 수정 {latest.version} · {latest.editedAt} · {latest.editedBy}
      </p>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        spellCheck={false}
        className="thin-scroll h-64 resize-none rounded border border-line-strong bg-canvas p-2.5 font-mono text-data leading-relaxed text-ink outline-none focus:border-accent"
      />

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!dirty}
          className="rounded bg-accent px-2.5 py-1 text-2xs font-medium text-accent-ink transition-colors hover:bg-accent-hover disabled:bg-surface-2 disabled:text-ink-3"
        >
          저장
        </button>
        {dirty && (
          <button
            type="button"
            onClick={() => setContent(SYSTEM_PROMPT.content)}
            className="text-2xs text-ink-3 hover:text-ink"
          >
            되돌리기
          </button>
        )}
      </div>

      <Disclosure summary={`변경 이력 ${SYSTEM_PROMPT.revisions.length}건`} dense>
        <ul className="mt-1 flex flex-col gap-2 border-l border-line pl-3">
          {SYSTEM_PROMPT.revisions.map((r) => (
            <li key={r.version} className="text-2xs">
              <span className="font-mono text-ink-2">{r.version}</span>
              <span className="text-ink-3"> · {r.editedAt} · {r.editedBy}</span>
              <p className="text-ink-2">{r.note}</p>
            </li>
          ))}
        </ul>
      </Disclosure>
    </div>
  );
}
