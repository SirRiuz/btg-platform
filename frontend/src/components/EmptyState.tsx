import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { radius, semantic } from "../theme/tokens";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Box
      role="status"
      sx={{
        padding: "48px 24px",
        textAlign: "center",
        background: "transparent",
        border: `1px dashed ${semantic.borderDefault}`,
        borderRadius: `${radius.md}px`,
      }}
    >
      <Box
        sx={{
          fontSize: 14,
          fontWeight: 500,
          color: semantic.textPrimary,
          lineHeight: 1.4,
        }}
      >
        {title}
      </Box>
      {description ? (
        <Box
          sx={{
            fontSize: 13,
            color: semantic.textSecondary,
            marginTop: "4px",
            lineHeight: 1.5,
          }}
        >
          {description}
        </Box>
      ) : null}
      {action ? (
        <Box
          sx={{
            marginTop: "16px",
            display: "inline-flex",
            justifyContent: "center",
          }}
        >
          {action}
        </Box>
      ) : null}
    </Box>
  );
}

export default EmptyState;
