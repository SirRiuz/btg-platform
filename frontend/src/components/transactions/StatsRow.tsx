import { Box } from "@mui/material";

import Card from "../Card";
import { colors, fonts, radius, semantic } from "../../theme/tokens";

interface StatsRowProps {
  total: number;
  opens: number;
  cancels: number;
  isLoading: boolean;
}

interface StatCardProps {
  label: string;
  value: number;
  isLoading: boolean;
}

function StatCard({ label, value, isLoading }: StatCardProps) {
  return (
    <Card padding={20}>
      <Box
        sx={{
          fontSize: 12,
          fontWeight: 500,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: semantic.textSecondary,
          lineHeight: 1.4,
        }}
      >
        {label}
      </Box>
      <Box sx={{ marginTop: "8px" }}>
        {isLoading ? (
          <Box
            aria-label="Cargando"
            sx={{
              width: 60,
              height: 28,
              backgroundColor: colors.gray100,
              borderRadius: `${radius.sm}px`,
            }}
          />
        ) : (
          <Box
            component="span"
            sx={{
              fontFamily: fonts.mono,
              fontSize: 24,
              fontWeight: 600,
              color: semantic.textPrimary,
              fontFeatureSettings: "'tnum'",
              lineHeight: 1.15,
              letterSpacing: "-0.01em",
            }}
          >
            {value}
          </Box>
        )}
      </Box>
    </Card>
  );
}

export function StatsRow({ total, opens, cancels, isLoading }: StatsRowProps) {
  return (
    <Box
      sx={{
        display: "grid",
        gap: "16px",
        gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
      }}
    >
      <StatCard label="Movimientos" value={total} isLoading={isLoading} />
      <StatCard label="Aperturas" value={opens} isLoading={isLoading} />
      <StatCard label="Cancelaciones" value={cancels} isLoading={isLoading} />
    </Box>
  );
}

export default StatsRow;
