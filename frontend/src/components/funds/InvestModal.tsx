import { Box } from "@mui/material";
import {
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import Badge from "../Badge";
import Button from "../Button";
import ErrorAlert from "../ErrorAlert";
import Modal from "../Modal";
import MoneyDisplay from "../MoneyDisplay";
import { colors, radius, semantic, transition } from "../../theme/tokens";
import type { ApiError } from "../../types/common";
import type { Fund } from "../../types/fund";
import type { SubscribeResponse } from "../../types/subscription";
import { subscribe } from "../../services/subscriptionsService";
import { formatCOP, parseAmountInput } from "../../utils/format";
import { toApiError } from "../../utils/errorMessages";

interface InvestModalProps {
  open: boolean;
  onClose: () => void;
  fund: Fund | null;
  userBalance: number;
  onSuccess: (response: SubscribeResponse) => void;
}

type ValidationState =
  | { kind: "untouched_empty" }
  | { kind: "valid_default" }
  | { kind: "valid"; amount: number }
  | { kind: "invalid"; message: string };

function validate(
  raw: string,
  touched: boolean,
  fund: Fund,
  balance: number,
): ValidationState {
  if (raw.length === 0) {
    return touched ? { kind: "valid_default" } : { kind: "untouched_empty" };
  }
  const parsed = parseAmountInput(raw);
  if (parsed === null) {
    return { kind: "invalid", message: "Ingresa un monto válido." };
  }
  if (parsed === 0) {
    return { kind: "invalid", message: "El monto debe ser mayor a cero." };
  }
  if (parsed < fund.monto_minimo) {
    return {
      kind: "invalid",
      message: `El monto mínimo para este fondo es ${formatCOP(fund.monto_minimo)}.`,
    };
  }
  if (parsed > balance) {
    return {
      kind: "invalid",
      message: `No tienes saldo suficiente. Tu saldo es ${formatCOP(balance)}.`,
    };
  }
  return { kind: "valid", amount: parsed };
}

export function InvestModal({
  open,
  onClose,
  fund,
  userBalance,
  onSuccess,
}: InvestModalProps) {
  const [rawInput, setRawInput] = useState("");
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (open) {
      setRawInput("");
      setTouched(false);
      setSubmitting(false);
      setServerError(null);
    }
  }, [open, fund?.id]);

  const validation: ValidationState | null = useMemo(() => {
    if (!fund) return null;
    return validate(rawInput, touched, fund, userBalance);
  }, [rawInput, touched, fund, userBalance]);

  const isError = validation?.kind === "invalid";
  const isSubmitDisabled =
    !fund || submitting || isError || (touched && validation?.kind !== "valid" && validation?.kind !== "valid_default" && validation?.kind !== "untouched_empty");

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (!touched) setTouched(true);
    const cleaned = event.target.value.replace(/[^0-9]/g, "").slice(0, 10);
    setRawInput(cleaned.replace(/^0+(?=\d)/, ""));
    if (serverError) setServerError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!fund || submitting) return;
    const result = validate(rawInput, touched, fund, userBalance);
    if (result.kind === "invalid") return;

    const amount =
      result.kind === "valid" ? result.amount : undefined;

    setSubmitting(true);
    setServerError(null);
    try {
      const response = await subscribe(fund.id, amount ? { amount } : undefined);
      onSuccess(response.data);
      onClose();
    } catch (err) {
      setServerError(toApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!fund) return null;

  const helperText = (() => {
    if (!validation) return null;
    switch (validation.kind) {
      case "untouched_empty":
      case "valid_default":
        return `Si dejas en blanco, se invertirá el mínimo de ${formatCOP(fund.monto_minimo)}.`;
      case "valid":
        return `Restará ${formatCOP(validation.amount)} de tu saldo. Saldo después: ${formatCOP(userBalance - validation.amount)}.`;
      case "invalid":
        return validation.message;
    }
  })();

  return (
    <Modal
      open={open}
      onClose={submitting ? () => undefined : onClose}
      title={`Invertir en ${fund.nombre}`}
      maxWidth={480}
      disableClose={submitting}
    >
      <Box
        component="form"
        onSubmit={handleSubmit}
        noValidate
        sx={{ display: "flex", flexDirection: "column", gap: "24px" }}
      >
        <Box sx={{ display: "inline-flex", gap: "6px", flexWrap: "wrap" }}>
          <Badge>{fund.categoria}</Badge>
          {fund.perfil_riesgo ? (
            <Badge variant="subtle">Riesgo {fund.perfil_riesgo}</Badge>
          ) : null}
        </Box>

        <Box>
          <SummaryRow label="Saldo disponible" value={<MoneyDisplay amount={userBalance} size="sm" />} />
          <SummaryRow
            label="Monto mínimo"
            value={<MoneyDisplay amount={fund.monto_minimo} size="sm" />}
          />
          <SummaryRow label="Categoría" value={fund.categoria} last />
        </Box>

        <Box>
          <Box
            component="label"
            htmlFor="invest-amount"
            sx={{
              display: "block",
              fontSize: 13,
              fontWeight: 500,
              color: semantic.textPrimary,
              marginBottom: "6px",
            }}
          >
            Monto a invertir{" "}
            <Box component="span" sx={{ color: semantic.textTertiary, fontWeight: 400 }}>
              (opcional)
            </Box>
          </Box>
          <Box
            component="input"
            id="invest-amount"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder={String(fund.monto_minimo)}
            value={rawInput}
            onChange={handleInputChange}
            disabled={submitting}
            aria-invalid={isError || undefined}
            aria-describedby="invest-amount-helper"
            sx={{
              all: "unset",
              boxSizing: "border-box",
              width: "100%",
              padding: "10px 12px",
              fontFamily: "inherit",
              fontSize: 14,
              lineHeight: 1.4,
              color: semantic.textPrimary,
              backgroundColor: submitting
                ? semantic.backgroundSubtle
                : colors.white,
              borderRadius: `${radius.md}px`,
              border: `1px solid ${
                isError ? semantic.errorBorder : semantic.borderDefault
              }`,
              transition: `border-color ${transition.default}, box-shadow ${transition.default}`,
              "&::placeholder": {
                color: semantic.textPlaceholder,
              },
              "&:hover:not(:disabled):not(:focus)": {
                borderColor: isError
                  ? semantic.errorBorder
                  : semantic.borderStrong,
              },
              "&:focus": {
                borderColor: isError
                  ? semantic.errorBorder
                  : semantic.borderFocus,
                boxShadow: isError
                  ? "0 0 0 3px rgba(229, 72, 77, 0.1)"
                  : "0 0 0 3px rgba(0,0,0,0.06)",
              },
            }}
          />
          {helperText ? (
            <Box
              id="invest-amount-helper"
              sx={{
                fontSize: 12,
                marginTop: "6px",
                lineHeight: 1.4,
                color: isError ? semantic.errorText : semantic.textSecondary,
              }}
            >
              {helperText}
            </Box>
          ) : null}
        </Box>

        <ErrorAlert error={serverError} />

        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column-reverse", sm: "row" },
            justifyContent: { sm: "flex-end" },
            gap: "12px",
            marginTop: "8px",
            "& > button": {
              width: { xs: "100%", sm: "auto" },
            },
          }}
        >
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitDisabled}
            loading={submitting}
          >
            Confirmar inversión
          </Button>
        </Box>
      </Box>
    </Modal>
  );
}

interface SummaryRowProps {
  label: string;
  value: React.ReactNode;
  last?: boolean;
}

function SummaryRow({ label, value, last = false }: SummaryRowProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", sm: "row" },
        alignItems: { xs: "flex-start", sm: "center" },
        justifyContent: "space-between",
        gap: { xs: "4px", sm: 0 },
        padding: "12px 0",
        borderBottom: last ? "none" : `1px solid ${semantic.borderSubtle}`,
        fontSize: 13,
      }}
    >
      <Box
        sx={{
          color: semantic.textSecondary,
          fontSize: { xs: 12, sm: 13 },
        }}
      >
        {label}
      </Box>
      <Box
        sx={{
          color: semantic.textPrimary,
          fontWeight: 500,
          textAlign: { xs: "left", sm: "right" },
        }}
      >
        {value}
      </Box>
    </Box>
  );
}

export default InvestModal;
