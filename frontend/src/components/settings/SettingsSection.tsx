import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { semantic } from "../../theme/tokens";

interface SettingsSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  last?: boolean;
}

export function SettingsSection({
  title,
  description,
  children,
  last = false,
}: SettingsSectionProps) {
  return (
    <Box
      component="section"
      sx={{
        display: "grid",
        gap: { xs: "16px", md: "48px" },
        gridTemplateColumns: { xs: "1fr", md: "1fr 1.5fr" },
        paddingBottom: last ? 0 : "32px",
        marginBottom: last ? 0 : "32px",
        borderBottom: last ? "none" : `1px solid ${semantic.borderSubtle}`,
      }}
    >
      <Box sx={{ maxWidth: 320 }}>
        <Box
          component="h2"
          sx={{
            fontSize: 16,
            fontWeight: 600,
            color: semantic.textPrimary,
            margin: 0,
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
      </Box>
      <Box>{children}</Box>
    </Box>
  );
}

export default SettingsSection;
