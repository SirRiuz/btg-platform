import { Box } from "@mui/material";
import { Link as RouterLink, useLocation } from "react-router-dom";

import { colors, semantic, transition } from "../../theme/tokens";

interface NavTab {
  to: string;
  label: string;
  matchExact?: boolean;
}

const TABS: NavTab[] = [
  { to: "/", label: "Inicio", matchExact: true },
  { to: "/transactions", label: "Historial" },
  { to: "/settings", label: "Ajustes" },
];

function isTabActive(tab: NavTab, pathname: string): boolean {
  if (tab.matchExact) return pathname === tab.to;
  return pathname === tab.to || pathname.startsWith(`${tab.to}/`);
}

export function NavBar() {
  const { pathname } = useLocation();

  return (
    <Box
      component="nav"
      aria-label="Navegación principal"
      sx={{
        backgroundColor: semantic.background,
        borderBottom: `1px solid ${semantic.borderDefault}`,
        padding: { xs: "0 24px", sm: "0 40px" },
        display: "flex",
        alignItems: "center",
        gap: "24px",
      }}
    >
      {TABS.map((tab) => {
        const isActive = isTabActive(tab, pathname);
        return (
          <Box
            key={tab.to}
            component={RouterLink}
            to={tab.to}
            aria-current={isActive ? "page" : undefined}
            sx={{
              display: "inline-flex",
              alignItems: "center",
              padding: "14px 0",
              fontSize: 14,
              fontWeight: 500,
              color: isActive
                ? semantic.textPrimary
                : semantic.textSecondary,
              borderBottom: `2px solid ${
                isActive ? semantic.textPrimary : "transparent"
              }`,
              marginBottom: "-1px",
              transition: `color ${transition.default}, border-color ${transition.default}`,
              textDecoration: "none",
              outline: "none",
              "&:hover": {
                color: semantic.textPrimary,
              },
              "&:focus-visible": {
                outline: `2px solid ${colors.gray400}`,
                outlineOffset: 4,
              },
            }}
          >
            {tab.label}
          </Box>
        );
      })}
    </Box>
  );
}

export default NavBar;
