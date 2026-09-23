import { useEffect, useRef, useState } from "react";
import { changeDocument, fetchDocument, saveDocument } from "@/lib/knowledge-api";
import type { DocumentFields, KnowledgeDocument, KnowledgeTarget } from "@/types/knowledge";

export type DocumentForm = Omit<DocumentFields, "tags"> & { tagsText: string };

const EMPTY_FORM: DocumentForm = {
  title: "",
  content: "",
  category: "업무 지식",
  tagsText: "",
  owner: "",
  source: "",
};

export const DOCUMENT_ACTION_LABELS: Record<string, string> = {
  save: "초안 저장",
  review: "검토 완료",
  activate: "활성화",
  deactivate: "비활성화",
  archive: "보관",
};

function formFrom(fields: DocumentFields): DocumentForm {
  return {
    title: fields.title,
    content: fields.content,
    category: fields.category,
    tagsText: fields.tags.join(", "),
    owner: fields.owner,
    source: fields.source,
  };
}

interface Options {
  selection: KnowledgeTarget | "new" | null;
  reload: number;
  setSelection: (selection: KnowledgeTarget) => void;
}

/** Owns text document loading, editing, saving, and review actions. */
export function useDocumentEditor({ selection, reload, setSelection }: Options) {
  const [doc, setDoc] = useState<KnowledgeDocument>();
  const [form, setForm] = useState<DocumentForm>(EMPTY_FORM);
  const [baseline, setBaseline] = useState<DocumentForm>(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [actor, setActor] = useState("");
  const [note, setNote] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(undefined);
    setDoc(undefined);
    setForm(EMPTY_FORM);
    setBaseline(EMPTY_FORM);
    setActor("");
    setNote("");
    if (!selection || selection === "new" || selection.kind !== "document") {
      setLoading(false);
      return () => controller.abort();
    }

    setLoading(true);
    fetchDocument(selection.id, controller.signal)
      .then((value) => {
        const selected = selection.version === undefined
          ? value.versions[0]
          : value.versions.find((version) => version.version === selection.version);
        if (!selected) throw new Error("인용한 버전을 찾을 수 없습니다.");
        if (controller.signal.aborted) return;
        setDoc(value);
        const next = formFrom(selected);
        setForm(next);
        setBaseline(next);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [selection, reload]);

  const creating = selection === "new";
  const selectedVersion = doc && selection && !creating
    ? selection.version === undefined
      ? doc.versions[0]
      : doc.versions.find((version) => version.version === selection.version)
    : undefined;
  const historical = !!(selection && !creating && selection.version !== undefined);
  const editable = !historical && !doc?.archived && (
    creating || (!!selection && !creating && selection.kind === "document" && !!doc)
  );
  const dirty = JSON.stringify(form) !== JSON.stringify(baseline);

  async function save(): Promise<boolean> {
    if (!formRef.current?.reportValidity()) return false;
    setBusy(true);
    setError(undefined);
    try {
      const { tagsText, ...fields } = form;
      const result = await saveDocument(
        {
          ...fields,
          tags: [...new Set(tagsText.split(",").map((tag) => tag.trim()).filter(Boolean))],
        },
        doc?.id,
        doc?.revision,
      );
      setDoc(result);
      const next = formFrom(result.versions[0]);
      setForm(next);
      setBaseline(next);
      if (creating) setSelection({ kind: "document", id: result.id });
      setNotice("초안을 저장했습니다. 검토 후 활성화하면 모든 대화의 검색에 반영됩니다.");
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "저장하지 못했습니다.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function act(action: "review" | "activate" | "deactivate" | "archive") {
    if (!doc || !selectedVersion || !actor.trim() || (action === "review" && !note.trim())) {
      setError("기록할 작업자와 검토 시 검토 근거를 입력하세요.");
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const result = await changeDocument(
        doc.id,
        action,
        doc.revision,
        actor,
        selectedVersion.version,
        note,
      );
      setDoc(result);
      setNotice(`${DOCUMENT_ACTION_LABELS[action]}했습니다.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "변경하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  function discard() {
    setForm(baseline);
  }

  return {
    doc,
    form,
    setForm,
    formRef,
    loading,
    error,
    setError,
    notice,
    setNotice,
    busy,
    actor,
    setActor,
    note,
    setNote,
    dirty,
    selectedVersion,
    historical,
    editable,
    save,
    act,
    discard,
  };
}
