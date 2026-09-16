import { useId, useMemo } from "react";
import {
  columnFilteringFeature,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  globalFilteringFeature,
  rowPaginationFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type ColumnDef,
  type FilterFn,
  type SortFn,
} from "@tanstack/react-table";
import {
  ArrowDownIcon,
  ArrowUpDownIcon,
  ArrowUpIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SearchIcon,
} from "lucide-react";

import type { StandaloneTablePayload, TableCell } from "@/lib/table-tool";

type DataRow = { cells: TableCell[] };

const PAGE_SIZES = [10, 25, 50, 100] as const;
const TABLE_FEATURES = tableFeatures({
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  rowPaginationFeature,
  paginatedRowModel: createPaginatedRowModel(),
});

function displayCell(value: TableCell | undefined): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function compareCells(left: TableCell | undefined, right: TableCell | undefined): number {
  if (left == null) return right == null ? 0 : 1;
  if (right == null) return -1;
  if (typeof left === "number" && typeof right === "number") return left - right;
  return displayCell(left).localeCompare(displayCell(right), "ko-KR", {
    numeric: true,
    sensitivity: "base",
  });
}

const tableCellSort: SortFn<typeof TABLE_FEATURES, DataRow> = (
  left,
  right,
  columnId,
) => compareCells(left.getValue<TableCell>(columnId), right.getValue<TableCell>(columnId));

const tableCellFilter: FilterFn<typeof TABLE_FEATURES, DataRow> = (
  row,
  columnId,
  filterValue,
) => displayCell(row.getValue<TableCell>(columnId))
  .toLocaleLowerCase("ko-KR")
  .includes(String(filterValue).trim().toLocaleLowerCase("ko-KR"));

tableCellFilter.autoRemove = (value) => String(value ?? "").trim().length === 0;

export function InteractiveDataTable({ table: payload }: { table: StandaloneTablePayload }) {
  const pageSizeId = useId();
  const data = useMemo<DataRow[]>(
    () => payload.rows.map((cells) => ({ cells })),
    [payload.rows],
  );
  const columns = useMemo<ColumnDef<typeof TABLE_FEATURES, DataRow>[]>(
    () => payload.columns.map((name, columnIndex) => ({
      id: `${columnIndex}:${name}`,
      accessorFn: (row) => row.cells[columnIndex] ?? null,
      header: name,
      cell: ({ getValue }) => displayCell(getValue() as TableCell),
      sortFn: tableCellSort,
      sortDescFirst: false,
      enableGlobalFilter: true,
    })),
    [payload.columns],
  );
  const dataTable = useTable({
    features: TABLE_FEATURES,
    columns,
    data,
    globalFilterFn: tableCellFilter,
    initialState: {
      globalFilter: "",
      pagination: { pageIndex: 0, pageSize: 10 },
    },
    autoResetPageIndex: true,
    enableMultiSort: false,
  });

  const { globalFilter, pagination } = dataTable.state;
  const filteredCount = dataTable.getFilteredRowModel().rows.length;
  const pageCount = Math.max(1, dataTable.getPageCount());
  const currentPage = Math.min(pagination.pageIndex, pageCount - 1);
  const visibleRows = dataTable.getRowModel().rows;

  return (
    <section
      className="flex min-w-0 flex-col gap-3 rounded border border-line bg-surface p-3"
      data-table-engine="tanstack"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-medium text-ink">{payload.title ?? "조회 결과 표"}</h3>
          <p className="mt-0.5 text-2xs text-ink-2">
            원본 {payload.rowCount.toLocaleString("ko-KR")}건 · 표에 {payload.displayedCount.toLocaleString("ko-KR")}건 포함
          </p>
        </div>
        <label className="relative min-w-52 flex-1 sm:max-w-72">
          <span className="sr-only">표 내용 검색</span>
          <SearchIcon aria-hidden className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-3" />
          <input
            type="search"
            value={String(globalFilter ?? "")}
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
          <tbody>
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
          <p className="px-3 py-8 text-center text-ui text-ink-2">검색 조건에 맞는 행이 없습니다.</p>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-2xs text-ink-2">
        <div className="flex items-center gap-2">
          <label htmlFor={pageSizeId}>페이지당 행</label>
          <select
            id={pageSizeId}
            value={pagination.pageSize}
            onChange={(event) => dataTable.setPageSize(Number(event.target.value))}
            className="h-7 rounded border border-line-strong bg-canvas px-2 text-ui text-ink outline-none focus:border-accent focus:ring-1 focus:ring-accent-weak"
          >
            {PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
          </select>
          <span aria-live="polite">검색 결과 {filteredCount.toLocaleString("ko-KR")}건</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => dataTable.previousPage()}
            disabled={!dataTable.getCanPreviousPage()}
            className="inline-flex size-7 items-center justify-center rounded border border-line-strong text-ink-2 hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="이전 페이지"
          >
            <ChevronLeftIcon aria-hidden className="size-3.5" />
          </button>
          <span className="min-w-20 text-center" aria-live="polite">{currentPage + 1} / {pageCount} 페이지</span>
          <button
            type="button"
            onClick={() => dataTable.nextPage()}
            disabled={!dataTable.getCanNextPage()}
            className="inline-flex size-7 items-center justify-center rounded border border-line-strong text-ink-2 hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="다음 페이지"
          >
            <ChevronRightIcon aria-hidden className="size-3.5" />
          </button>
        </div>
      </div>

      {(payload.rowCount > payload.displayedCount || payload.sourceTruncated) && (
        <p className="text-2xs text-warn-ink">
          {payload.sourceTruncated
            ? `조회 결과가 저장 상한에서 잘렸으며, 저장된 범위 중 앞 ${payload.displayedCount.toLocaleString("ko-KR")}건을 표시합니다.`
            : `전체 결과 중 앞 ${payload.displayedCount.toLocaleString("ko-KR")}건을 표시합니다.`}
        </p>
      )}
    </section>
  );
}
