import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import type { ReactNode } from "react";

import { semantic } from "../theme/tokens";
import type { ApiError } from "../types/common";
import { getUserFriendlyMessage } from "../utils/errorMessages";
import { AlertIcon } from "./icons";

interface ErrorAlertProps {
  error: ApiError | null;
  children?: ReactNode;
}

export function ErrorAlert({ error, children }: ErrorAlertProps) {
  return (
    <AnimatePresence initial={false}>
      {error ? (
        <Box
          key="error"
          component={motion.div}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
          role="alert"
          sx={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            padding: "12px 16px",
            backgroundColor: semantic.errorBg,
            borderLeft: `2px solid ${semantic.errorBorder}`,
            borderRadius: "0 6px 6px 0",
            color: semantic.errorText,
            fontSize: 13,
            lineHeight: 1.4,
          }}
        >
          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              flexShrink: 0,
              marginTop: "1px",
            }}
          >
            <AlertIcon />
          </Box>
          <Box>
            {children ?? getUserFriendlyMessage(error)}
          </Box>
        </Box>
      ) : null}
    </AnimatePresence>
  );
}

export default ErrorAlert;
