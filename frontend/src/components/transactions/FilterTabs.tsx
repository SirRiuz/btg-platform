import { Box } from "@mui/material";

import { colors, semantic, transition } from "../../theme/tokens";

export type TransactionFilter = "all" | "OPEN" | "CANCEL";

interface FilterCounts {
  total: number;
  opens: number;
  cancels: number;
}

interface FilterTabsProps {
  activeFilter: TransactionFilter;
  onChange: (filter: TransactionFilter) => void;
  counts: FilterCounts;
}

interface TabSpec {
  value: TransactionFilter;
  label: string;
  count: number;
}

export function FilterTabs({
  activeFilter,
  onChange,
  counts,
}: FilterTabsProps) {
  const tabs: TabSpec[] = [
    { value: "all", label: "Todas", count: counts.total },
    { value: "OPEN", label: "Aperturas", count: counts.opens },
    { value: "CANCEL", label: "Cancelaciones", count: counts.cancels },
  ];

  return (
    <Box
      role="tablist"
      aria-label="Filtrar transacciones"
      sx={{
        display: "flex",
        gap: "24px",
        borderBottom: `1px solid ${semantic.borderDefault}`,
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab.value === activeFilter;
        return (
          <Box
            key={tab.value}
            component="button"
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.value)}
            sx={{
              all: "unset",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "14px 0",
              fontSize: 14,
              fontWeight: 500,
              color: isActive
                ? semantic.textPrimary
                : semantic.textSecondary,
              borderBottom: `2px solid ${
                isActive ? semantic.textPrimary : "transparent"
              }`,
              marginBottom: "-1px",
              cursor: "pointer",
              transition: `color ${transition.default}, border-color ${transition.default}`,
              "&:hover": { color: semantic.textPrimary },
              "&:focus-visible": {
                outline: `2px solid ${colors.gray400}`,
                outlineOffset: 4,
              },
            }}
          >
            {tab.label}
            <Box
              component="span"
              sx={{
                fontSize: 12,
                color: colors.gray400,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {tab.count}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

export default FilterTabs;
