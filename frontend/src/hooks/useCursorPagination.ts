import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { DEFAULT_DATA_PAGE_SIZE } from "../components/CursorPagination";

interface CursorPageTarget {
  cursor: string | undefined;
  pageIndex: number;
  pageCursors: Array<string | undefined>;
}

type CursorPageLoader = (cursor: string | undefined) => void;

export interface CursorPaginationState {
  pageCursors: Array<string | undefined>;
  pageIndex: number;
  pageSize: number;
}

export function useCursorPagination(initialState?: CursorPaginationState, filterKey?: string) {
  const location = useLocation();
  const navigate = useNavigate();
  const saved = location.state?.dataPagination as
    (CursorPaginationState & { filterKey: string }) | undefined;
  const restored = filterKey && saved?.filterKey === filterKey ? saved : initialState;
  const activeKey = useRef(filterKey);
  const activeSize = useRef(restored?.pageSize ?? DEFAULT_DATA_PAGE_SIZE);
  const [pageCursors, setPageCursors] = useState(restored?.pageCursors ?? [undefined]);
  const [pageIndex, setPageIndex] = useState(restored?.pageIndex ?? 0);
  const [pageSize, setPageSize] = useState(restored?.pageSize ?? DEFAULT_DATA_PAGE_SIZE);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const returnState = useMemo(
    () => ({
      ...location.state,
      dataPagination: { filterKey, pageCursors, pageIndex, pageSize },
    }),
    [location.state, filterKey, pageCursors, pageIndex, pageSize],
  );
  useEffect(() => {
    if (!filterKey || activeKey.current !== filterKey || activeSize.current !== pageSize) return;
    if (JSON.stringify(saved) === JSON.stringify(returnState.dataPagination)) return;
    navigate(`${location.pathname}${location.search}${location.hash}`, {
      replace: true,
      state: returnState,
    });
  }, [filterKey, pageSize, location, navigate, returnState, saved]);

  const latestPagination = useRef({ filterKey, nextCursor, pageCursors, pageIndex, pageSize });
  latestPagination.current = { filterKey, nextCursor, pageCursors, pageIndex, pageSize };

  const resetPagination = useCallback(() => {
    setPageCursors([undefined]);
    setPageIndex(0);
    setNextCursor(null);
  }, []);

  const restorePagination = useCallback(() => {
    const current = latestPagination.current;
    const restore =
      activeKey.current === current.filterKey && activeSize.current === current.pageSize;
    activeKey.current = current.filterKey;
    activeSize.current = current.pageSize;
    if (!restore) resetPagination();
    return restore ? current.pageCursors[current.pageIndex] : undefined;
  }, [resetPagination]);

  const moveToPage = useCallback((target: CursorPageTarget) => {
    setPageIndex(target.pageIndex);
    setPageCursors(target.pageCursors);
    setNextCursor(null);
  }, []);

  const getNextPageTarget = useCallback((): CursorPageTarget | null => {
    const current = latestPagination.current;
    if (!current.nextCursor) return null;
    return {
      cursor: current.nextCursor,
      pageIndex: current.pageIndex + 1,
      pageCursors: [...current.pageCursors.slice(0, current.pageIndex + 1), current.nextCursor],
    };
  }, []);

  const getPreviousPageTarget = useCallback((): CursorPageTarget | null => {
    const current = latestPagination.current;
    if (current.pageIndex === 0) return null;
    const previousPageIndex = current.pageIndex - 1;
    return {
      cursor: current.pageCursors[previousPageIndex],
      pageIndex: previousPageIndex,
      pageCursors: current.pageCursors,
    };
  }, []);

  const loadNextPage = useCallback(
    (loadPage: CursorPageLoader) => {
      const target = getNextPageTarget();
      if (!target) return;
      moveToPage(target);
      loadPage(target.cursor);
    },
    [getNextPageTarget, moveToPage],
  );

  const loadPreviousPage = useCallback(
    (loadPage: CursorPageLoader) => {
      const target = getPreviousPageTarget();
      if (!target) return;
      moveToPage(target);
      loadPage(target.cursor);
    },
    [getPreviousPageTarget, moveToPage],
  );

  return {
    returnState,
    restorePagination,
    pageCursors,
    pageIndex,
    pageSize,
    nextCursor,
    setNextCursor,
    setPageSize,
    resetPagination,
    loadNextPage,
    loadPreviousPage,
  };
}
