/** Read-only contextual discovery. Changes belong in the central management view. */
import { useCallback, useState } from "react";
import { ChevronRightIcon } from "lucide-react";
import { fetchKnowledgeEntries, fetchKnowledgeSkill, fetchKnowledgeSkills, fetchKnowledgeTools } from "@/lib/knowledge-api";
import { useKnowledgeResource } from "@/hooks/use-knowledge-resource";
import { controlClass, EntryStatus, ResourceState } from "@/components/knowledge/shared";
import { KNOWLEDGE_LABELS } from "@/types/knowledge";
import { SkillMarkdown } from "./skill-markdown";

type Tab = "knowledge" | "tools" | "skills";
const TABS: { id: Tab; label: string }[] = [{ id: "tools", label: "도구" }, { id: "skills", label: "스킬" }, { id: "knowledge", label: "지식" }];
export function ContextInspector({ onCollapse }: { onCollapse: () => void }) {
  const [tab, setTab] = useState<Tab>("tools");
  return <div className="flex h-full flex-col bg-surface">
    <div className="flex h-16 shrink-0 items-center gap-1 border-b border-line px-2">
      <div role="tablist" aria-label="참고 정보" className="flex flex-1 gap-1" onKeyDown={event => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const index = TABS.findIndex(t => t.id === tab);
        const next = event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : (index + (event.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length;
        setTab(TABS[next].id);
        (event.currentTarget.children[next] as HTMLButtonElement).focus();
      }}>
        {TABS.map(t => <button key={t.id} id={`inspector-tab-${t.id}`} role="tab" aria-selected={tab === t.id} aria-controls={`inspector-panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1} onClick={() => setTab(t.id)} className={`rounded px-2 py-1 text-ui ${tab === t.id ? "bg-accent-weak text-accent" : "text-ink-2 hover:bg-surface-2"}`}>{t.label}</button>)}
      </div>
      <button onClick={onCollapse} aria-label="인스펙터 접기" className="rounded px-2 py-1 text-ink-2 hover:bg-surface-2">›</button>
    </div>
    {TABS.map(t => <div key={t.id} role="tabpanel" hidden={tab !== t.id} id={`inspector-panel-${t.id}`} aria-labelledby={`inspector-tab-${t.id}`} className="thin-scroll min-h-0 flex-1 overflow-y-auto p-3 [scrollbar-gutter:stable]">
      {t.id === "tools" ? <ToolsPanel /> : t.id === "skills" ? <SkillsPanel /> : <KnowledgePanel />}
    </div>)}
  </div>;
}
function KnowledgePanel() {
  const [query, setQuery] = useState("");
  const load = useCallback((signal: AbortSignal) => fetchKnowledgeEntries(signal, query), [query]);
  const resource = useKnowledgeResource(load);
  const [kind, setKind] = useState("");
  const rows = resource.data?.filter(e => !e.archived && (!kind || e.type === kind));
  return <div className="space-y-3">
    <p className="text-2xs text-ink-2">Agent가 참고할 수 있는 공용 지식입니다.</p>
    <input aria-label="우측 지식 검색" placeholder="지식 검색" className={controlClass} value={query} onChange={e => setQuery(e.target.value)} />
    <select aria-label="우측 지식 유형" className={controlClass} value={kind} onChange={e => setKind(e.target.value)}><option value="">전체 유형</option>{Object.entries(KNOWLEDGE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
    <ResourceState {...resource} retry={resource.reload} />
    {rows?.length === 0 && <p className="text-ui text-ink-3">일치하는 지식이 없습니다.</p>}
    <ul className="divide-y divide-line">{rows?.map(e => <li key={`${e.type}:${e.id}`} className="space-y-1 py-3"><p className="break-words text-ui font-semibold">{e.title}<span className="ml-2 font-sans text-2xs font-normal text-ink-3">{KNOWLEDGE_LABELS[e.type]}</span></p><EntryStatus entry={e} /><p className="line-clamp-3 break-words text-2xs text-ink-2">{e.summary || "등록된 설명이 없습니다."}</p></li>)}</ul>
  </div>;
}
function ToolsPanel() {
  const resource = useKnowledgeResource(fetchKnowledgeTools);
  return <div className="space-y-3"><p className="text-2xs text-ink-2">Agent에 등록된 도구입니다. 서비스 연결 상태를 의미하지 않습니다.</p><ResourceState {...resource} retry={resource.reload} />
    {resource.data?.length === 0 && <p>등록된 도구가 없습니다.</p>}
    {resource.data?.map(tool => <details key={tool.name} className="border-b border-line pb-3"><summary className="cursor-pointer break-words font-mono text-data">{tool.name}<span className="ml-2 font-sans text-2xs text-ink-3">사용 가능</span></summary><div className="mt-3 space-y-2 border-l-2 border-line-strong pl-3"><p className="text-ui leading-relaxed text-ink-2">{tool.description}</p><p className="text-2xs leading-relaxed text-ink-2"><span className="font-medium text-ink">결과</span> · {tool.output}</p></div></details>)}
  </div>;
}
function SkillsPanel() {
  const resource = useKnowledgeResource(fetchKnowledgeSkills);
  return <div className="space-y-4"><p className="text-2xs leading-relaxed text-ink-2">질문에 맞춰 Agent가 선택하는 업무 절차입니다.</p><ResourceState {...resource} retry={resource.reload} />{resource.data?.length === 0 && <p>등록된 Skill이 없습니다.</p>}<ul className="space-y-5">{resource.data?.map(s => <SkillItem key={s.name} name={s.name} description={s.description} />)}</ul></div>;
}
function SkillItem({ name, description }: { name: string; description: string }) {
  const [expanded, setExpanded] = useState(false);
  const headingId = `skill-${name}`;
  const contentId = `skill-content-${name}`;
  return <li className="border-b border-line pb-5 last:border-b-0"><article aria-labelledby={headingId}><header><div className="flex min-w-0 items-center gap-2"><h3 id={headingId} className="min-w-0 flex-1"><button type="button" aria-expanded={expanded} aria-controls={contentId} onClick={() => setExpanded(current => !current)} className="flex min-w-0 items-center gap-1.5 rounded py-1 text-left font-mono text-data font-semibold text-ink hover:text-accent"><ChevronRightIcon aria-hidden className={`size-3.5 shrink-0 ${expanded ? "rotate-90" : ""}`} /><span className="min-w-0 [overflow-wrap:anywhere]">{name}</span></button></h3><span className="shrink-0 text-2xs text-ink-3">사용 가능</span></div><p className="mt-2 text-ui leading-[1.65] text-ink-2">{description}</p></header>{expanded && <div id={contentId} className="mt-4 border-l-2 border-line-strong pl-3"><SkillBody name={name} /></div>}</article></li>;
}
function SkillBody({ name }: { name: string }) {
  const load = useCallback((signal: AbortSignal) => fetchKnowledgeSkill(name, signal), [name]);
  const resource = useKnowledgeResource(load);
  return <><ResourceState {...resource} retry={resource.reload} />{resource.data?.content && <SkillMarkdown content={resource.data.content} />}</>;
}
