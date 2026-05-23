import { Box } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { semantic } from "../theme/tokens";

interface WordmarkProps {
  to?: string;
  fixed?: boolean;
}

export function Wordmark({ to = "/", fixed = true }: WordmarkProps) {
  return (
    <Box
      component={RouterLink}
      to={to}
      aria-label="BTG Pactual"
      sx={{
        position: fixed ? "absolute" : "static",
        top: fixed ? 40 : undefined,
        left: fixed ? 40 : undefined,
        zIndex: 10,
        display: "inline-flex",
        alignItems: "center",
        gap: 1,
        fontSize: 14,
        fontWeight: 500,
        letterSpacing: "-0.01em",
        color: semantic.textPrimary,
        textDecoration: "none",
        "@media (max-width: 640px)": fixed
          ? { top: 24, left: 24 }
          : undefined,
      }}
    >
      <Box
        aria-hidden
        sx={{
          width: 8,
          height: 8,
          borderRadius: "2px",
          backgroundColor: semantic.textPrimary,
        }}
      />
      BTG Pactual
    </Box>
  );
}

export default Wordmark;
