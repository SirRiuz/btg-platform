import { createTheme, type Theme } from "@mui/material/styles";

import {
  colors,
  fontFeatures,
  fonts,
  radius,
  semantic,
  typography,
} from "./tokens";

export const theme: Theme = createTheme({
  palette: {
    mode: "light",
    common: { white: colors.white, black: colors.black },
    primary: {
      main: colors.black,
      contrastText: colors.white,
      dark: colors.gray800,
      light: colors.gray700,
    },
    secondary: {
      main: colors.gray900,
      contrastText: colors.white,
    },
    background: {
      default: semantic.background,
      paper: semantic.background,
    },
    text: {
      primary: semantic.textPrimary,
      secondary: semantic.textSecondary,
      disabled: semantic.textTertiary,
    },
    divider: semantic.borderDefault,
    grey: {
      50: colors.gray50,
      100: colors.gray100,
      200: colors.gray200,
      300: colors.gray300,
      400: colors.gray400,
      500: colors.gray500,
      600: colors.gray600,
      700: colors.gray700,
      800: colors.gray800,
      900: colors.gray900,
    },
    error: {
      main: semantic.errorBorder,
      light: semantic.errorBg,
      contrastText: colors.white,
    },
    action: {
      hover: semantic.backgroundHover,
      selected: semantic.backgroundHover,
      disabled: semantic.textTertiary,
      disabledBackground: semantic.ctaDisabledBg,
    },
  },
  shape: { borderRadius: radius.md },
  typography: {
    fontFamily: fonts.sans,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 600,
    htmlFontSize: 16,
    fontSize: 14,
    h1: typography.display,
    h2: typography.h1,
    h3: typography.h2,
    body1: typography.body,
    body2: typography.small,
    caption: typography.caption,
    button: {
      fontSize: 14,
      fontWeight: 500,
      letterSpacing: 0,
      textTransform: "none",
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: semantic.background,
          color: semantic.textPrimary,
          fontFeatureSettings: fontFeatures,
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0, square: false },
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: semantic.background,
        },
      },
    },
    MuiButtonBase: {
      defaultProps: { disableRipple: true, disableTouchRipple: true },
    },
    MuiLink: {
      defaultProps: { underline: "always" },
      styleOverrides: {
        root: {
          color: semantic.textPrimary,
          fontWeight: 500,
          textUnderlineOffset: 3,
          textDecorationColor: colors.gray300,
          transition: "text-decoration-color 150ms cubic-bezier(0.4,0,0.2,1)",
          "&:hover": { textDecorationColor: semantic.textPrimary },
        },
      },
    },
  },
});

export default theme;
