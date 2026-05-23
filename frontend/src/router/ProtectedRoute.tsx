import { Box } from "@mui/material";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import Spinner from "../components/Spinner";
import { useAuth } from "../hooks/useAuth";
import { semantic } from "../theme/tokens";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

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

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
