import { Button, Select } from "antd";

const DATA_PAGE_SIZE_OPTIONS = [20, 50, 100] as const;
export const DEFAULT_DATA_PAGE_SIZE = 20;

type CursorPageLoader = (cursor: string | undefined) => void;

interface CursorPaginationController {
  pageIndex: number;
  pageSize: number;
  nextCursor: string | null;
  setPageSize: (pageSize: number) => void;
  loadNextPage: (loadPage: CursorPageLoader) => void;
  loadPreviousPage: (loadPage: CursorPageLoader) => void;
}

interface CursorPaginationProps {
  controller: CursorPaginationController;
  itemCount: number;
  loading: boolean;
  loadPage: CursorPageLoader;
}

export function CursorPagination({
  controller,
  itemCount,
  loading,
  loadPage,
}: CursorPaginationProps) {
  const hasPrevious = controller.pageIndex > 0;
  const hasNext = Boolean(controller.nextCursor);
  if (loading || (itemCount === 0 && !hasPrevious && !hasNext)) return null;

  return (
    <nav className="cursor-pagination" aria-label="列表分页">
      <div className="cursor-pagination__controls">
        <span>
          第 {controller.pageIndex + 1} 页 · 本页 {itemCount} 条
        </span>
        <label htmlFor="cursor-page-size">
          每页
          <Select
            aria-label="每页条数"
            id="cursor-page-size"
            options={DATA_PAGE_SIZE_OPTIONS.map((option) => ({
              label: `${option} 条`,
              value: option,
            }))}
            value={controller.pageSize}
            onChange={controller.setPageSize}
          />
        </label>
        <Button disabled={!hasPrevious} onClick={() => controller.loadPreviousPage(loadPage)}>
          上一页
        </Button>
        <Button disabled={!hasNext} onClick={() => controller.loadNextPage(loadPage)}>
          下一页
        </Button>
      </div>
    </nav>
  );
}
