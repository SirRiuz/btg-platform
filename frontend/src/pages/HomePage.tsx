import { Box } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";

import EmptyState from "../components/EmptyState";
import ErrorAlert from "../components/ErrorAlert";
import FundCard from "../components/funds/FundCard";
import InvestModal from "../components/funds/InvestModal";
import SubscriptionCard from "../components/funds/SubscriptionCard";
import AppShell from "../components/layout/AppShell";
import MoneyDisplay from "../components/MoneyDisplay";
import SectionHeader from "../components/SectionHeader";
import Spinner from "../components/Spinner";
import { useAuth } from "../hooks/useAuth";
import { listFunds } from "../services/fundsService";
import {
  cancelSubscription,
  listMySubscriptions,
} from "../services/subscriptionsService";
import { semantic } from "../theme/tokens";
import type { ApiError } from "../types/common";
import type { Fund } from "../types/fund";
import type {
  SubscribeResponse,
  Subscription,
} from "../types/subscription";
import { toApiError } from "../utils/errorMessages";

export default function HomePage() {
  const { user, updateBalance } = useAuth();

  const [funds, setFunds] = useState<Fund[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [totalInvested, setTotalInvested] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<ApiError | null>(null);

  const [investModalOpen, setInvestModalOpen] = useState(false);
  const [selectedFund, setSelectedFund] = useState<Fund | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<ApiError | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);

    Promise.all([listFunds(), listMySubscriptions()])
      .then(([fundsRes, subsRes]) => {
        if (cancelled) return;
        setFunds(fundsRes.data.items.filter((f) => f.activo));
        setSubscriptions(subsRes.data.items);
        setTotalInvested(subsRes.data.total_invested);
        if (typeof subsRes.data.current_balance === "number") {
          updateBalance(subsRes.data.current_balance);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(toApiError(err));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [updateBalance]);

  const subscribedFundIds = useMemo(
    () => new Set(subscriptions.map((s) => s.fund_id)),
    [subscriptions],
  );

  const handleOpenInvest = useCallback((fund: Fund) => {
    setSelectedFund(fund);
    setActionError(null);
    setInvestModalOpen(true);
  }, []);

  const handleCloseInvest = useCallback(() => {
    setInvestModalOpen(false);
  }, []);

  const handleInvestSuccess = useCallback(
    (response: SubscribeResponse) => {
      setSubscriptions((prev) => [response.subscription, ...prev]);
      setTotalInvested((prev) => prev + response.subscription.amount);
      updateBalance(response.new_balance);
      setActionError(null);
    },
    [updateBalance],
  );

  const handleCancel = useCallback(
    async (subscription: Subscription) => {
      setCancellingId(subscription.id);
      setActionError(null);
      try {
        const response = await cancelSubscription(subscription.id);
        setSubscriptions((prev) =>
          prev.filter((s) => s.id !== subscription.id),
        );
        setTotalInvested((prev) =>
          Math.max(0, prev - response.data.amount_returned),
        );
        updateBalance(response.data.new_balance);
      } catch (err) {
        setActionError(toApiError(err));
      } finally {
        setCancellingId(null);
      }
    },
    [updateBalance],
  );

  const balance = user?.balance ?? 0;
  const patrimonio = balance + totalInvested;

  return (
    <AppShell>
      <Box
        component={motion.section}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      >
        <Box
          sx={{
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: semantic.textSecondary,
            lineHeight: 1.4,
          }}
        >
          Saldo disponible
        </Box>
        <Box sx={{ marginTop: "4px" }}>
          <MoneyDisplay
            amount={balance}
            size="xl"
            animate
            aria-label="Saldo disponible"
          />
        </Box>
        <Box
          sx={{
            marginTop: "12px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "16px",
            fontSize: 13,
            color: semantic.textSecondary,
          }}
        >
          <Box sx={{ display: "inline-flex", alignItems: "baseline", gap: "6px" }}>
            <span>Total invertido</span>
            <MoneyDisplay amount={totalInvested} size="sm" emphasis={false} />
          </Box>
          {totalInvested > 0 ? (
            <Box
              sx={{
                display: "inline-flex",
                alignItems: "baseline",
                gap: "6px",
                color: semantic.textTertiary,
              }}
            >
              <span>Patrimonio total</span>
              <MoneyDisplay amount={patrimonio} size="sm" emphasis={false} />
            </Box>
          ) : null}
        </Box>
      </Box>

      {loadError ? (
        <Box sx={{ marginTop: "32px" }}>
          <ErrorAlert error={loadError} />
        </Box>
      ) : null}
      {actionError ? (
        <Box sx={{ marginTop: "16px" }}>
          <ErrorAlert error={actionError} />
        </Box>
      ) : null}

      {isLoading ? (
        <Box
          sx={{
            marginTop: "64px",
            display: "flex",
            justifyContent: "center",
            color: semantic.textTertiary,
          }}
        >
          <Spinner size={20} />
        </Box>
      ) : (
        <>
          <Box component="section" sx={{ marginTop: "64px" }}>
            <SectionHeader
              title="Mis inversiones"
              count={subscriptions.length}
              countLabel={
                subscriptions.length === 1 ? "inversión" : "inversiones"
              }
            />
            <Box sx={{ marginTop: "16px" }}>
              {subscriptions.length === 0 ? (
                <EmptyState
                  title="Aún no tienes inversiones"
                  description="Explora los fondos disponibles abajo para empezar a invertir."
                />
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: "16px",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "repeat(2, 1fr)",
                      md: "repeat(3, 1fr)",
                    },
                  }}
                >
                  <AnimatePresence initial={false}>
                    {subscriptions.map((sub) => (
                      <Box
                        key={sub.id}
                        component={motion.div}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{
                          duration: 0.2,
                          ease: [0.4, 0, 0.2, 1],
                        }}
                      >
                        <SubscriptionCard
                          subscription={sub}
                          onCancel={handleCancel}
                          isCancelling={cancellingId === sub.id}
                        />
                      </Box>
                    ))}
                  </AnimatePresence>
                </Box>
              )}
            </Box>
          </Box>

          <Box component="section" sx={{ marginTop: "64px" }}>
            <SectionHeader
              title="Fondos disponibles"
              count={funds.length}
              countLabel={funds.length === 1 ? "fondo" : "fondos"}
            />
            <Box sx={{ marginTop: "16px" }}>
              {funds.length === 0 ? (
                <EmptyState
                  title="No hay fondos disponibles"
                  description="Vuelve más tarde para ver nuevas oportunidades de inversión."
                />
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: "16px",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "repeat(2, 1fr)",
                      md: "repeat(3, 1fr)",
                    },
                  }}
                >
                  {funds.map((fund) => {
                    const isSubscribed = subscribedFundIds.has(fund.id);
                    const disabled =
                      !isSubscribed && fund.monto_minimo > balance;
                    return (
                      <FundCard
                        key={fund.id}
                        fund={fund}
                        isSubscribed={isSubscribed}
                        disabled={disabled}
                        onInvest={handleOpenInvest}
                      />
                    );
                  })}
                </Box>
              )}
            </Box>
          </Box>
        </>
      )}

      <InvestModal
        open={investModalOpen}
        onClose={handleCloseInvest}
        fund={selectedFund}
        userBalance={balance}
        onSuccess={handleInvestSuccess}
      />
    </AppShell>
  );
}
