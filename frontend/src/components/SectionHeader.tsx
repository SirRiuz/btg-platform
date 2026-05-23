import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { semantic } from "../theme/tokens";
import Badge from "./Badge";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  count?: number;
  countLabel?: string;
  action?: ReactNode;
}

export function SectionHeader({
  title,
  subtitle,
  count,
  countLabel,
  action,
}: SectionHeaderProps) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "baseline",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <Box
          component="h2"
          sx={{
            fontSize: 18,
            fontWeight: 600,
            color: semantic.textPrimary,
            letterSpacing: "-0.01em",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          {title}
        </Box>
        {typeof count === "number" ? (
          <Badge variant="subtle">
            {count} {countLabel ?? (count === 1 ? "ítem" : "ítems")}
          </Badge>
        ) : null}
        {subtitle ? (
          <Box
            sx={{
              fontSize: 13,
              color: semantic.textSecondary,
              marginLeft: "8px",
              lineHeight: 1.4,
            }}
          >
            {subtitle}
          </Box>
        ) : null}
      </Box>
      {action ? <Box sx={{ flexShrink: 0 }}>{action}</Box> : null}
    </Box>
  );
}

export default SectionHeader;
