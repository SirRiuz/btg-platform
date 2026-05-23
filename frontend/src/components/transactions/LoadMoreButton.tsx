import { Box } from "@mui/material";

import Button from "../Button";
import { semantic } from "../../theme/tokens";

interface LoadMoreButtonProps {
  onClick: () => void;
  isLoading: boolean;
  hasMore: boolean;
  hideWhenEmpty?: boolean;
}

export function LoadMoreButton({
  onClick,
  isLoading,
  hasMore,
  hideWhenEmpty = false,
}: LoadMoreButtonProps) {
  if (!hasMore) {
    if (hideWhenEmpty) return null;
    return (
      <Box
        sx={{
          marginTop: "32px",
          textAlign: "center",
          fontSize: 13,
          color: semantic.textSecondary,
        }}
      >
        No hay más transacciones.
      </Box>
    );
  }

  return (
    <Box sx={{ marginTop: "32px" }}>
      <Button
        variant="secondary"
        fullWidth
        onClick={onClick}
        loading={isLoading}
      >
        Cargar más
      </Button>
    </Box>
  );
}

export default LoadMoreButton;
