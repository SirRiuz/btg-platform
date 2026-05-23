import type { ApiError, ErrorCode } from "../types/common";

const USER_MESSAGES: Record<ErrorCode, string> = {
  EMAIL_ALREADY_EXISTS:
    "Este correo ya está registrado. ¿Quieres iniciar sesión?",
  PHONE_ALREADY_EXISTS: "Este número de teléfono ya está registrado.",
  INVALID_CREDENTIALS:
    "Credenciales inválidas. Verifica tu correo y contraseña.",
  INACTIVE_USER: "Tu cuenta está deshabilitada. Contacta a soporte.",
  VALIDATION_ERROR: "Revisa los datos ingresados.",
  NETWORK_ERROR:
    "No se pudo conectar con el servidor. Verifica tu conexión.",
  UNKNOWN_ERROR: "Ocurrió un error inesperado. Intenta de nuevo.",
  INSUFFICIENT_BALANCE: "No tienes saldo suficiente para esta inversión.",
  AMOUNT_BELOW_MINIMUM: "El monto está por debajo del mínimo del fondo.",
  ALREADY_SUBSCRIBED:
    "Ya tienes una inversión activa en este fondo. Cancélala primero si quieres modificar el monto.",
  FUND_NOT_FOUND: "El fondo solicitado ya no existe.",
  FUND_INACTIVE: "Este fondo ya no está disponible.",
  SUBSCRIPTION_NOT_FOUND: "Esta inversión ya no existe.",
};

const PASSTHROUGH_BACKEND_MESSAGE = new Set<ErrorCode>([
  "INSUFFICIENT_BALANCE",
  "AMOUNT_BELOW_MINIMUM",
  "VALIDATION_ERROR",
]);

function isKnownCode(code: string): code is ErrorCode {
  return code in USER_MESSAGES;
}

export function getUserFriendlyMessage(error: ApiError): string {
  if (typeof error.error === "string" && isKnownCode(error.error)) {
    if (PASSTHROUGH_BACKEND_MESSAGE.has(error.error) && error.message) {
      return error.message;
    }
    return USER_MESSAGES[error.error];
  }
  return error.message || USER_MESSAGES.UNKNOWN_ERROR;
}

export function toApiError(value: unknown): ApiError {
  if (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    "message" in value &&
    typeof (value as ApiError).error === "string" &&
    typeof (value as ApiError).message === "string"
  ) {
    return value as ApiError;
  }
  return {
    error: "UNKNOWN_ERROR",
    message:
      value instanceof Error
        ? value.message
        : "Ocurrió un error inesperado. Intenta de nuevo.",
  };
}
