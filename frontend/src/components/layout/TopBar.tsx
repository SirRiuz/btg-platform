import { Box } from "@mui/material";
import { useState } from "react";

import Button from "../Button";
import Wordmark from "../Wordmark";
import { useAuth } from "../../hooks/useAuth";
import { semantic } from "../../theme/tokens";

export function TopBar() {
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <Box
      sx={{
        backgroundColor: semantic.background,
        borderBottom: `1px solid ${semantic.borderDefault}`,
        padding: { xs: "16px 24px", sm: "20px 40px" },
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      <Wordmark fixed={false} />
      <Box sx={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {user ? (
          <Box
            sx={{
              fontSize: 13,
              color: semantic.textSecondary,
              display: { xs: "none", sm: "inline" },
            }}
          >
            Hola, {user.nombre}
          </Box>
        ) : null}
        <Button
          variant="secondary"
          onClick={handleLogout}
          loading={loggingOut}
        >
          Cerrar sesión
        </Button>
      </Box>
    </Box>
  );
}

export default TopBar;
