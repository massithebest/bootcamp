/** 줄 단위 diff. 지식 YAML은 수백 줄 이하라 LCS로 충분하며 새 패키지를 쓰지 않는다. */
export type DiffRow = { kind: "same" | "add" | "del"; text: string; oldNo?: number; newNo?: number };
export type DiffChunk = DiffRow | { kind: "gap"; count: number };

const MAX_CELLS = 4_000_000;

export function diffLines(before: string, after: string): DiffRow[] {
  const a = before === "" ? [] : before.replace(/\n$/, "").split("\n");
  const b = after === "" ? [] : after.replace(/\n$/, "").split("\n");
  if (a.length * b.length > MAX_CELLS) {
    // 너무 큰 입력은 정밀 비교를 포기하고 전체 교체로 표시한다.
    return [
      ...a.map((text, i): DiffRow => ({ kind: "del", text, oldNo: i + 1 })),
      ...b.map((text, i): DiffRow => ({ kind: "add", text, newNo: i + 1 })),
    ];
  }
  // lcs[i][j] = a[i..], b[j..] 의 공통 부분 수열 길이
  const lcs = Array.from({ length: a.length + 1 }, () => new Uint32Array(b.length + 1));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const rows: DiffRow[] = [];
  let i = 0, j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { rows.push({ kind: "same", text: a[i], oldNo: i + 1, newNo: j + 1 }); i++; j++; }
    // 같은 위치의 교체는 이전 줄(삭제)이 이후 줄(추가) 위에 오도록 삭제를 먼저 낸다.
    else if (i < a.length && (j === b.length || lcs[i + 1][j] >= lcs[i][j + 1])) { rows.push({ kind: "del", text: a[i], oldNo: i + 1 }); i++; }
    else { rows.push({ kind: "add", text: b[j], newNo: j + 1 }); j++; }
  }
  return rows;
}

/** 변경 줄 주변 `context`줄만 남기고 나머지 변경 없는 구간은 하나의 gap 으로 접는다. */
export function collapseUnchanged(rows: DiffRow[], context = 3): DiffChunk[] {
  const keep = new Array<boolean>(rows.length).fill(false);
  rows.forEach((row, index) => {
    if (row.kind === "same") return;
    for (let k = Math.max(0, index - context); k <= Math.min(rows.length - 1, index + context); k++) keep[k] = true;
  });
  const chunks: DiffChunk[] = [];
  let hidden = 0;
  rows.forEach((row, index) => {
    if (keep[index]) {
      if (hidden) { chunks.push({ kind: "gap", count: hidden }); hidden = 0; }
      chunks.push(row);
    } else hidden++;
  });
  if (hidden) chunks.push({ kind: "gap", count: hidden });
  return chunks;
}

export const hasChanges = (rows: DiffRow[]) => rows.some(row => row.kind !== "same");
