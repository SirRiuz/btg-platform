export type ErrorCode =
  | "EMAIL_ALREADY_EXISTS"
  | "PHONE_ALREADY_EXISTS"
  | "INVALID_CREDENTIALS"
  | "INACTIVE_USER"
  | "VALIDATION_ERROR"
  | "NETWORK_ERROR"
  | "UNKNOWN_ERROR"
  | "INSUFFICIENT_BALANCE"
  | "AMOUNT_BELOW_MINIMUM"
  | "ALREADY_SUBSCRIBED"
  | "FUND_NOT_FOUND"
  | "FUND_INACTIVE"
  | "SUBSCRIPTION_NOT_FOUND";

export interface ApiError {
  error: ErrorCode | string;
  message: string;
  details?: unknown;
}

export function isApiError(value: unknown): value is ApiError {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.error === "string" &&
    typeof candidate.message === "string"
  );
}
