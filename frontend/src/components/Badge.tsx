import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { colors, radius, semantic } from "../theme/tokens";

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "subtle";
}

export function Badge({ children, variant = "default" }: BadgeProps) {
  const isSubtle = variant === "subtle";
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.02em",
        lineHeight: 1.4,
        borderRadius: `${radius.sm}px`,
        backgroundColor: isSubtle ? "transparent" : colors.gray100,
        color: isSubtle ? semantic.textSecondary : colors.gray700,
        border: isSubtle ? `1px solid ${semantic.borderDefault}` : "none",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </Box>
  );
}

export default Badge;
