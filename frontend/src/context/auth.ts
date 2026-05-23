import { STORAGE_KEYS } from "../config";
import type { UserProfile } from "../types/user";

export function getAuthToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.authToken);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(STORAGE_KEYS.authToken, token);
}

export function removeAuthToken(): void {
  localStorage.removeItem(STORAGE_KEYS.authToken);
}

export function getStoredUser(): UserProfile | null {
  const raw = localStorage.getItem(STORAGE_KEYS.authUser);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    localStorage.removeItem(STORAGE_KEYS.authUser);
    return null;
  }
}

export function setStoredUser(user: UserProfile): void {
  localStorage.setItem(STORAGE_KEYS.authUser, JSON.stringify(user));
}

export function removeStoredUser(): void {
  localStorage.removeItem(STORAGE_KEYS.authUser);
}

export function clearAuthStorage(): void {
  removeAuthToken();
  removeStoredUser();
}
