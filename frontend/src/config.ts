const rawBaseUrl = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL: string =
  typeof rawBaseUrl === "string" && rawBaseUrl.length > 0
    ? rawBaseUrl
    : "http://localhost:8000";

export const HTTP_TIMEOUT_MS = 15_000;

export const STORAGE_KEYS = {
  authToken: "btg_auth_token",
  authUser: "btg_auth_user",
} as const;
