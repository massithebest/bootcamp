import { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  columnFilteringFeature,
  globalFilteringFeature,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type ColumnDef,
  type PaginationState,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowDownIcon,
  ArrowUpDownIcon,
  ArrowUpIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SearchIcon,
} from "lucide-react";

import { useQueryTable } from "@/hooks/use-query-result";
import { displayCell } from "@/lib/format-cell";
import type { QueryTablePage } from "@/types/query-result";
import { ResultNotice, RetryButton } from "./message";

export interface QueryTableProps {
  resultId: string;
  columns?: string[];
  title?: string;
}

type DataRow = { cells: QueryTablePage["rows"][number] };
type LastPage = {
  requestBaseKey: string;
  value: QueryTablePage;
};

const PAGE_SIZES = [10, 25, 50, 100] as const;
const DEFAULT_PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 250;
const TABLE_FEATURES = tableFeatures({
  columnFilteringFeature,
  globalFilteringFeature,
  rowSortingFeature,
  rowPaginationFeature,
});

/** TanStack의 수동 모드로 저장 결과 전체에 서버 검색·정렬·pagination을 적용하는 표. */
export function QueryTable({ resultId, columns, title }: QueryTableProps) {
  const pageSizeId = useId();
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  });
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const lastPage = useRef<LastPage | null>(null);
  const columnKey = columns?.join("\u0000") ?? "";

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedSearch(globalFilter.trim()),
      SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [globalFilter]);

  useEffect(() => {
    setPagination({ pageIndex: 0, pageSize: DEFAULT_PAGE_SIZE });
    setSorting([]);
    setGlobalFilter("");
    setDebouncedSearch("");
  }, [resultId, columnKey]);

  const sort = sorting[0];
  const request = useMemo(
    () => ({
      resultId,
      page: pagination.pageIndex + 1,
      pageSize: pagination.pageSize,
      columns,
      search: debouncedSearch || undefined,
      sortColumn: sort?.id,
      sortDirection: sort ? (sort.desc ? "desc" as const : "asc" as const) : undefined,
    }),
    // columns 배열 identity 대신 내용으로 비교한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      resultId,
      pagination.pageIndex,
      pagination.pageSize,
      columnKey,
      debouncedSearch,
      sort?.id,
      sort?.desc,
    ],
  );
  const state = useQueryTable(request, retryKey);
  const requestBaseKey = JSON.stringify([
    resultId,
    pagination.pageSize,
    columnKey,
    debouncedSearch,
    sort?.id ?? "",
    sort?.desc ?? false,
  ]);
  useEffect(() => {
    if (state.type === "success") {
      lastPage.current = { requestBaseKey, value: state.value };
    }
  }, [request.page, requestBaseKey, state]);
  const retainedPage = lastPage.current?.requestBaseKey === requestBaseKey
    ? lastPage.current.value
    : null;
  const current = state.type === "success"
    ? state.value
    : state.type === "loading"
      ? state.stale ?? retainedPage
      : retainedPage;
  const loading = state.type === "loading";

  const data = useMemo<DataRow[]>(
    () => current?.rows.map((cells) => ({ cells })) ?? [],
    [current?.rows],
  );
  const tableColumns = useMemo<ColumnDef<typeof TABLE_FEATURES, DataRow>[]>(
    () => current?.columns.map((column, columnIndex) => ({
      id: column.name,
      accessorFn: (row) => row.cells[columnIndex] ?? null,
      header: column.name,
      cell: ({ getValue }) => displayCell(
        getValue() as QueryTablePage["rows"][number][number],
      ),
      sortDescFirst: false,
      enableGlobalFilter: true,
    })) ?? [],
    [current?.columns],
  );
  const dataTable = useTable({
    features: TABLE_FEATURES,
    columns: tableColumns,
    data,
    state: { pagination, sorting, globalFilter },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    manualFiltering: true,
    manualSorting: true,
    manualPagination: true,
    rowCount: current?.filtered_row_count ?? 0,
    autoResetPageIndex: false,
    enableMultiSort: false,
  });

  if (!current) {
    if (state.type === "loading") {
      return <ResultNotice loading className="animate-pulse motion-reduce:animate-none">표를 불러오는 중…</ResultNotice>;
    }
    if (state.type === "success") return null;
    return <TableFailure state={state} onRetry={() => setRetryKey((v) => v + 1)} />;
  }

  const pageCount = Math.max(1, dataTable.getPageCount());
  const requestedPage = Math.min(pagination.pageIndex + 1, pageCount);
  const first = current.rows.length ? (current.page - 1) * current.page_size + 1 : 0;
  const last = first ? first + current.rows.length - 1 : 0;
  const visibleRows = dataTable.getRowModel().rows;
  const hasSearch = debouncedSearch.length > 0;

  return (
    <section
      className="flex min-w-0 flex-col gap-3 rounded border border-line bg-surface p-3"
      data-slot="query-table"
      data-table-engine="tanstack"
      aria-label={title ?? "조회 결과 표"}
      aria-busy={loading || undefined}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-medium text-ink">{title ?? "조회 결과 표"}</h3>
          <p className="mt-0.5 text-2xs text-ink-2">
            전체 {current.row_count.toLocaleString("ko-KR")}건
            {hasSearch && ` · 검색 결과 ${current.filtered_row_count.toLocaleString("ko-KR")}건`}
            {" · "}
            {first ? `${first.toLocaleString("ko-KR")}–${last.toLocaleString("ko-KR")}행` : "표시할 행 없음"}
            {loading && (current.page !== requestedPage
              ? ` · ${requestedPage}페이지 불러오는 중…`
              : " · 불러오는 중…")}
            {state.type !== "loading" && state.type !== "success" && current.page !== requestedPage
              ? ` · ${requestedPage}페이지를 불러오지 못해 ${current.page}페이지를 유지 중`
              : ""}
          </p>
        </div>
        <label className="relative min-w-52 flex-1 sm:max-w-72">
          <span className="sr-only">표 내용 검색</span>
          <SearchIcon
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-3"
          />
          <input
            type="search"
            value={globalFilter}
            maxLength={200}
            onChange={(event) => {
              dataTable.setGlobalFilter(event.target.value);
              dataTable.setPageIndex(0);
            }}
            placeholder="표 내용 검색"
            className="h-8 w-full rounded border border-line-strong bg-canvas pl-8 pr-2.5 text-ui text-ink outline-none placeholder:text-ink-3 focus:border-accent focus:ring-1 focus:ring-accent-weak"
          />
        </label>
      </div>

      <div className="thin-scroll max-h-[32rem] overflow-auto rounded border border-line">
        <table className="w-full min-w-max border-collapse font-mono text-data tabular-nums">
          <thead className="sticky top-0 z-10 bg-surface-2">
            {dataTable.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-line-strong text-left text-ink-2">
                {headerGroup.headers.map((header) => {
                  const direction = header.column.getIsSorted();
                  const SortIcon = direction === "asc"
                    ? ArrowUpIcon
                    : direction === "desc"
                      ? ArrowDownIcon
                      : ArrowUpDownIcon;
                  const columnName = String(header.column.columnDef.header ?? header.column.id);
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      aria-sort={direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none"}
                      className="whitespace-nowrap p-0 font-medium"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          if (direction === false) header.column.toggleSorting(false);
                          else if (direction === "asc") header.column.toggleSorting(true);
                          else header.column.clearSorting();
                          dataTable.setPageIndex(0);
                        }}
                        className="flex w-full items-center gap-1 px-2 py-2 text-left hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
                        aria-label={`${columnName} 열 정렬${direction === "asc" ? ", 오름차순" : direction === "desc" ? ", 내림차순" : ""}`}
                        aria-pressed={direction !== false}
                      >
                        <span>{header.isPlaceholder ? null : <dataTable.FlexRender header={header} />}</span>
                        <SortIcon aria-hidden className="size-3" />
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className={loading ? "opacity-60" : undefined}>
            {visibleRows.map((row) => (
              <tr key={row.id} className="border-b border-line last:border-0">
                {row.getAllCells().map((cell, columnIndex) => (
                  <td
                    key={cell.id}
                    className={`whitespace-nowrap px-2 py-1.5 ${columnIndex === 0 ? "text-ink-2" : "text-ink"}`}
                  >
                    <dataTable.FlexRender cell={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {visibleRows.length === 0 && (
          <p className="px-3 py-8 text-center text-ui text-ink-2">
            {hasSearch ? "검색 조건에 맞는 행이 없습니다." : "조회 결과 0건입니다. 조건에 맞는 데이터가 없습니다."}
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-2xs text-ink-2">
        <div className="flex items-center gap-2">
          <label htmlFor={pageSizeId}>페이지당 행</label>
          <select
            id={pageSizeId}
            value={pagination.pageSize}
            onChange={(event) => setPagination({
              pageIndex: 0,
              pageSize: Number(event.target.value),
            })}
            className="h-7 rounded border border-line-strong bg-canvas px-2 text-ui text-ink outline-none focus:border-accent focus:ring-1 focus:ring-accent-weak"
          >
            {PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => {
              if (!loading && dataTable.getCanPreviousPage()) dataTable.previousPage();
            }}
            aria-disabled={!dataTable.getCanPreviousPage() || loading}
            className="inline-flex size-7 items-center justify-center rounded border border-line-strong text-ink-2 hover:bg-surface-2 aria-disabled:cursor-not-allowed aria-disabled:opacity-40"
            aria-label="이전 페이지"
          >
            <ChevronLeftIcon aria-hidden className="size-3.5" />
          </button>
          <span className="min-w-20 text-center" aria-live="polite">{requestedPage} / {pageCount} 페이지</span>
          <button
            type="button"
            onClick={() => {
              if (!loading && dataTable.getCanNextPage()) dataTable.nextPage();
            }}
            aria-disabled={!dataTable.getCanNextPage() || loading}
            className="inline-flex size-7 items-center justify-center rounded border border-line-strong text-ink-2 hover:bg-surface-2 aria-disabled:cursor-not-allowed aria-disabled:opacity-40"
            aria-label="다음 페이지"
          >
            <ChevronRightIcon aria-hidden className="size-3.5" />
          </button>
        </div>
      </div>

      {state.type !== "loading" && state.type !== "success" && (
        <TableFailure state={state} onRetry={() => setRetryKey((v) => v + 1)} inline />
      )}
      {current.source_truncated && (
        <p className="text-2xs text-warn-ink">
          조회 결과가 저장 상한에서 잘렸으며, 저장된 범위 {current.row_count.toLocaleString("ko-KR")}건만 검색·정렬·조회할 수 있습니다.
        </p>
      )}
    </section>
  );
}

function TableFailure({
  state,
  onRetry,
  inline = false,
}: {
  state: { type: "not-found" | "invalid-request" | "invalid-response" | "error"; message: string };
  onRetry: () => void;
  inline?: boolean;
}) {
  const retryable = state.type === "error" || state.type === "invalid-response";
  const body = (
    <>
      <span>
        {state.type === "invalid-request" ? `이 표 설정을 적용할 수 없습니다. ${state.message}` : state.message}
      </span>
      {retryable && <RetryButton onClick={onRetry} />}
    </>
  );
  return inline
    ? <div role="alert" className="flex items-center gap-2 text-ui text-block-ink">{body}</div>
    : <ResultNotice tone="alert">{body}</ResultNotice>;
}
