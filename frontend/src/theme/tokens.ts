export const colors = {
  white: "#FFFFFF",
  black: "#000000",
  gray50: "#FAFAFA",
  gray100: "#F5F5F5",
  gray200: "#EAEAEA",
  gray300: "#D4D4D4",
  gray400: "#A3A3A3",
  gray500: "#737373",
  gray600: "#525252",
  gray700: "#404040",
  gray800: "#262626",
  gray900: "#171717",
  red50: "#FEF2F2",
  red500: "#E5484D",
} as const;

export const semantic = {
  background: colors.white,
  backgroundSubtle: colors.gray50,
  backgroundHover: colors.gray100,
  borderDefault: colors.gray200,
  borderSubtle: colors.gray100,
  borderStrong: colors.gray300,
  borderFocus: colors.black,
  textPrimary: colors.gray900,
  textSecondary: colors.gray500,
  textTertiary: colors.gray400,
  textPlaceholder: colors.gray400,
  textOnDark: colors.white,
  ctaBg: colors.black,
  ctaBgHover: colors.gray800,
  ctaText: colors.white,
  ctaDisabledBg: colors.gray200,
  ctaDisabledText: colors.gray400,
  errorBg: colors.red50,
  errorBorder: colors.red500,
  errorText: colors.red500,
} as const;

export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  20: 80,
  24: 96,
} as const;

export const radius = {
  none: 0,
  sm: 4,
  md: 6,
} as const;

export const transition = {
  fast: "100ms cubic-bezier(0.4, 0, 0.2, 1)",
  default: "150ms cubic-bezier(0.4, 0, 0.2, 1)",
} as const;

export const fonts = {
  sans:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'IBM Plex Mono', 'SF Mono', Menlo, monospace",
} as const;

export const fontFeatures = "'cv02','cv03','cv04','cv11','ss01'";
export const fontFeaturesTabular = "'cv02','cv03','cv04','cv11','ss01','tnum'";

export const typography = {
  display: {
    fontSize: 32,
    lineHeight: 1.15,
    fontWeight: 600,
    letterSpacing: "-0.025em",
  },
  h1: {
    fontSize: 24,
    lineHeight: 1.25,
    fontWeight: 600,
    letterSpacing: "-0.02em",
  },
  h2: {
    fontSize: 18,
    lineHeight: 1.4,
    fontWeight: 600,
    letterSpacing: "-0.01em",
  },
  body: { fontSize: 14, lineHeight: 1.5, fontWeight: 400 },
  bodyEmphasis: { fontSize: 14, lineHeight: 1.5, fontWeight: 500 },
  small: { fontSize: 13, lineHeight: 1.4, fontWeight: 400 },
  caption: { fontSize: 12, lineHeight: 1.4, fontWeight: 400 },
  label: { fontSize: 13, lineHeight: 1.4, fontWeight: 500 },
} as const;

export type ColorToken = keyof typeof colors;
