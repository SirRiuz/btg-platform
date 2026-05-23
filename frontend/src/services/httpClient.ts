import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import { API_BASE_URL, HTTP_TIMEOUT_MS, STORAGE_KEYS } from "../config";
import type { ApiError } from "../types/common";
import { isApiError } from "../types/common";

const AUTH_PATHS = new Set(["/auth/login", "/auth/register"]);

function isAuthRequest(url: string | undefined): boolean {
  if (!url) return false;
  try {
    const path = url.startsWith("http")
      ? new URL(url).pathname
      : url.split("?")[0];
    return AUTH_PATHS.has(path);
  } catch {
    return false;
  }
}

const httpClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: HTTP_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

httpClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem(STORAGE_KEYS.authToken);
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
);

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError | unknown>) => {
    if (error.response) {
      const { status, data } = error.response;
      const requestUrl = error.config?.url;

      if (status === 401 && !isAuthRequest(requestUrl)) {
        localStorage.removeItem(STORAGE_KEYS.authToken);
        localStorage.removeItem(STORAGE_KEYS.authUser);
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }

      if (isApiError(data)) {
        return Promise.reject(data);
      }

      const fallback: ApiError = {
        error: "UNKNOWN_ERROR",
        message:
          typeof (data as { message?: unknown })?.message === "string"
            ? (data as { message: string }).message
            : "Error inesperado.",
      };
      return Promise.reject(fallback);
    }

    const networkError: ApiError = {
      error: "NETWORK_ERROR",
      message:
        error.code === "ECONNABORTED"
          ? "La solicitud tardó demasiado. Intenta de nuevo."
          : "No se pudo conectar.",
    };
    return Promise.reject(networkError);
  },
);

export default httpClient;
