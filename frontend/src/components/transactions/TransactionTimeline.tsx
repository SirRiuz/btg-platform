import { Box } from "@mui/material";
import { motion } from "framer-motion";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import EmptyState from "../EmptyState";
import { colors, radius, semantic } from "../../theme/tokens";
import type { Transaction } from "../../types/transaction";
import { groupTransactionsByDate } from "../../utils/dateGrouping";
import DateGroupHeader from "./DateGroupHeader";
import TransactionRow from "./TransactionRow";

interface TransactionTimelineProps {
  transactions: Transaction[];
  isLoading: boolean;
}

function SkeletonRow() {
  return (
    <Box
      aria-hidden
      sx={{
        display: "flex",
        alignItems: "center",
        gap: "16px",
        padding: "14px 0",
        borderBottom: `1px solid ${semantic.borderSubtle}`,
      }}
    >
      <Box sx={{ width: 40, height: 14, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
      <Box sx={{ width: 16, height: 14, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
        <Box sx={{ width: "60%", height: 14, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
        <Box sx={{ width: "30%", height: 11, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
      </Box>
      <Box sx={{ width: 100, height: 16, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
      <Box sx={{ width: 14, height: 14, backgroundColor: colors.gray100, borderRadius: `${radius.sm}px` }} />
    </Box>
  );
}

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.03 },
  },
};

const itemVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] },
  },
};

export function TransactionTimeline({
  transactions,
  isLoading,
}: TransactionTimelineProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (isLoading && transactions.length === 0) {
    return (
      <Box>
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </Box>
    );
  }

  if (!isLoading && transactions.length === 0) {
    return (
      <EmptyState
        title="Aún no has hecho movimientos."
        description="Tus aperturas y cancelaciones aparecerán aquí."
        action={
          <Box
            component={RouterLink}
            to="/"
            sx={{
              fontSize: 13,
              fontWeight: 500,
              color: semantic.textPrimary,
              textDecoration: "underline",
              textUnderlineOffset: "3px",
              textDecorationColor: colors.gray300,
              "&:hover": { textDecorationColor: semantic.textPrimary },
            }}
          >
            Ver fondos disponibles
          </Box>
        }
      />
    );
  }

  const groups = groupTransactionsByDate(transactions);

  return (
    <Box
      component={motion.div}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {groups.map((group, index) => (
        <Box key={group.dateKey}>
          <Box
            component={motion.div}
            variants={itemVariants}
          >
            <DateGroupHeader label={group.label} isFirst={index === 0} />
          </Box>
          {group.items.map((tx) => (
            <Box key={tx.id} component={motion.div} variants={itemVariants}>
              <TransactionRow
                transaction={tx}
                isExpanded={expandedIds.has(tx.id)}
                onToggle={() => toggle(tx.id)}
              />
            </Box>
          ))}
        </Box>
      ))}
    </Box>
  );
}

export default TransactionTimeline;
