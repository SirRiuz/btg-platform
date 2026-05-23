import { Box } from "@mui/material";
import {
  forwardRef,
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";

import { colors, radius, semantic, transition } from "../theme/tokens";
import { EyeIcon, EyeOffIcon } from "./icons";

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label: string;
  helperText?: ReactNode;
  error?: boolean;
  errorMessage?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    helperText,
    error = false,
    errorMessage,
    id,
    type = "text",
    disabled,
    ...rest
  },
  ref,
) {
  const reactId = useId();
  const inputId = id ?? `input-${reactId}`;
  const helperId = `${inputId}-helper`;
  const [revealPassword, setRevealPassword] = useState(false);
  const isPassword = type === "password";
  const effectiveType = isPassword
    ? revealPassword
      ? "text"
      : "password"
    : type;

  const helperContent = error && errorMessage ? errorMessage : helperText;
  const helperColor = error ? semantic.errorText : semantic.textSecondary;

  const baseBorderColor = error
    ? semantic.errorBorder
    : semantic.borderDefault;
  const hoverBorderColor = error
    ? semantic.errorBorder
    : semantic.borderStrong;
  const focusBorderColor = error
    ? semantic.errorBorder
    : semantic.borderFocus;
  const focusRing = error
    ? "0 0 0 3px rgba(229, 72, 77, 0.1)"
    : "0 0 0 3px rgba(0, 0, 0, 0.06)";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      <Box
        component="label"
        htmlFor={inputId}
        sx={{
          fontSize: 13,
          fontWeight: 500,
          color: semantic.textPrimary,
          lineHeight: 1.4,
        }}
      >
        {label}
      </Box>
      <Box sx={{ position: "relative" }}>
        <Box
          component="input"
          ref={ref}
          id={inputId}
          type={effectiveType}
          disabled={disabled}
          aria-invalid={error || undefined}
          aria-describedby={helperContent ? helperId : undefined}
          {...rest}
          sx={{
            all: "unset",
            boxSizing: "border-box",
            width: "100%",
            padding: isPassword ? "10px 40px 10px 12px" : "10px 12px",
            fontFamily: "inherit",
            fontSize: 14,
            lineHeight: 1.4,
            color: semantic.textPrimary,
            backgroundColor: disabled
              ? semantic.backgroundSubtle
              : colors.white,
            borderRadius: `${radius.md}px`,
            border: `1px solid ${baseBorderColor}`,
            transition: `border-color ${transition.default}, box-shadow ${transition.default}, background-color ${transition.default}`,
            "&::placeholder": {
              color: semantic.textPlaceholder,
            },
            "&:hover:not(:disabled):not(:focus)": {
              borderColor: hoverBorderColor,
            },
            "&:focus": {
              borderColor: focusBorderColor,
              boxShadow: focusRing,
            },
            "&:disabled": {
              color: semantic.textTertiary,
              cursor: "not-allowed",
            },
          }}
        />
        {isPassword ? (
          <Box
            component="button"
            type="button"
            aria-label={
              revealPassword ? "Ocultar contraseña" : "Mostrar contraseña"
            }
            aria-pressed={revealPassword}
            tabIndex={0}
            onClick={() => setRevealPassword((prev) => !prev)}
            sx={{
              all: "unset",
              position: "absolute",
              top: "50%",
              right: 12,
              transform: "translateY(-50%)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 20,
              height: 20,
              color: semantic.textTertiary,
              cursor: "pointer",
              transition: `color ${transition.default}`,
              "&:hover": { color: semantic.textPrimary },
              "&:focus-visible": {
                outline: `2px solid ${colors.gray400}`,
                outlineOffset: 2,
                borderRadius: 2,
              },
            }}
          >
            {revealPassword ? <EyeOffIcon /> : <EyeIcon />}
          </Box>
        ) : null}
      </Box>
      {helperContent ? (
        <Box
          id={helperId}
          sx={{
            fontSize: 12,
            lineHeight: 1.4,
            color: helperColor,
          }}
        >
          {helperContent}
        </Box>
      ) : null}
    </Box>
  );
});

export default Input;
