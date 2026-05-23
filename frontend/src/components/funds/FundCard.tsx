import { Box } from "@mui/material";

import Badge from "../Badge";
import Button from "../Button";
import Card from "../Card";
import { CheckIcon } from "../icons";
import MoneyDisplay from "../MoneyDisplay";
import { semantic } from "../../theme/tokens";
import type { Fund } from "../../types/fund";

interface FundCardProps {
  fund: Fund;
  isSubscribed: boolean;
  disabled?: boolean;
  onInvest: (fund: Fund) => void;
}

export function FundCard({
  fund,
  isSubscribed,
  disabled = false,
  onInvest,
}: FundCardProps) {
  return (
    <Card padding={20}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          gap: 0,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
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
            {fund.nombre}
          </Box>
          <Badge>{fund.categoria}</Badge>
        </Box>

        {fund.descripcion ? (
          <Box
            sx={{
              marginTop: "4px",
              fontSize: 13,
              color: semantic.textSecondary,
              lineHeight: 1.5,
              display: "-webkit-box",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: 2,
              overflow: "hidden",
            }}
          >
            {fund.descripcion}
          </Box>
        ) : null}

        <Box
          sx={{
            marginTop: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          <Box>
            <Box
              sx={{
                fontSize: 12,
                color: semantic.textSecondary,
                lineHeight: 1.2,
                marginBottom: "2px",
              }}
            >
              Mínimo
            </Box>
            <MoneyDisplay amount={fund.monto_minimo} size="sm" />
          </Box>
          {fund.perfil_riesgo ? (
            <Badge variant="subtle">{fund.perfil_riesgo}</Badge>
          ) : null}
        </Box>

        <Box
          sx={{
            marginTop: "16px",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          {isSubscribed ? (
            <Box
              sx={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontSize: 13,
                fontWeight: 500,
                color: semantic.textSecondary,
              }}
            >
              <CheckIcon size={14} />
              Ya invertido
            </Box>
          ) : disabled ? (
            <Button variant="secondary" disabled>
              Saldo insuficiente
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={() => onInvest(fund)}
              aria-label={`Invertir en ${fund.nombre}`}
            >
              Invertir
            </Button>
          )}
        </Box>
      </Box>
    </Card>
  );
}

export default FundCard;
