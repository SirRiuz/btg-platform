import { Box } from "@mui/material";
import { useEffect, useRef, useState } from "react";

import Button from "../Button";
import Card from "../Card";
import MoneyDisplay from "../MoneyDisplay";
import { colors, radius, semantic, transition } from "../../theme/tokens";
import type { Subscription } from "../../types/subscription";
import { formatRelativeDate } from "../../utils/dateGrouping";

interface SubscriptionCardProps {
  subscription: Subscription;
  onCancel: (subscription: Subscription) => Promise<void>;
  isCancelling?: boolean;
}

const CONFIRM_WINDOW_MS = 4000;

export function SubscriptionCard({
  subscription,
  onCancel,
  isCancelling = false,
}: SubscriptionCardProps) {
  const [confirmMode, setConfirmMode] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, []);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const startConfirmCountdown = () => {
    clearTimer();
    timerRef.current = window.setTimeout(() => {
      setConfirmMode(false);
      timerRef.current = null;
    }, CONFIRM_WINDOW_MS);
  };

  const handleClick = async () => {
    if (isCancelling) return;
    if (!confirmMode) {
      setConfirmMode(true);
      startConfirmCountdown();
      return;
    }
    clearTimer();
    await onCancel(subscription);
  };

  return (
    <Card padding={20}>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "12px",
          }}
        >
          <Box
            sx={{
              fontSize: 14,
              fontWeight: 500,
              color: semantic.textPrimary,
              lineHeight: 1.4,
            }}
          >
            {subscription.fund_nombre}
          </Box>
          <MoneyDisplay amount={subscription.amount} size="md" />
        </Box>

        <Box
          sx={{
            marginTop: "4px",
            fontSize: 12,
            color: semantic.textSecondary,
            lineHeight: 1.4,
          }}
        >
          Suscrito el {formatRelativeDate(subscription.subscribed_at)}
        </Box>

        <Box
          sx={{
            marginTop: "16px",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          {confirmMode ? (
            <Box
              component="button"
              type="button"
              onClick={handleClick}
              disabled={isCancelling}
              aria-busy={isCancelling || undefined}
              sx={{
                all: "unset",
                boxSizing: "border-box",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 40,
                padding: "10px 16px",
                fontFamily: "inherit",
                fontSize: 14,
                fontWeight: 500,
                lineHeight: 1.2,
                borderRadius: `${radius.md}px`,
                cursor: isCancelling ? "not-allowed" : "pointer",
                backgroundColor: "transparent",
                color: semantic.errorBorder,
                border: `1px solid ${semantic.errorBorder}`,
                transition: `background-color ${transition.default}, color ${transition.default}, border-color ${transition.default}`,
                "&:hover:not(:disabled)": {
                  backgroundColor: semantic.errorBg,
                },
                "&:focus-visible": {
                  outline: `2px solid ${colors.gray400}`,
                  outlineOffset: 2,
                },
              }}
            >
              {isCancelling ? "Cancelando…" : "Confirmar cancelación"}
            </Box>
          ) : (
            <Button
              variant="secondary"
              onClick={handleClick}
              loading={isCancelling}
              aria-label={`Cancelar inversión en ${subscription.fund_nombre}`}
            >
              Cancelar inversión
            </Button>
          )}
        </Box>
      </Box>
    </Card>
  );
}

export default SubscriptionCard;
