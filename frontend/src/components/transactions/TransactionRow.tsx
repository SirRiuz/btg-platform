import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { useId, type KeyboardEvent } from "react";

import MoneyDisplay from "../MoneyDisplay";
import { ChevronDownIcon } from "../icons";
import { colors, fonts, radius, semantic, transition } from "../../theme/tokens";
import type { Transaction } from "../../types/transaction";
import {
  formatFullDateTime,
  formatTimeLabel,
  parseTimestamp,
} from "../../utils/dateGrouping";

interface TransactionRowProps {
  transaction: Transaction;
  isExpanded: boolean;
  onToggle: () => void;
}

const TYPE_LABEL: Record<Transaction["type"], string> = {
  OPEN: "Apertura",
  CANCEL: "Cancelación",
};

export function TransactionRow({
  transaction,
  isExpanded,
  onToggle,
}: TransactionRowProps) {
  const panelId = useId();
  const date = parseTimestamp(transaction.timestamp);
  const sign = transaction.type === "OPEN" ? "−" : "+";
  const signColor =
    transaction.type === "OPEN" ? colors.gray700 : colors.gray900;

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onToggle();
    }
  };

  return (
    <Box
      sx={{
        borderBottom: `1px solid ${semantic.borderSubtle}`,
      }}
    >
      <Box
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: "16px",
          padding: "14px 12px",
          marginInline: "-12px",
          borderRadius: `${radius.md}px`,
          cursor: "pointer",
          outline: "none",
          transition: `background-color ${transition.default}`,
          "&:hover": {
            backgroundColor: semantic.backgroundSubtle,
          },
          "&:focus-visible": {
            outline: `2px solid ${colors.gray400}`,
            outlineOffset: -2,
          },
        }}
      >
        <Box
          sx={{
            width: 56,
            flexShrink: 0,
            fontSize: 13,
            color: semantic.textSecondary,
            fontFamily: fonts.mono,
            fontFeatureSettings: "'tnum'",
          }}
        >
          {formatTimeLabel(date)}
        </Box>

        <Box
          aria-hidden
          sx={{
            width: 16,
            flexShrink: 0,
            fontSize: 16,
            fontWeight: 500,
            fontFamily: fonts.mono,
            color: signColor,
            textAlign: "center",
            lineHeight: 1,
          }}
        >
          {sign}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box
            sx={{
              fontSize: 14,
              fontWeight: 500,
              color: semantic.textPrimary,
              lineHeight: 1.4,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {transaction.fund_nombre}
          </Box>
          <Box
            sx={{
              fontSize: 12,
              color: semantic.textSecondary,
              lineHeight: 1.4,
              marginTop: "2px",
            }}
          >
            {TYPE_LABEL[transaction.type]}
          </Box>
        </Box>

        <Box sx={{ textAlign: "right", flexShrink: 0 }}>
          <MoneyDisplay
            amount={transaction.amount}
            size="md"
            aria-label={`${TYPE_LABEL[transaction.type]} de ${transaction.fund_nombre}`}
          />
        </Box>

        <Box
          aria-hidden
          sx={{
            width: 20,
            flexShrink: 0,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: colors.gray400,
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: `transform ${transition.default}`,
          }}
        >
          <ChevronDownIcon size={14} />
        </Box>
      </Box>

      <AnimatePresence initial={false}>
        {isExpanded ? (
          <Box
            id={panelId}
            component={motion.div}
            key="panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            sx={{ overflow: "hidden" }}
          >
            <Box
              sx={{
                backgroundColor: semantic.backgroundSubtle,
                borderRadius: `${radius.md}px`,
                padding: "20px",
                marginTop: "8px",
                marginBottom: "8px",
                display: "grid",
                gap: "16px",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              }}
            >
              <DetailField
                label="ID de transacción"
                value={transaction.id}
                monospace
              />
              <DetailField
                label="ID de fondo"
                value={`#${transaction.fund_id}`}
                monospace
              />
              <DetailField
                label="Saldo antes"
                value={<MoneyDisplay amount={transaction.balance_before} size="sm" />}
              />
              <DetailField
                label="Saldo después"
                value={<MoneyDisplay amount={transaction.balance_after} size="sm" />}
              />
              <DetailField
                label="Fecha completa"
                value={formatFullDateTime(date)}
              />
              <DetailField
                label="Tipo"
                value={TYPE_LABEL[transaction.type]}
              />
            </Box>
          </Box>
        ) : null}
      </AnimatePresence>
    </Box>
  );
}

interface DetailFieldProps {
  label: string;
  value: React.ReactNode;
  monospace?: boolean;
}

function DetailField({ label, value, monospace = false }: DetailFieldProps) {
  return (
    <Box>
      <Box
        sx={{
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: colors.gray400,
          lineHeight: 1.4,
        }}
      >
        {label}
      </Box>
      <Box
        sx={{
          fontSize: 13,
          color: semantic.textPrimary,
          lineHeight: 1.4,
          marginTop: "2px",
          fontFamily: monospace ? fonts.mono : "inherit",
          fontFeatureSettings: monospace ? "'tnum'" : undefined,
          wordBreak: monospace ? "break-all" : "normal",
        }}
      >
        {value}
      </Box>
    </Box>
  );
}

export default TransactionRow;
