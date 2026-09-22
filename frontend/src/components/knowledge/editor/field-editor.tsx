import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { PlusIcon, XIcon } from "lucide-react";
import type { FieldData, FieldGuide, FieldWidget } from "@/types/knowledge";
import { buttonClass, controlClass } from "../shared";
import { blankRecord } from "./blank-value";

/** 필드 경로(`columns[0].name`) → 오류 메시지. 백엔드 검증 결과의 path 와 같은 표기다. */
export type FieldErrors = Record<string, string[]>;
interface EditorContext { errors: FieldErrors; readOnly: boolean; locked: ReadonlySet<string> }
const Context = createContext<EditorContext>({ errors: {}, readOnly: false, locked: new Set() });

const WIDE: ReadonlySet<FieldWidget> = new Set(["text", "sql", "string_list", "record_list", "object", "map", "json"]);
const iconButton = "shrink-0 rounded p-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink focus-visible:outline-2 focus-visible:outline-accent";
const readonlyClass = "read-only:bg-surface read-only:text-ink-2";
const isObject = (v: unknown): v is FieldData => typeof v === "object" && v !== null && !Array.isArray(v);
const toList = (v: unknown): unknown[] => Array.isArray(v) ? v : typeof v === "string" && v !== "" ? [v] : [];
const domId = (path: string) => `field-${path.replace(/[^\w가-힣]+/g, "-")}`;

function ErrorText({ id, messages }: { id: string; messages: string[] }) {
  if (!messages.length) return null;
  return <p id={id} className="text-2xs text-block-ink">{messages.join(" ")}</p>;
}

/** 필드 하나: 라벨, 도움말, 위젯, 오류. 목록·객체는 fieldset 으로 묶어 스크린 리더가 그룹으로 읽게 한다. */
function Field({ field, value, onChange, path }: { field: FieldGuide; value: unknown; onChange: (next: unknown) => void; path: string }) {
  const { errors, readOnly: formReadOnly, locked } = useContext(Context);
  const id = domId(path);
  const messages = errors[path] ?? [];
  const readOnly = formReadOnly || field.readonly || locked.has(path);
  const describedBy = [field.help && `${id}-help`, messages.length && `${id}-error`].filter(Boolean).join(" ") || undefined;
  const composite = field.widget === "string_list" || field.widget === "record_list" || field.widget === "object" || field.widget === "map";
  const label = <>{field.label}{field.required && !field.readonly && <span className="ml-1.5 text-2xs text-ink-3">필수</span>}</>;
  const help = field.help && <p id={`${id}-help`} className="text-2xs text-ink-3">{field.help}</p>;
  // 선택 문자열을 비우면 키를 제거해 빈 문자열이 YAML 에 남지 않게 한다.
  const commit = (next: unknown) => onChange(!field.required && next === "" ? undefined : next);
  const common = { id, readOnly, "aria-describedby": describedBy, "aria-invalid": messages.length ? true : undefined };

  let control: ReactNode;
  switch (field.widget) {
    case "boolean":
      return <div className={WIDE.has(field.widget) ? "sm:col-span-2" : ""}><label className="flex items-start gap-2 text-ui text-ink"><input type="checkbox" className="mt-1" checked={value === true} disabled={readOnly} aria-describedby={describedBy} onChange={e => onChange(e.target.checked)} />{field.label}</label>{help && <div className="pl-6">{help}</div>}<ErrorText id={`${id}-error`} messages={messages} /></div>;
    case "enum":
      control = readOnly
        ? <p id={id} className="text-ui text-ink">{String(value ?? "")}</p>
        : <select id={id} className={controlClass} value={String(value ?? "")} aria-describedby={describedBy} onChange={e => onChange(e.target.value)}>{field.options?.map(o => <option key={o} value={o}>{o}</option>)}</select>;
      break;
    case "date":
      control = <p id={id} className="text-ui text-ink-2">{value ? String(value) : "승인할 때 기록됩니다"}</p>;
      break;
    case "number":
      control = <input {...common} type="number" className={`${controlClass} ${readonlyClass}`} value={typeof value === "number" ? value : ""} onChange={e => onChange(e.target.value === "" ? 0 : Number(e.target.value))} />;
      break;
    case "text":
      control = <textarea {...common} rows={3} placeholder={field.example} className={`${controlClass} ${readonlyClass} resize-y`} value={String(value ?? "")} onChange={e => commit(e.target.value)} />;
      break;
    case "sql":
      control = <textarea {...common} rows={7} spellCheck={false} placeholder={field.example} className={`${controlClass} ${readonlyClass} thin-scroll resize-y font-mono text-data`} value={String(value ?? "")} onChange={e => commit(e.target.value)} />;
      break;
    case "string_list": control = <StringList field={field} value={value} onChange={onChange} path={path} readOnly={readOnly} />; break;
    case "record_list": control = <RecordList field={field} value={value} onChange={onChange} path={path} readOnly={readOnly} />; break;
    case "object": control = <Fields fields={field.fields ?? []} value={isObject(value) ? value : {}} onChange={onChange} path={path} />; break;
    case "map": control = <MapField field={field} value={value} onChange={onChange} path={path} readOnly={readOnly} />; break;
    case "json": control = <JsonField id={id} value={value} onChange={onChange} readOnly={readOnly} describedBy={describedBy} />; break;
    default:
      control = <input {...common} placeholder={field.example} className={`${controlClass} ${readonlyClass}`} value={String(value ?? "")} onChange={e => commit(e.target.value)} />;
  }
  const wide = WIDE.has(field.widget) ? "sm:col-span-2" : "";
  if (composite) {
    return <fieldset className={`${wide} min-w-0 space-y-1.5 border-0 p-0`} aria-describedby={describedBy}><legend className="p-0 text-ui text-ink-2">{label}</legend>{control}{help}<ErrorText id={`${id}-error`} messages={messages} /></fieldset>;
  }
  return <div className={`${wide} min-w-0 space-y-1`}><label htmlFor={id} className="block text-ui text-ink-2">{label}</label>{control}{help}<ErrorText id={`${id}-error`} messages={messages} /></div>;
}

/** 같은 부모 아래 필드들. 짧은 입력은 두 열, 긴 입력은 한 열을 다 쓴다. */
function Fields({ fields, value, onChange, path }: { fields: FieldGuide[]; value: FieldData; onChange: (next: FieldData) => void; path: string }) {
  const set = (name: string, next: unknown) => {
    const copy = { ...value };
    if (next === undefined) delete copy[name]; else copy[name] = next;
    onChange(copy);
  };
  return <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2">{fields.map(field => <Field key={field.name} field={field} value={value[field.name]} onChange={next => set(field.name, next)} path={path ? `${path}.${field.name}` : field.name} />)}</div>;
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" className={`${buttonClass} inline-flex items-center gap-1.5`} onClick={onClick}><PlusIcon aria-hidden className="size-3" />{label}</button>;
}

function StringList({ field, value, onChange, path, readOnly }: { field: FieldGuide; value: unknown; onChange: (next: unknown) => void; path: string; readOnly: boolean }) {
  const { errors } = useContext(Context);
  const items = toList(value).map(String);
  const replace = (index: number, text: string) => onChange(items.map((item, i) => i === index ? text : item));
  return <div className="space-y-2">
    {items.length === 0 && readOnly && <p className="text-ui text-ink-3">없음</p>}
    <ul className="space-y-2">{items.map((item, index) => {
      const itemErrors = errors[`${path}[${index}]`] ?? [];
      const props = { id: `${domId(path)}-${index}`, readOnly, "aria-label": `${field.label} ${index + 1}`, "aria-invalid": itemErrors.length ? true : undefined, placeholder: field.example, value: item, onChange: (e: { target: { value: string } }) => replace(index, e.target.value) };
      return <li key={index} className="flex items-start gap-1.5">
        <div className="min-w-0 flex-1 space-y-1">
          {field.item_widget === "text" ? <textarea {...props} rows={2} className={`${controlClass} ${readonlyClass} resize-y`} /> : <input {...props} className={`${controlClass} ${readonlyClass}`} />}
          <ErrorText id={`${props.id}-error`} messages={itemErrors} />
        </div>
        {!readOnly && <button type="button" className={iconButton} aria-label={`${field.label} ${index + 1} 삭제`} onClick={() => onChange(items.filter((_, i) => i !== index))}><XIcon aria-hidden className="size-3.5" /></button>}
      </li>;
    })}</ul>
    {!readOnly && <AddButton label={`${field.label} 추가`} onClick={() => onChange([...items, ""])} />}
  </div>;
}

function RecordList({ field, value, onChange, path, readOnly }: { field: FieldGuide; value: unknown; onChange: (next: unknown) => void; path: string; readOnly: boolean }) {
  const records = toList(value).map(item => isObject(item) ? item : {});
  const subFields = field.fields ?? [];
  return <div className="space-y-3">
    {records.length === 0 && readOnly && <p className="text-ui text-ink-3">없음</p>}
    <ul className="space-y-4">{records.map((record, index) => <li key={index} className="space-y-3 border-l-2 border-line pl-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-2xs font-medium tabular-nums text-ink-2">{field.label} {index + 1}</span>
        {!readOnly && <button type="button" className={iconButton} aria-label={`${field.label} ${index + 1} 삭제`} onClick={() => onChange(records.filter((_, i) => i !== index))}><XIcon aria-hidden className="size-3.5" /></button>}
      </div>
      <Fields fields={subFields} value={record} path={`${path}[${index}]`} onChange={next => onChange(records.map((r, i) => i === index ? next : r))} />
    </li>)}</ul>
    {!readOnly && <AddButton label={`${field.label} 추가`} onClick={() => onChange([...records, blankRecord(subFields)])} />}
  </div>;
}

/** 키 이름은 입력이 끝났을 때(blur) 확정한다. 비었거나 겹치면 이전 값으로 되돌린다. */
function MapKey({ name, taken, readOnly, label, onRename }: { name: string; taken: (candidate: string) => boolean; readOnly: boolean; label: string; onRename: (next: string) => void }) {
  const [text, setText] = useState(name);
  useEffect(() => setText(name), [name]);
  const commit = () => { const next = text.trim(); if (!next || (next !== name && taken(next))) setText(name); else if (next !== name) onRename(next); };
  return <input aria-label={label} readOnly={readOnly} className={`${controlClass} ${readonlyClass} font-mono text-data`} value={text} onChange={e => setText(e.target.value)} onBlur={commit} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); commit(); } }} />;
}

function MapField({ field, value, onChange, path, readOnly }: { field: FieldGuide; value: unknown; onChange: (next: unknown) => void; path: string; readOnly: boolean }) {
  const entries = Object.entries(isObject(value) ? value : {});
  const spec = field.value ?? { widget: "string" as FieldWidget };
  const setEntries = (next: [string, unknown][]) => onChange(Object.fromEntries(next));
  const scalar = (item: unknown, apply: (next: unknown) => void, label: string) => spec.widget === "number"
    ? <input type="number" aria-label={label} readOnly={readOnly} className={`${controlClass} ${readonlyClass}`} value={typeof item === "number" ? item : ""} onChange={e => apply(e.target.value === "" ? 0 : Number(e.target.value))} />
    : <input aria-label={label} readOnly={readOnly} className={`${controlClass} ${readonlyClass}`} value={String(item ?? "")} onChange={e => apply(e.target.value)} />;
  return <div className="space-y-3">
    {entries.length === 0 && readOnly && <p className="text-ui text-ink-3">없음</p>}
    <ul className="space-y-3">{entries.map(([key, item], index) => <li key={key} className="space-y-2 border-l-2 border-line pl-3">
      <div className="flex items-center gap-1.5">
        <div className="min-w-0 flex-1"><MapKey name={key} readOnly={readOnly} label={`${field.label} 이름 ${index + 1}`} taken={candidate => entries.some(([k]) => k === candidate)} onRename={next => setEntries(entries.map(([k, v]) => [k === key ? next : k, v]))} /></div>
        {!readOnly && <button type="button" className={iconButton} aria-label={`${field.label} ${key} 삭제`} onClick={() => setEntries(entries.filter(([k]) => k !== key))}><XIcon aria-hidden className="size-3.5" /></button>}
      </div>
      {spec.widget === "object"
        ? <Fields fields={spec.fields ?? []} value={isObject(item) ? item : {}} path={`${path}.${key}`} onChange={next => setEntries(entries.map(([k, v]) => [k, k === key ? next : v]))} />
        : scalar(item, next => setEntries(entries.map(([k, v]) => [k, k === key ? next : v])), `${field.label} ${key} 값`)}
    </li>)}</ul>
    {!readOnly && <AddButton label={`${field.label} 추가`} onClick={() => {
      let n = entries.length + 1; while (entries.some(([k]) => k === `항목${n}`)) n++;
      setEntries([...entries, [`항목${n}`, spec.widget === "object" ? blankRecord(spec.fields ?? []) : spec.widget === "number" ? 0 : ""]]);
    }} />}
  </div>;
}

/** 스키마가 정해지지 않은 필드. 유효한 JSON 일 때만 값에 반영하고 그동안은 입력 문자열을 유지한다. */
function JsonField({ id, value, onChange, readOnly, describedBy }: { id: string; value: unknown; onChange: (next: unknown) => void; readOnly: boolean; describedBy?: string }) {
  const canonical = JSON.stringify(value ?? {}, null, 2);
  const [text, setText] = useState(canonical);
  const [invalid, setInvalid] = useState(false);
  useEffect(() => { try { if (JSON.stringify(JSON.parse(text)) !== JSON.stringify(value ?? {})) { setText(canonical); setInvalid(false); } } catch { /* 입력 중인 잘못된 JSON 은 덮어쓰지 않는다 */ } }, [canonical]); // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="space-y-1">
    <textarea id={id} rows={6} spellCheck={false} readOnly={readOnly} aria-invalid={invalid || undefined} aria-describedby={describedBy} className={`${controlClass} ${readonlyClass} thin-scroll resize-y font-mono text-data`} value={text} onChange={e => { setText(e.target.value); try { onChange(JSON.parse(e.target.value)); setInvalid(false); } catch { setInvalid(true); } }} />
    {invalid && <p className="text-2xs text-block-ink">JSON 형식이 올바르지 않습니다. 올바른 값이 될 때까지 이전 내용이 유지됩니다.</p>}
  </div>;
}

/** 가이드 명세로 그린 편집 폼. 그룹(기본 정보·구조·규칙·관계·관리 정보) 순서는 백엔드 명세를 따른다. */
export function FieldEditor({ fields, value, onChange, errors, readOnly = false, locked }: { fields: FieldGuide[]; value: FieldData; onChange: (next: FieldData) => void; errors: FieldErrors; readOnly?: boolean; locked?: ReadonlySet<string> }) {
  const groups: { name: string; fields: FieldGuide[] }[] = [];
  for (const field of fields) {
    const name = field.group ?? "기타";
    (groups.find(g => g.name === name) ?? groups[groups.push({ name, fields: [] }) - 1]).fields.push(field);
  }
  return <Context.Provider value={{ errors, readOnly, locked: locked ?? new Set() }}>
    <div className="space-y-8">{groups.map(group => <section key={group.name} aria-labelledby={domId(`group-${group.name}`)} className="space-y-4">
      <h3 id={domId(`group-${group.name}`)} className="border-b border-line pb-1.5 text-ui font-semibold text-ink">{group.name}</h3>
      <Fields fields={group.fields} value={value} onChange={onChange} path="" />
    </section>)}</div>
  </Context.Provider>;
}
