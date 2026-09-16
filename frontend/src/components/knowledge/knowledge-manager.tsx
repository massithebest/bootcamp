import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { fetchDocument, fetchKnowledgeEntries, fetchKnowledgeEntry, saveDocument, changeDocument } from "@/lib/knowledge-api";
import { useKnowledgeResource } from "@/hooks/use-knowledge-resource";
import { KNOWLEDGE_LABELS, STATUS_LABELS, type DocumentFields, type KnowledgeDocument, type KnowledgeEntry, type KnowledgeTarget } from "@/types/knowledge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { buttonClass, controlClass, EntryStatus, ResourceState } from "./shared";
import { StructuredDetail } from "./structured-detail";

export interface KnowledgeManagerHandle { requestLeave: (next: () => void) => void; open: (target?: KnowledgeTarget) => void }
type Form = Omit<DocumentFields, "tags"> & { tagsText: string };
const emptyForm: Form = { title: "", content: "", category: "업무 지식", tagsText: "", owner: "", source: "" };
const formFrom = (fields: DocumentFields): Form => ({ title: fields.title, content: fields.content, category: fields.category, tagsText: fields.tags.join(", "), owner: fields.owner, source: fields.source });
const ACTION_LABELS: Record<string, string> = { save: "초안 저장", review: "검토 완료", activate: "활성화", deactivate: "비활성화", archive: "보관" };

export const KnowledgeManager = forwardRef<KnowledgeManagerHandle>(function KnowledgeManager(_, ref) {
  const [query, setQuery] = useState("");
  const loadList = useCallback((signal: AbortSignal) => fetchKnowledgeEntries(signal, query), [query]);
  const list = useKnowledgeResource(loadList);
  const [selection, setSelection] = useState<KnowledgeTarget | "new" | null>(null);
  const [doc, setDoc] = useState<KnowledgeDocument>();
  const [entry, setEntry] = useState<KnowledgeEntry>();
  const [form, setForm] = useState<Form>(emptyForm);
  const [baseline, setBaseline] = useState<Form>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [actor, setActor] = useState("");
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [active, setActive] = useState("");
  const [pending, setPending] = useState<(() => void) | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const dirty = JSON.stringify(form) !== JSON.stringify(baseline);
  const requestLeave = useCallback((next: () => void) => {
    if (busy) return;
    if (dirty) setPending(() => next); else next();
  }, [busy, dirty]);
  useImperativeHandle(ref, () => ({ requestLeave, open: target => { setSelection(target ?? null); setNotice(""); } }), [requestLeave]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  useEffect(() => {
    const controller = new AbortController();
    setError(undefined); setDoc(undefined); setEntry(undefined); setForm(emptyForm); setBaseline(emptyForm); setActor(""); setNote("");
    if (!selection || selection === "new") { setLoading(false); return; }
    setLoading(true);
    const load = async () => {
      if (selection.kind === "document") {
        const value = await fetchDocument(selection.id, controller.signal);
        const selected = selection.version === undefined ? value.versions[0] : value.versions.find(v => v.version === selection.version);
        if (!selected) throw new Error("인용한 버전을 찾을 수 없습니다.");
        if (!controller.signal.aborted) { setDoc(value); const next = formFrom(selected); setForm(next); setBaseline(next); }
      } else {
        const value = await fetchKnowledgeEntry(selection.kind, selection.id, controller.signal);
        if (!controller.signal.aborted) setEntry(value);
      }
    };
    load().catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "불러오지 못했습니다."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selection, reload]);
  useEffect(() => { if (selection && !loading) titleRef.current?.focus(); }, [selection, loading]);

  const selectedVersion = doc && (selection && selection !== "new" && selection.version !== undefined ? doc.versions.find(v => v.version === selection.version) : doc.versions[0]);
  const historical = !!(selection && selection !== "new" && selection.version !== undefined);
  const editable = !historical && !doc?.archived && (selection === "new" || !!doc);
  async function save(): Promise<boolean> {
    if (!formRef.current?.reportValidity()) return false;
    setBusy(true); setError(undefined);
    try {
      const { tagsText, ...fields } = form;
      const result = await saveDocument({ ...fields, tags: [...new Set(tagsText.split(",").map(t => t.trim()).filter(Boolean))] }, doc?.id, doc?.revision);
      setDoc(result); const next = formFrom(result.versions[0]); setForm(next); setBaseline(next);
      if (selection === "new") setSelection({ kind: "document", id: result.id });
      setNotice("초안을 저장했습니다. 검토 후 활성화하면 모든 대화의 검색에 반영됩니다.");
      return true;
    } catch (e) { setError(e instanceof Error ? e.message : "저장하지 못했습니다."); return false; }
    finally { setBusy(false); }
  }
  async function act(action: "review" | "activate" | "deactivate" | "archive") {
    if (!doc || !selectedVersion || !actor.trim() || (action === "review" && !note.trim())) { setError("기록할 작업자와 검토 시 검토 근거를 입력하세요."); return; }
    setBusy(true); setError(undefined);
    try {
      const result = await changeDocument(doc.id, action, doc.revision, actor, selectedVersion.version, note);
      setDoc(result); setNotice(`${ACTION_LABELS[action]}했습니다.`);
    } catch (e) { setError(e instanceof Error ? e.message : "변경하지 못했습니다."); }
    finally { setBusy(false); }
  }
  const rows = list.data?.filter(e => (!kind || e.type === kind) && (!status || e.status === status) && (!active || (active === "archived" ? e.archived : !e.archived && e.active === (active === "active"))));
  const navigate = (next: KnowledgeTarget | "new" | null) => requestLeave(() => { setSelection(next); setNotice(""); });
  const field = (name: keyof Form, label: string, max: number, multiline = false) => <label className="block space-y-1 text-ui" key={name}><span className="text-ink-2">{label}{name !== "tagsText" && " *"}</span>{multiline ? <textarea name={name} className={`${controlClass} min-h-64 resize-y`} required readOnly={!editable} maxLength={max} value={form[name]} onChange={e => setForm({ ...form, [name]: e.target.value })} /> : <input name={name} className={controlClass} required={name !== "tagsText"} readOnly={!editable} maxLength={max} value={form[name]} onChange={e => setForm({ ...form, [name]: e.target.value })} />}</label>;
  return <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
    <div className="shrink-0 border-b border-line px-5 py-3"><p className="text-ui text-ink-2">공용 지식 · 활성화 변경은 모든 대화의 이후 검색에 적용됩니다.</p><p className="mt-1 text-2xs text-ink-3">기존 YAML 구조화 지식은 별도 설정 없이 항상 읽기 전용으로 표시됩니다. 작성자와 검토자 이름은 기록용입니다.</p></div>
    <div className="flex min-h-0 flex-1 overflow-hidden">
      <section aria-label="지식 목록" className={`${selection ? "hidden lg:flex" : "flex"} thin-scroll w-full shrink-0 flex-col gap-3 overflow-y-auto border-r border-line p-4 lg:w-72`}>
        <button className={buttonClass} disabled={busy} onClick={() => navigate("new")}>텍스트 지식 등록</button>
        <input className={controlClass} aria-label="관리 지식 검색" placeholder="제목·본문·출처 검색" value={query} onChange={e => setQuery(e.target.value)} />
        <select className={controlClass} aria-label="관리 지식 유형" value={kind} onChange={e => setKind(e.target.value)}><option value="">전체 유형</option>{Object.entries(KNOWLEDGE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
        <div className="flex gap-2"><select aria-label="검토 상태" className={controlClass} value={status} onChange={e => setStatus(e.target.value)}><option value="">전체 검토 상태</option><option value="draft">미검토</option><option value="verified">검토 완료</option></select><select aria-label="활성 여부" className={controlClass} value={active} onChange={e => setActive(e.target.value)}><option value="">전체 사용 상태</option><option value="active">검색 반영</option><option value="inactive">검색 제외</option><option value="archived">보관됨</option></select></div>
        <ResourceState {...list} retry={list.reload} />
        {rows?.length === 0 && <p className="text-ui text-ink-3">일치하는 지식이 없습니다.</p>}
        <ul className="divide-y divide-line">{rows?.map(e => {
          const selected = selection && selection !== "new" && selection.id === e.id && selection.kind === e.type;
          return <li key={`${e.type}:${e.id}`}><button type="button" aria-current={selected ? "true" : undefined} className={`w-full space-y-1.5 border-l-2 px-3 py-3 text-left transition-colors hover:bg-surface-2 ${selected ? "border-accent bg-accent-weak" : "border-transparent"}`} onClick={() => navigate({ kind: e.type, id: e.id })}><span className="flex items-start justify-between gap-2"><span className="text-2xs font-medium text-ink-2">{KNOWLEDGE_LABELS[e.type]}</span><EntryStatus entry={e} /></span><span className="block break-words text-ui font-semibold text-ink">{e.title}</span><span className="block line-clamp-2 text-2xs leading-relaxed text-ink-2">{e.summary || "요약 없음"}</span></button></li>;
        })}</ul>
      </section>
      <section aria-label="지식 상세" className={`${selection ? "flex" : "hidden lg:flex"} thin-scroll min-w-0 flex-1 flex-col overflow-y-auto p-4 sm:p-6`}>
        {selection && <button className={`${buttonClass} mb-4 self-start lg:hidden`} onClick={() => navigate(null)}>← 목록으로</button>}
        {!selection && <p className="my-auto text-center text-ui text-ink-3">지식을 선택해 내용을 확인하거나 텍스트 지식을 등록하세요.</p>}
        <div className="mx-auto w-full max-w-4xl space-y-4">
          {selection && <h2 ref={titleRef} tabIndex={-1} className="text-ui-lg font-semibold outline-none">{selection === "new" ? "텍스트 지식 등록" : entry?.title ?? selectedVersion?.title ?? "지식 상세"}</h2>}
          <ResourceState loading={loading} error={error} retry={() => requestLeave(() => setReload(v => v + 1))} />
          {notice && <p role="status" className="border-l-2 border-ok-ink bg-ok-weak p-3 text-ui">{notice}</p>}
          {entry && <><EntryStatus entry={entry} /><p className="text-ui text-ink-2">구조화 지식 · 읽기 전용 · 담당: {entry.owner || "미기록"} · 출처: {entry.source || "미기록"}</p><StructuredDetail data={entry.detail ?? {}} /></>}
          {(selection === "new" || doc) && !loading && <>
            {doc && selectedVersion && <><div className="flex flex-wrap items-center gap-3"><EntryStatus entry={{ status: selectedVersion.status, active: doc.active_version !== null, archived: doc.archived }} /><span className="text-2xs text-ink-2">표시 v{selectedVersion.version} · 검색 버전 {doc.active_version ? `v${doc.active_version}` : "없음"}</span>{historical && <button className={buttonClass} onClick={() => navigate({ kind: "document", id: doc.id })}>최신 버전 열기</button>}</div>{historical && <p className="text-ui text-ink-2">인용한 버전의 보존된 내용입니다. 최신 내용 및 현재 검색 상태와 다를 수 있습니다.</p>}</>}
            <form ref={formRef} onSubmit={e => { e.preventDefault(); void save(); }} className="space-y-4">
              <fieldset disabled={busy} className="space-y-4">
                {field("title", "제목", 200)}
                <div className="grid gap-4 sm:grid-cols-2">{field("category", "분류", 100)}{field("tagsText", "태그 (쉼표 구분)", 2400)}</div>
                {field("content", "본문", 100000, true)}
                <div className="grid gap-4 sm:grid-cols-2">{field("owner", "담당자 / 작성자", 100)}{field("source", "출처", 500)}</div>
                {editable && <div className="flex items-center gap-3"><button type="submit" className={`${buttonClass} border-accent bg-accent-weak text-accent`} disabled={busy || !dirty}>초안 저장</button><span className="text-2xs text-ink-3">{dirty ? "저장하지 않은 변경 있음" : "저장된 내용"}</span></div>}
              </fieldset>
            </form>
            {doc && selectedVersion && <>
              {doc.active_version !== null && doc.active_version !== selectedVersion.version && <details className="border-t border-line pt-4" open><summary className="cursor-pointer text-ui font-semibold">현재 사용본과 수정본 비교</summary><div className="mt-3 grid gap-3 xl:grid-cols-2">{[doc.versions.find(v => v.version === doc.active_version), selectedVersion].map((v, index) => v && <div key={index} className="min-w-0 rounded border border-line p-3"><p className="text-ui font-semibold">{index === 0 ? "현재 사용" : "수정"} v{v.version} · {v.title}</p><p className="text-2xs text-ink-3">{v.category} · {v.tags.join(", ")} · {v.owner} · {v.source}</p><pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans text-ui">{v.content}</pre></div>)}</div></details>}
              {!historical && !doc.archived && <section className="space-y-3 border-t border-line pt-4" aria-label="검토 및 적용"><h3 className="text-ui font-semibold">검토 및 적용</h3><p className="text-2xs text-ink-2">기술 테스트 통과만으로 검토 완료하지 않습니다. 담당자가 업무 정의와 출처를 확인하세요.</p><label className="block text-ui">작업자 / 검토자<input className={`${controlClass} mt-1`} value={actor} maxLength={100} onChange={e => setActor(e.target.value)} /></label><label className="block text-ui">검토 근거<textarea className={`${controlClass} mt-1`} value={note} maxLength={2000} onChange={e => setNote(e.target.value)} /></label><div className="flex flex-wrap gap-2"><button className={buttonClass} disabled={busy || dirty || !actor.trim() || !note.trim() || selectedVersion.status !== "draft"} onClick={() => void act("review")}>검토 완료</button><button className={buttonClass} disabled={busy || dirty || !actor.trim() || selectedVersion.status !== "verified" || doc.active_version === selectedVersion.version} onClick={() => void act("activate")}>이 버전 활성화</button><button className={buttonClass} disabled={busy || dirty || !actor.trim() || doc.active_version === null} onClick={() => void act("deactivate")}>비활성화</button><button className={buttonClass} disabled={busy || dirty || !actor.trim()} onClick={() => { if (window.confirm("보관하면 이후 검색에서 제외되고 편집할 수 없습니다. 보관할까요?")) void act("archive"); }}>보관</button></div></section>}
              {selectedVersion.status === "verified" && <p className="text-2xs text-ink-2">검토: {selectedVersion.reviewer} · {selectedVersion.reviewed_at}<br />근거: {selectedVersion.review_note}</p>}
              <details className="border-t border-line pt-4"><summary className="cursor-pointer text-ui font-semibold">버전 및 변경 이력 ({doc.versions.length}개 버전)</summary><div className="my-3 flex flex-wrap gap-2">{doc.versions.map(v => <button key={v.version} className={buttonClass} onClick={() => navigate({ kind: "document", id: doc.id, version: v.version })}>v{v.version} · {STATUS_LABELS[v.status]}</button>)}</div><ul className="space-y-2">{doc.history.map(h => <li key={h.revision} className="text-2xs text-ink-2">{h.at} · {ACTION_LABELS[h.action] ?? h.action} {h.version && `v${h.version}`} · {h.actor}<p>{h.note}</p></li>)}</ul></details>
            </>}
          </>}
        </div>
      </section>
    </div>
    <Dialog open={pending !== null} onOpenChange={open => { if (!open && !busy) setPending(null); }}><DialogContent showCloseButton={!busy}><DialogTitle>저장하지 않은 변경</DialogTitle><DialogDescription>이동하기 전에 초안을 저장하거나 변경을 취소하세요.</DialogDescription><div className="flex flex-wrap gap-2"><button className={buttonClass} disabled={busy} onClick={async () => { const next = pending; if (await save()) { setPending(null); next?.(); } }}>저장 후 이동</button><button className={buttonClass} disabled={busy} onClick={() => { const next = pending; setForm(baseline); setPending(null); next?.(); }}>변경 취소 후 이동</button><button className={buttonClass} disabled={busy} onClick={() => setPending(null)}>계속 편집</button></div></DialogContent></Dialog>
  </div>;
});
