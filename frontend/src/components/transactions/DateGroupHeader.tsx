import { Box } from "@mui/material";

import { colors, semantic } from "../../theme/tokens";

interface DateGroupHeaderProps {
  label: string;
  isFirst?: boolean;
}

export function DateGroupHeader({
  label,
  isFirst = false,
}: DateGroupHeaderProps) {
  return (
    <Box
      sx={{
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: colors.gray400,
        padding: isFirst ? "0 0 12px 0" : "32px 0 12px 0",
        borderTop: isFirst ? "none" : `1px solid ${semantic.borderSubtle}`,
      }}
    >
      {label}
    </Box>
  );
}

export default DateGroupHeader;
