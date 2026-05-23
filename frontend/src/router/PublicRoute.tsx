import { Box } from "@mui/material";
import { Navigate, Outlet } from "react-router-dom";

import Spinner from "../components/Spinner";
import { useAuth } from "../hooks/useAuth";
import { semantic } from "../theme/tokens";

export function PublicRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: semantic.textTertiary,
        }}
      >
        <Spinner size={20} />
      </Box>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export default PublicRoute;
