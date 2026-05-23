import { Box } from "@mui/material";
import { forwardRef, type KeyboardEvent } from "react";

import { colors, semantic, transition } from "../theme/tokens";
import Spinner from "./Spinner";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  loading?: boolean;
  id?: string;
  ariaLabel?: string;
  ariaLabelledBy?: string;
}

const CONTAINER_WIDTH = 36;
const CONTAINER_HEIGHT = 20;
const KNOB_SIZE = 14;
const KNOB_INSET = 2;
const KNOB_TRANSLATE = CONTAINER_WIDTH - KNOB_SIZE - KNOB_INSET * 2;

export const Toggle = forwardRef<HTMLButtonElement, ToggleProps>(
  function Toggle(
    {
      checked,
      onChange,
      disabled = false,
      loading = false,
      id,
      ariaLabel,
      ariaLabelledBy,
    },
    ref,
  ) {
    const interactive = !disabled && !loading;

    const handleClick = () => {
      if (!interactive) return;
      onChange(!checked);
    };

    const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
      if (!interactive) return;
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        onChange(!checked);
      }
    };

    return (
      <Box
        component="button"
        ref={ref}
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-disabled={disabled || loading || undefined}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        tabIndex={disabled ? -1 : 0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        sx={{
          all: "unset",
          boxSizing: "border-box",
          position: "relative",
          display: "inline-block",
          width: CONTAINER_WIDTH,
          height: CONTAINER_HEIGHT,
          borderRadius: `${CONTAINER_HEIGHT / 2}px`,
          backgroundColor: checked
            ? semantic.textPrimary
            : semantic.borderDefault,
          border: `1px solid ${
            checked ? semantic.textPrimary : semantic.borderDefault
          }`,
          cursor: interactive ? "pointer" : "not-allowed",
          opacity: disabled ? 0.5 : 1,
          transition: `background-color ${transition.default}, border-color ${transition.default}`,
          flexShrink: 0,
          "&:focus-visible": {
            outline: `2px solid ${colors.gray400}`,
            outlineOffset: 2,
          },
        }}
      >
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            top: "50%",
            left: KNOB_INSET,
            width: KNOB_SIZE,
            height: KNOB_SIZE,
            marginTop: -(KNOB_SIZE / 2) + "px",
            backgroundColor: colors.white,
            borderRadius: "50%",
            boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
            transform: checked
              ? `translateX(${KNOB_TRANSLATE}px)`
              : "translateX(0)",
            transition: `transform ${transition.default}`,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {loading ? (
            <Spinner
              size={10}
              thickness={1.25}
              color={checked ? semantic.textPrimary : colors.gray500}
              aria-label="Guardando"
            />
          ) : null}
        </Box>
      </Box>
    );
  },
);

export default Toggle;
