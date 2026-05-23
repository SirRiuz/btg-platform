import { Box } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "../components/layout/AppShell";
import ErrorAlert from "../components/ErrorAlert";
import FilterTabs, {
  type TransactionFilter,
} from "../components/transactions/FilterTabs";
import LoadMoreButton from "../components/transactions/LoadMoreButton";
import StatsRow from "../components/transactions/StatsRow";
import TransactionTimeline from "../components/transactions/TransactionTimeline";
import { listMyTransactions } from "../services/transactionsService";
import { semantic } from "../theme/tokens";
import type { ApiError } from "../types/common";
import type { Transaction, TransactionType } from "../types/transaction";
import { toApiError } from "../utils/errorMessages";

const PAGE_SIZE = 20;

interface AbsoluteCounts {
  total: number;
  opens: number;
  cancels: number;
}

function filterToType(filter: TransactionFilter): TransactionType | undefined {
  return filter === "all" ? undefined : filter;
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filteredTotal, setFilteredTotal] = useState<number>(0);
  const [activeFilter, setActiveFilter] = useState<TransactionFilter>("all");
  const [isLoadingInitial, setIsLoadingInitial] = useState<boolean>(true);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<ApiError | null>(null);

  const [absoluteCounts, setAbsoluteCounts] = useState<AbsoluteCounts | null>(
    null,
  );
  const [isLoadingCounts, setIsLoadingCounts] = useState<boolean>(true);

  const requestIdRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setIsLoadingCounts(true);
    Promise.all([
      listMyTransactions({ skip: 0, limit: 1 }),
      listMyTransactions({ skip: 0, limit: 1, type: "OPEN" }),
      listMyTransactions({ skip: 0, limit: 1, type: "CANCEL" }),
    ])
      .then(([allRes, opensRes, cancelsRes]) => {
        if (cancelled) return;
        setAbsoluteCounts({
          total: allRes.data.total,
          opens: opensRes.data.total,
          cancels: cancelsRes.data.total,
        });
      })
      .catch(() => {
        if (cancelled) return;
        // Los counts son secundarios: si fallan, el StatsRow se queda en 0
        // pero la lista principal funciona igual. El error de la lista se
        // muestra desde fetchPage().
      })
      .finally(() => {
        if (!cancelled) setIsLoadingCounts(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchPage = useCallback(
    async (filter: TransactionFilter, skip: number, append: boolean) => {
      const currentRequestId = ++requestIdRef.current;
      if (append) setIsLoadingMore(true);
      else setIsLoadingInitial(true);
      setLoadError(null);
      try {
        const response = await listMyTransactions({
          skip,
          limit: PAGE_SIZE,
          type: filterToType(filter),
        });
        if (requestIdRef.current !== currentRequestId) return;
        setFilteredTotal(response.data.total);
        setTransactions((prev) =>
          append ? [...prev, ...response.data.items] : response.data.items,
        );
      } catch (err) {
        if (requestIdRef.current !== currentRequestId) return;
        setLoadError(toApiError(err));
      } finally {
        if (requestIdRef.current !== currentRequestId) return;
        if (append) setIsLoadingMore(false);
        else setIsLoadingInitial(false);
      }
    },
    [],
  );

  useEffect(() => {
    setTransactions([]);
    setFilteredTotal(0);
    fetchPage(activeFilter, 0, false);
  }, [activeFilter, fetchPage]);

  const handleFilterChange = (next: TransactionFilter) => {
    if (next === activeFilter) return;
    setActiveFilter(next);
  };

  const handleLoadMore = () => {
    if (isLoadingMore) return;
    fetchPage(activeFilter, transactions.length, true);
  };

  const hasMore = transactions.length < filteredTotal;

  const counts: AbsoluteCounts = absoluteCounts ?? {
    total: 0,
    opens: 0,
    cancels: 0,
  };

  const visibleSubtitle = (() => {
    if (isLoadingInitial || transactions.length === 0) return null;
    const filteredCategoryTotal =
      activeFilter === "all"
        ? counts.total
        : activeFilter === "OPEN"
          ? counts.opens
          : counts.cancels;
    const noun =
      activeFilter === "all"
        ? transactions.length === 1
          ? "movimiento"
          : "movimientos"
        : activeFilter === "OPEN"
          ? transactions.length === 1
            ? "apertura"
            : "aperturas"
          : transactions.length === 1
            ? "cancelación"
            : "cancelaciones";
    return `Mostrando ${transactions.length} de ${filteredCategoryTotal} ${noun}`;
  })();

  return (
    <AppShell>
      <Box component="section" sx={{ marginBottom: "32px" }}>
        <Box
          component="h1"
          sx={{
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: semantic.textPrimary,
            margin: 0,
            lineHeight: 1.25,
          }}
        >
          Historial de transacciones
        </Box>
        <Box
          sx={{
            marginTop: "4px",
            fontSize: 14,
            color: semantic.textSecondary,
            lineHeight: 1.5,
          }}
        >
          Todos tus movimientos en orden cronológico.
        </Box>
      </Box>

      <Box sx={{ marginBottom: "32px" }}>
        <StatsRow
          total={counts.total}
          opens={counts.opens}
          cancels={counts.cancels}
          isLoading={isLoadingCounts}
        />
      </Box>

      <Box sx={{ marginBottom: "8px" }}>
        <FilterTabs
          activeFilter={activeFilter}
          onChange={handleFilterChange}
          counts={counts}
        />
      </Box>

      {visibleSubtitle ? (
        <Box
          sx={{
            fontSize: 13,
            color: semantic.textSecondary,
            marginTop: "8px",
            marginBottom: "24px",
          }}
        >
          {visibleSubtitle}
        </Box>
      ) : (
        <Box sx={{ marginBottom: "24px" }} />
      )}

      {loadError ? (
        <Box sx={{ marginBottom: "16px" }}>
          <ErrorAlert error={loadError} />
        </Box>
      ) : null}

      <Box sx={{ marginBottom: "16px" }}>
        <TransactionTimeline
          transactions={transactions}
          isLoading={isLoadingInitial}
        />
      </Box>

      {transactions.length > 0 ? (
        <LoadMoreButton
          onClick={handleLoadMore}
          isLoading={isLoadingMore}
          hasMore={hasMore}
        />
      ) : null}
    </AppShell>
  );
}
