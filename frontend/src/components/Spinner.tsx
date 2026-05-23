import { Box } from "@mui/material";
import { keyframes } from "@mui/system";

const rotate = keyframes`
  to { transform: rotate(360deg); }
`;

interface SpinnerProps {
  size?: number;
  color?: string;
  thickness?: number;
  "aria-label"?: string;
}

export function Spinner({
  size = 16,
  color = "currentColor",
  thickness = 1.75,
  "aria-label": ariaLabel = "Cargando",
}: SpinnerProps) {
  const inner = `calc(50% - ${thickness}px)`;
  return (
    <Box
      role="status"
      aria-label={ariaLabel}
      sx={{
        display: "inline-block",
        width: size,
        height: size,
        position: "relative",
        animation: `${rotate} 700ms linear infinite`,
        color,
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          border: `${thickness}px solid currentColor`,
          opacity: 0.2,
        }}
      />
      <Box
        sx={{
          position: "absolute",
          top: 0,
          left: inner,
          width: thickness * 2,
          height: thickness * 2,
          backgroundColor: "currentColor",
          borderRadius: "50%",
        }}
      />
    </Box>
  );
}

export default Spinner;
