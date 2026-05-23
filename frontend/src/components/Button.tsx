import { Box } from "@mui/material";
import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";

import { colors, radius, semantic, transition } from "../theme/tokens";
import Spinner from "./Spinner";

type Variant = "primary" | "secondary";

interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  variant?: Variant;
  fullWidth?: boolean;
  loading?: boolean;
  children: ReactNode;
}

const PRIMARY_STYLES = {
  base: {
    backgroundColor: semantic.ctaBg,
    color: semantic.ctaText,
    border: `1px solid ${semantic.ctaBg}`,
  },
  hover: {
    backgroundColor: semantic.ctaBgHover,
    borderColor: semantic.ctaBgHover,
  },
  disabled: {
    backgroundColor: semantic.ctaDisabledBg,
    borderColor: semantic.ctaDisabledBg,
    color: semantic.ctaDisabledText,
  },
} as const;

const SECONDARY_STYLES = {
  base: {
    backgroundColor: colors.white,
    color: semantic.textPrimary,
    border: `1px solid ${semantic.borderDefault}`,
  },
  hover: {
    backgroundColor: semantic.backgroundSubtle,
    borderColor: semantic.textPrimary,
  },
  disabled: {
    backgroundColor: colors.white,
    borderColor: semantic.borderDefault,
    color: semantic.textTertiary,
  },
} as const;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      fullWidth = false,
      loading = false,
      disabled,
      children,
      type = "button",
      style,
      ...rest
    },
    ref,
  ) {
    const isDisabled = disabled || loading;
    const styles =
      variant === "primary" ? PRIMARY_STYLES : SECONDARY_STYLES;

    const spinnerColor =
      variant === "primary" ? colors.white : semantic.textPrimary;

    return (
      <Box
        component="button"
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        sx={{
          all: "unset",
          boxSizing: "border-box",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 1,
          minHeight: 40,
          padding: "10px 16px",
          width: fullWidth ? "100%" : "auto",
          fontFamily: "inherit",
          fontSize: 14,
          fontWeight: 500,
          lineHeight: 1.2,
          borderRadius: `${radius.md}px`,
          cursor: isDisabled ? "not-allowed" : "pointer",
          userSelect: "none",
          transition: `background-color ${transition.default}, border-color ${transition.default}, color ${transition.default}`,
          ...styles.base,
          "&:hover:not(:disabled)": styles.hover,
          "&:focus-visible": {
            outline: `2px solid ${colors.gray400}`,
            outlineOffset: 2,
          },
          "&:disabled": styles.disabled,
        }}
        style={style}
        {...rest}
      >
        {loading ? <Spinner size={16} color={spinnerColor} /> : children}
      </Box>
    );
  },
);

export default Button;
