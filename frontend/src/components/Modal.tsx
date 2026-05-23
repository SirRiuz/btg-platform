import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { colors, radius, semantic, transition } from "../theme/tokens";
import { CloseIcon } from "./icons";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidth?: number;
  disableClose?: boolean;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = 440,
  disableClose = false,
}: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusFirst = () => {
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusable.length > 0) focusable[0].focus();
      else dialog.focus();
    };
    const raf = requestAnimationFrame(focusFirst);

    return () => {
      cancelAnimationFrame(raf);
      document.body.style.overflow = originalOverflow;
      previousFocusRef.current?.focus();
    };
  }, [open]);

  const handleOverlayClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (disableClose) return;
      if (event.target === event.currentTarget) onClose();
    },
    [disableClose, onClose],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "Escape" && !disableClose) {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter((el) => !el.hasAttribute("aria-hidden"));
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (event.shiftKey) {
        if (active === first || !dialog.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else {
        if (active === last) {
          event.preventDefault();
          first.focus();
        }
      }
    },
    [disableClose, onClose],
  );

  return createPortal(
    <AnimatePresence>
      {open ? (
        <Box
          component={motion.div}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
          onClick={handleOverlayClick}
          sx={{
            position: "fixed",
            inset: 0,
            zIndex: 1300,
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: { xs: "16px", sm: "24px" },
          }}
        >
          <Box
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            onKeyDown={handleKeyDown}
            component={motion.div}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            sx={{
              position: "relative",
              backgroundColor: colors.white,
              borderRadius: `${radius.md}px`,
              boxShadow:
                "0 4px 12px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.04)",
              width: "100%",
              maxWidth,
              maxHeight: {
                xs: "calc(100vh - 32px)",
                sm: "calc(100vh - 64px)",
              },
              overflowY: "auto",
              overflowX: "hidden",
              padding: { xs: "24px 20px", sm: "32px" },
              outline: "none",
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
              }}
            >
              <Box
                id={titleId}
                component="h2"
                sx={{
                  fontSize: { xs: 20, sm: 24 },
                  lineHeight: 1.25,
                  fontWeight: 600,
                  letterSpacing: "-0.02em",
                  color: semantic.textPrimary,
                  margin: 0,
                  wordBreak: "break-word",
                  overflowWrap: "anywhere",
                  minWidth: 0,
                }}
              >
                {title}
              </Box>
              {!disableClose ? (
                <Box
                  component="button"
                  type="button"
                  onClick={onClose}
                  aria-label="Cerrar"
                  sx={{
                    all: "unset",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 28,
                    height: 28,
                    marginRight: "-4px",
                    marginTop: "-4px",
                    color: semantic.textTertiary,
                    borderRadius: `${radius.sm}px`,
                    cursor: "pointer",
                    transition: `background-color ${transition.default}, color ${transition.default}`,
                    "&:hover": {
                      backgroundColor: semantic.backgroundSubtle,
                      color: semantic.textPrimary,
                    },
                    "&:focus-visible": {
                      outline: `2px solid ${colors.gray400}`,
                      outlineOffset: 2,
                    },
                  }}
                >
                  <CloseIcon size={16} />
                </Box>
              ) : null}
            </Box>
            <Box sx={{ paddingTop: "16px" }}>{children}</Box>
          </Box>
        </Box>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}

export default Modal;
