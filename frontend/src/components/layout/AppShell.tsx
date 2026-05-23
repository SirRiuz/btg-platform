import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { semantic } from "../../theme/tokens";
import NavBar from "./NavBar";
import TopBar from "./TopBar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <Box sx={{ minHeight: "100vh", backgroundColor: semantic.background }}>
      <Box
        component="header"
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          backgroundColor: semantic.background,
        }}
      >
        <TopBar />
        <NavBar />
      </Box>
      <Box
        component="main"
        sx={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: { xs: "40px 24px 96px", sm: "40px 40px 96px" },
        }}
      >
        {children}
      </Box>
    </Box>
  );
}

export default AppShell;
