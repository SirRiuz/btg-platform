import { Box } from "@mui/material";
import {
  forwardRef,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { colors, radius, semantic, transition } from "../theme/tokens";

interface CardProps {
  children: ReactNode;
  padding?: number | string;
  interactive?: boolean;
  onClick?: (event: MouseEvent<HTMLDivElement>) => void;
  ariaLabel?: string;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { children, padding = 20, interactive = false, onClick, ariaLabel },
  ref,
) {
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!interactive || !onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick(event as unknown as MouseEvent<HTMLDivElement>);
    }
  };

  return (
    <Box
      ref={ref}
      onClick={interactive ? onClick : undefined}
      onKeyDown={interactive ? handleKeyDown : undefined}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={interactive ? ariaLabel : undefined}
      sx={{
        backgroundColor: colors.white,
        border: `1px solid ${semantic.borderDefault}`,
        borderRadius: `${radius.md}px`,
        padding: typeof padding === "number" ? `${padding}px` : padding,
        transition: `border-color ${transition.default}`,
        cursor: interactive ? "pointer" : "default",
        outline: "none",
        "&:hover": interactive
          ? { borderColor: semantic.borderStrong }
          : undefined,
        "&:focus-visible": interactive
          ? {
              borderColor: semantic.textPrimary,
              boxShadow: "0 0 0 3px rgba(0,0,0,0.06)",
            }
          : undefined,
      }}
    >
      {children}
    </Box>
  );
});

export default Card;
