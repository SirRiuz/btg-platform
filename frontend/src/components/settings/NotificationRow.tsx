import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { useId } from "react";

import Spinner from "../Spinner";
import Toggle from "../Toggle";
import { fonts, semantic, transition } from "../../theme/tokens";

export type SaveState = "idle" | "saving" | "success" | "error";

interface NotificationRowProps {
  label: string;
  secondaryText?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  saveState: SaveState;
  errorMessage?: string | null;
  isLast?: boolean;
}

export function NotificationRow({
  label,
  secondaryText,
  checked,
  onChange,
  saveState,
  errorMessage,
  isLast = false,
}: NotificationRowProps) {
  const labelId = useId();
  const isSaving = saveState === "saving";

  return (
    <Box
      sx={{
        padding: "12px 0",
        borderBottom: isLast ? "none" : `1px solid ${semantic.borderSubtle}`,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Box
            id={labelId}
            sx={{
              fontSize: 14,
              fontWeight: 500,
              color: semantic.textPrimary,
              lineHeight: 1.4,
            }}
          >
            {label}
          </Box>
          {secondaryText ? (
            <Box
              sx={{
                fontSize: 13,
                color: semantic.textSecondary,
                marginTop: "2px",
                fontFamily: fonts.mono,
                fontFeatureSettings: "'tnum'",
                wordBreak: "break-all",
              }}
            >
              {secondaryText}
            </Box>
          ) : null}
        </Box>

        <Box
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            flexShrink: 0,
          }}
        >
          <Box
            sx={{
              minWidth: 60,
              fontSize: 12,
              lineHeight: 1.4,
              textAlign: "right",
              color:
                saveState === "error"
                  ? semantic.errorText
                  : semantic.textSecondary,
              transition: `color ${transition.default}`,
            }}
          >
            <AnimatePresence mode="wait" initial={false}>
              {saveState === "saving" ? (
                <Box
                  key="saving"
                  component={motion.span}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "flex-end",
                    gap: "6px",
                  }}
                >
                  <Spinner size={12} />
                </Box>
              ) : saveState === "success" ? (
                <Box
                  key="success"
                  component={motion.span}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  Guardado
                </Box>
              ) : saveState === "error" ? (
                <Box
                  key="error"
                  component={motion.span}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  Error
                </Box>
              ) : null}
            </AnimatePresence>
          </Box>

          <Toggle
            checked={checked}
            onChange={onChange}
            loading={isSaving}
            ariaLabelledBy={labelId}
          />
        </Box>
      </Box>

      {saveState === "error" && errorMessage ? (
        <Box
          component={motion.div}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
          role="alert"
          sx={{
            marginTop: "8px",
            fontSize: 12,
            color: semantic.errorText,
            lineHeight: 1.4,
          }}
        >
          {errorMessage}
        </Box>
      ) : null}
    </Box>
  );
}

export default NotificationRow;
