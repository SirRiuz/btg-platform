import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";

import { fonts, semantic } from "../theme/tokens";
import { formatCOP } from "../utils/format";

type Size = "sm" | "md" | "lg" | "xl";

interface MoneyDisplayProps {
  amount: number;
  size?: Size;
  emphasis?: boolean;
  animate?: boolean;
  "aria-label"?: string;
}

const SIZE_STYLES: Record<Size, { fontSize: number; fontWeight: number; letterSpacing?: string }> = {
  sm: { fontSize: 13, fontWeight: 500 },
  md: { fontSize: 16, fontWeight: 500 },
  lg: { fontSize: 24, fontWeight: 600, letterSpacing: "-0.02em" },
  xl: { fontSize: 32, fontWeight: 600, letterSpacing: "-0.025em" },
};

export function MoneyDisplay({
  amount,
  size = "md",
  emphasis = true,
  animate = false,
  "aria-label": ariaLabel,
}: MoneyDisplayProps) {
  const sizeStyle = SIZE_STYLES[size];
  const color = emphasis ? semantic.textPrimary : semantic.textSecondary;
  const formatted = formatCOP(amount);

  const sharedStyle = {
    fontFamily: fonts.mono,
    fontFeatureSettings: "'tnum'",
    color,
    lineHeight: 1.15,
    ...sizeStyle,
  };

  if (!animate) {
    return (
      <Box
        component="span"
        aria-label={ariaLabel}
        sx={{ display: "inline-block", ...sharedStyle }}
      >
        {formatted}
      </Box>
    );
  }

  return (
    <Box
      component="span"
      aria-label={ariaLabel}
      aria-live="polite"
      sx={{ position: "relative", display: "inline-block", ...sharedStyle }}
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <Box
          key={amount}
          component={motion.span}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, position: "absolute" }}
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          sx={{ display: "inline-block" }}
        >
          {formatted}
        </Box>
      </AnimatePresence>
    </Box>
  );
}

export default MoneyDisplay;
