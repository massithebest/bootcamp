import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { formatTime } from "@/lib/format-time";
import { actOnChange, createChange, fetchChange, fetchKnowledgeGuide, fetchKnowledgeSource, updateChange, validateKnowledge } from "@/lib/knowledge-api";
import {
  KNOWLEDGE_LABELS, PERMISSION_APPROVE, PERMISSION_WRITE, type ChangeAction, type ChangeContent, type ChangeDetail, type FieldData, type KindGuide, type Me,
  type StructuredKind, type ValidationResult,
} from "@/types/knowledge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { buttonClass, controlClass, ResourceState } from "../shared";
import { ChangeStateBadge } from "./change-badge";
import { ChangeHistory } from "./change-history";
import { DiffView } from "./diff-view";
import { FieldEditor, type FieldErrors } from "./field-editor";
import { ValidationSummary } from "./validation-summary";

export type EditorTarget =
  | { type: "new"; kind: StructuredKind }
  | { type: "entry"; kind: StructuredKind; key: string }
  | { type: "change"; id: string };
export interface EntryEditorHandle { save: () => Promise<boolean> }
interface Props { target: EditorTarget; me?: Me; onDirtyChange: (dirty: boolean) => void; onTarget: (target: EditorTarget) => void; onClose: () => void }

type Content = { mode: "form"; data: FieldData } | { mode: "yaml"; yaml: string };
type Tab = "form" | "yaml" | "review";
const TABS: { id: Tab; label: string }[] = [{ id: "form", label: "입력 폼" }, { id: "yaml", label: "원문 YAML" }, { id: "review", label: "변경 검토" }];
const payload = (content: Content): ChangeContent => content.mode === "form" ? { data: content.data } : { yaml: content.yaml };
// 승인·검토 요청 등 1차 액션. accent가 signature color를 겸하므로 accent 채움을 쓴다.
const primaryButton = "rounded border border-accent bg-accent px-3 py-1.5 text-ui text-accent-ink hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50";

/** 구조화 지식 하나의 편집·검토·승인 화면. 초안은 서버 변경 요청으로 저장되고 승인 전에는 런타임에 반영되지 않는다. */
export const EntryEditor = forwardRef<EntryEditorHandle, Props>(function EntryEditor({ target, me, onDirtyChange, onTarget, onClose }, ref) {
  const [guide, setGuide] = useState<KindGuide>();
  const [change, setChange] = useState<ChangeDetail>();
  const [currentYaml, setCurrentYaml] = useState("");
  const [content, setContent] = useState<Content>({ mode: "form", data: {} });
  const [edited, setEdited] = useState(false);
  const [tab, setTab] = useState<Tab>("form");
  const [validation, setValidation] = useState<ValidationResult>();
  const [checking, setChecking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);
  const [decision, setDecision] = useState<"approve" | "reject" | null>(null);
  const [note, setNote] = useState("");
  const titleRef = useRef<HTMLHeadingElement>(null);
  const changeRef = useRef<ChangeDetail>();
  changeRef.current = change;

  const kind: StructuredKind | undefined = target.type === "change" ? change?.kind : target.kind;
  const existingKey = target.type === "entry" ? target.key : change && !change.is_new ? change.key : undefined;
  const canWrite = !!me?.knowledge_management && !!me.permissions.includes(PERMISSION_WRITE);
  const canApprove = !!me?.knowledge_management && !!me.permissions.includes(PERMISSION_APPROVE);
  const isAuthor = !change || change.author.id === me?.id;
  const editable = canWrite && isAuthor && (!change || change.state === "draft" || change.state === "rejected");
  const locked = useMemo(() => new Set(guide && (existingKey !== undefined || change) ? [guide.key_field] : []), [guide, existingKey, change]);

  useEffect(() => onDirtyChange(edited), [edited, onDirtyChange]);
  const applyDetail = useCallback((detail: ChangeDetail, mode: Content["mode"]) => {
    setChange(detail); setCurrentYaml(detail.current_yaml);
    setContent(mode === "yaml" ? { mode: "yaml", yaml: detail.yaml } : { mode: "form", data: detail.data });
    setEdited(false);
  }, []);

  // 대상이 바뀌면 명세와 내용을 새로 불러온다. 방금 저장해 이미 들고 있는 요청은 다시 받지 않는다.
  const targetKey = JSON.stringify(target);
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const load = async () => {
      if (target.type === "change") {
        if (changeRef.current?.id === target.id && reloadTick === 0) { setLoading(false); return; }
        const detail = await fetchChange(target.id, signal);
        const loaded = await fetchKnowledgeGuide(detail.kind, signal);
        if (signal.aborted) return;
        setGuide(loaded); applyDetail(detail, "form");
      } else {
        const loaded = await fetchKnowledgeGuide(target.kind, signal);
        const source = target.type === "entry" ? await fetchKnowledgeSource(target.kind, target.key, signal) : undefined;
        if (signal.aborted) return;
        setGuide(loaded); setChange(undefined); setEdited(false);
        setCurrentYaml(source?.yaml ?? "");
        setContent({ mode: "form", data: source?.data ?? loaded.template });
      }
      setTab("form"); setValidation(undefined); setNotice("");
    };
    setLoading(true); setError(undefined);
    load().catch((e: unknown) => { if (!signal.aborted) setError(e instanceof Error ? e.message : "불러오지 못했습니다."); })
      .finally(() => { if (!signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [targetKey, reloadTick, applyDetail]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!loading && guide) titleRef.current?.focus(); }, [loading, guide === undefined]); // eslint-disable-line react-hooks/exhaustive-deps

  // 입력을 멈추면 서버 검증(모델 + 정합성 dry-run)을 돌린다. 저장하지 않는다.
  useEffect(() => {
    if (!kind || !editable || loading) return;
    const controller = new AbortController();
    setChecking(true);
    const handle = setTimeout(() => {
      validateKnowledge(kind, payload(content), existingKey, controller.signal)
        .then(result => { if (!controller.signal.aborted) { setValidation(result); setChecking(false); } })
        .catch(() => { if (!controller.signal.aborted) { setValidation(undefined); setChecking(false); } });
    }, 500);
    return () => { clearTimeout(handle); controller.abort(); };
  }, [content, kind, editable, loading, existingKey]);

  const errors = useMemo<FieldErrors>(() => {
    const map: FieldErrors = {};
    for (const item of validation?.errors ?? []) if (item.path) (map[item.path] ??= []).push(item.message);
    return map;
  }, [validation]);

  const edit = (next: Content) => { setContent(next); setEdited(true); setNotice(""); };

  async function switchTab(next: Tab) {
    if (next === tab || !kind) return;
    setError(undefined);
    if (next === "review") { setTab(next); return; }
    if (content.mode === "form" && next === "yaml") {
      try { const result = await validateKnowledge(kind, { data: content.data }, existingKey); setValidation(result); setContent({ mode: "yaml", yaml: result.yaml }); setTab(next); }
      catch (e) { setError(e instanceof Error ? e.message : "변환하지 못했습니다."); }
    } else if (content.mode === "yaml" && next === "form") {
      try {
        const result = await validateKnowledge(kind, { yaml: content.yaml }, existingKey);
        setValidation(result);
        if (!result.parsed) { setError("YAML 문법 오류가 있어 폼으로 바꿀 수 없습니다. 아래 오류를 고친 뒤 다시 시도하세요."); return; }
        setContent({ mode: "form", data: result.data }); setTab(next);
      } catch (e) { setError(e instanceof Error ? e.message : "변환하지 못했습니다."); }
    } else setTab(next);
  }
  const onTabKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = TABS.findIndex(t => t.id === tab);
    const next = event.key === "ArrowRight" ? (index + 1) % TABS.length : event.key === "ArrowLeft" ? (index + TABS.length - 1) % TABS.length : event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault(); void switchTab(TABS[next].id);
    document.getElementById(`editor-tab-${TABS[next].id}`)?.focus();
  };

  const fail = (e: unknown, fallback: string) => setError(e instanceof Error ? e.message : fallback);
  /** 화면의 내용을 요청으로 저장한다. 상태를 먼저 반영한 뒤 부모에 알려 방금 만든 요청을 다시 불러오지 않게 한다. */
  async function persist(): Promise<ChangeDetail> {
    const detail = change ? await updateChange(change.id, change.revision, payload(content)) : await createChange(kind!, payload(content), existingKey);
    applyDetail(detail, content.mode);
    if (!change) onTarget({ type: "change", id: detail.id });
    return detail;
  }
  async function save(): Promise<boolean> {
    if (!kind) return false;
    setBusy(true); setError(undefined);
    try { await persist(); setNotice("초안을 저장했습니다. 검토를 요청하면 승인 권한자가 확인합니다."); return true; }
    catch (e) { fail(e, "저장하지 못했습니다."); return false; }
    finally { setBusy(false); }
  }
  useImperativeHandle(ref, () => ({ save }));

  async function transition(action: ChangeAction, message: string, reason = "") {
    setBusy(true); setError(undefined);
    try {
      // 검토 요청은 화면에 보이는 내용을 그대로 보내도록 저장하지 않은 변경을 먼저 저장한다.
      const current = action === "submit" && (edited || !change) ? await persist() : change;
      if (!current) throw new Error("먼저 초안을 저장하세요.");
      const detail = await actOnChange(current.id, action, current.revision, reason);
      applyDetail(detail, content.mode); setNotice(message); setDecision(null); setNote("");
    } catch (e) {
      fail(e, "처리하지 못했습니다.");
      // 검증 실패로 거절됐다면 어느 항목인지 바로 보이도록 결과를 다시 받는다.
      if (kind && action !== "withdraw") validateKnowledge(kind, payload(content), existingKey).then(setValidation).catch(() => undefined);
    } finally { setBusy(false); }
  }

  const proposedYaml = editable ? validation?.yaml ?? change?.yaml ?? "" : change?.yaml ?? validation?.yaml ?? "";
  const selfApprovalBlocked = !!change && change.author.id === me?.id && !me.allow_self_approval;
  const draftKey = content.mode === "form" && guide ? content.data[guide.key_field] : undefined;
  const name = existingKey ?? change?.key ?? (typeof draftKey === "string" && draftKey ? draftKey : "새 지식");
  const title = kind ? `${KNOWLEDGE_LABELS[kind]} · ${name}` : "구조화 지식";
  const readOnlyReason = !me ? "사용자 권한을 확인하지 못해 볼 수만 있습니다."
    : !me.knowledge_management ? "관리 기능이 꺼져 있어 볼 수만 있습니다."
    : !canWrite ? "작성 권한이 없어 볼 수만 있습니다."
    : !isAuthor ? `${change?.author.name}님이 작성한 요청이라 볼 수만 있습니다.`
    : change?.state === "submitted" ? "검토 대기 중에는 수정할 수 없습니다. 요청을 철회하면 다시 수정할 수 있습니다."
    : change && !editable ? "종료된 요청이라 수정할 수 없습니다." : "";
  const lastReject = change?.state === "rejected" ? change.history.find(h => h.action === "reject") : undefined;
  const open = !!change && ["draft", "submitted", "rejected"].includes(change.state);

  return <div className="space-y-5">
    <div className="sticky top-0 z-10 -mt-4 flex flex-wrap items-start justify-between gap-3 border-b border-line bg-canvas pb-3 pt-4 sm:-mt-6 sm:pt-6">
      <div className="min-w-0 space-y-1">
        <h2 ref={titleRef} tabIndex={-1} className="break-words text-ui-lg font-semibold outline-none">{title}</h2>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-ink-2">
          {change ? <><ChangeStateBadge state={change.state} /><span>작성 {change.author.name}</span><span className="tabular-nums">수정 {formatTime(change.updated_at)}</span></> : <span>{existingKey ? "현재 승인본에서 시작한 수정 요청" : "새 지식 요청"} · 아직 저장하지 않았습니다</span>}
        </div>
      </div>
      <button type="button" className={buttonClass} disabled={busy} onClick={onClose}>편집 닫기</button>
    </div>
    <ResourceState loading={loading} error={error && (!guide || loading) ? error : undefined} retry={() => setReloadTick(v => v + 1)} />
    {!loading && guide && kind && <>
      {error && <div role="alert" className="border-l-2 border-warn-ink bg-warn-weak p-3 text-ui"><p>{error}</p>{/다시 불러오세요/.test(error) && <button type="button" className={`${buttonClass} mt-2`} onClick={() => setReloadTick(v => v + 1)}>최신 내용 불러오기</button>}</div>}
      {notice && <p role="status" className="border-l-2 border-ok-ink bg-ok-weak p-3 text-ui">{notice}</p>}
      {lastReject && <div className="border-l-2 border-block-ink bg-block-weak p-3 text-ui"><p className="font-semibold text-block-ink">반려되었습니다 · {lastReject.actor_name}</p><p className="mt-1 whitespace-pre-wrap break-words">{lastReject.note}</p><p className="mt-1 text-2xs text-ink-2">내용을 고쳐 저장하면 초안으로 돌아가고 다시 검토를 요청할 수 있습니다.</p></div>}
      {readOnlyReason && <p className="border-l-2 border-line pl-3 text-ui text-ink-2">{readOnlyReason}</p>}
      {editable && tab !== "review" && <ValidationSummary errors={validation?.errors ?? []} ok={!!validation?.ok} checking={checking} />}
      <div role="tablist" aria-label="편집 보기" className="flex gap-1 border-b border-line" onKeyDown={onTabKey}>
        {TABS.map(item => <button key={item.id} id={`editor-tab-${item.id}`} type="button" role="tab" aria-selected={tab === item.id} aria-controls={`editor-panel-${item.id}`} tabIndex={tab === item.id ? 0 : -1}
          className={`-mb-px border-b-2 px-3 py-2 text-ui focus-visible:outline-2 focus-visible:outline-accent ${tab === item.id ? "border-accent font-semibold text-ink" : "border-transparent text-ink-2 hover:text-ink"}`} onClick={() => void switchTab(item.id)}>{item.label}</button>)}
      </div>
      <div role="tabpanel" id={`editor-panel-${tab}`} aria-labelledby={`editor-tab-${tab}`} className="space-y-4">
        {tab === "form" && content.mode === "form" && <FieldEditor fields={guide.fields} value={content.data} errors={errors} readOnly={!editable} locked={locked} onChange={data => edit({ mode: "form", data })} />}
        {tab === "yaml" && content.mode === "yaml" && <div className="space-y-2">
          <p className="text-2xs text-ink-3">저장하면 서버가 형식을 정리합니다. 주석과 들여쓰기 스타일은 유지되지 않습니다.</p>
          <textarea aria-label="원문 YAML 편집" spellCheck={false} readOnly={!editable} rows={24} className={`${controlClass} thin-scroll resize-y font-mono text-data read-only:bg-surface`} value={content.yaml} onChange={e => edit({ mode: "yaml", yaml: e.target.value })} />
        </div>}
        {tab === "review" && <div className="space-y-6">
          <section className="space-y-2"><h3 className="text-ui font-semibold">현재 승인본과 비교</h3><DiffView before={currentYaml} after={proposedYaml} /></section>
          {change && <section className="space-y-2"><h3 className="text-ui font-semibold">진행 이력</h3><ChangeHistory items={change.history} /></section>}
        </div>}
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
        {editable && <>
          <button type="button" className={buttonClass} disabled={busy || !edited} onClick={() => void save()}>초안 저장</button>
          <button type="button" className={primaryButton} disabled={busy || !validation?.ok || checking} title={validation?.ok ? undefined : "검증을 통과해야 검토를 요청할 수 있습니다."} onClick={() => void transition("submit", "검토를 요청했습니다. 승인 권한자가 확인하면 반영됩니다.")}>검토 요청</button>
        </>}
        {open && isAuthor && canWrite && <button type="button" className={buttonClass} disabled={busy} onClick={() => void transition("withdraw", "요청을 철회했습니다.")}>요청 철회</button>}
        {change?.state === "submitted" && canApprove && <>
          <button type="button" className={primaryButton} disabled={busy || selfApprovalBlocked} onClick={() => { setDecision("approve"); setNote(""); }}>승인</button>
          <button type="button" className={buttonClass} disabled={busy} onClick={() => { setDecision("reject"); setNote(""); }}>반려</button>
          {selfApprovalBlocked && <p className="basis-full text-2xs text-ink-2">작성자 본인은 승인할 수 없습니다. 다른 승인 권한자가 확인해야 합니다.</p>}
        </>}
        {editable && edited && <span className="ml-auto text-2xs text-ink-3">저장하지 않은 변경 있음</span>}
      </div>
    </>}
    <Dialog open={decision !== null} onOpenChange={o => { if (!o && !busy) setDecision(null); }}>
      <DialogContent showCloseButton={!busy}>
        <DialogTitle>{decision === "approve" ? "이 변경을 승인할까요?" : "이 변경을 반려할까요?"}</DialogTitle>
        <DialogDescription>{decision === "approve" ? "승인하면 지식 파일에 기록되고 이후 모든 대화의 검색·Tool·SQL 허용 목록에 바로 반영됩니다." : "반려하면 작성자가 사유를 보고 내용을 고쳐 다시 요청할 수 있습니다."}</DialogDescription>
        <label className="block space-y-1 text-ui"><span className="text-ink-2">{decision === "approve" ? "승인 근거" : "반려 사유"}<span className="ml-1.5 text-2xs text-ink-3">필수</span></span>
          <textarea className={controlClass} rows={4} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} placeholder={decision === "approve" ? "확인한 자료나 검토 내용을 적습니다." : "무엇을 어떻게 고쳐야 하는지 적습니다."} /></label>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={primaryButton} disabled={busy || !note.trim()} onClick={() => void transition(decision!, decision === "approve" ? "승인했습니다. 지식이 즉시 반영되었습니다." : "요청을 반려했습니다.", note)}>{decision === "approve" ? "승인하고 반영" : "반려"}</button>
          <button type="button" className={buttonClass} disabled={busy} onClick={() => setDecision(null)}>취소</button>
        </div>
      </DialogContent>
    </Dialog>
  </div>;
});
