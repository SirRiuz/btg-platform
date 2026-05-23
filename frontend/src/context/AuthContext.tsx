import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { getMyProfile } from "../services/accountsService";
import * as authService from "../services/authService";
import type {
  NotificationSettings,
  UserProfile,
  UserPublic,
} from "../types/user";
import {
  clearAuthStorage,
  getAuthToken,
  getStoredUser,
  setAuthToken,
  setStoredUser,
} from "./auth";

export interface AuthContextValue {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  register: (token: string, initialUser: UserPublic) => Promise<void>;
  logout: () => Promise<void>;
  updateBalance: (newBalance: number) => void;
  updateNotificationSettings: (settings: NotificationSettings) => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserProfile | null>(() => {
    return getAuthToken() ? getStoredUser() : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(() => !!getAuthToken());
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchProfile = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const response = await getMyProfile();
      if (!mountedRef.current) return null;
      setUser(response.data);
      setStoredUser(response.data);
      return response.data;
    } catch {
      if (!mountedRef.current) return null;
      clearAuthStorage();
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    if (!getAuthToken()) {
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      await fetchProfile();
      if (!cancelled) setIsLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchProfile]);

  const login = useCallback(
    async (token: string): Promise<void> => {
      setAuthToken(token);
      await fetchProfile();
    },
    [fetchProfile],
  );

  const register = useCallback(
    async (token: string, initialUser: UserPublic): Promise<void> => {
      setAuthToken(token);
      const optimistic: UserProfile = {
        ...initialUser,
        settings: { allow_email: true, allow_sms: true },
      };
      setUser(optimistic);
      setStoredUser(optimistic);
      await fetchProfile();
    },
    [fetchProfile],
  );

  const updateBalance = useCallback((newBalance: number): void => {
    setUser((prev) => {
      if (!prev) return prev;
      const next = { ...prev, balance: newBalance };
      setStoredUser(next);
      return next;
    });
  }, []);

  const updateNotificationSettings = useCallback(
    (settings: NotificationSettings): void => {
      setUser((prev) => {
        if (!prev) return prev;
        const next = { ...prev, settings };
        setStoredUser(next);
        return next;
      });
    },
    [],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authService.logout();
    } catch {
      // Logout local debe funcionar incluso si el servidor falla.
    } finally {
      clearAuthStorage();
      if (mountedRef.current) setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user && !!getAuthToken(),
      isLoading,
      login,
      register,
      logout,
      updateBalance,
      updateNotificationSettings,
    }),
    [
      user,
      isLoading,
      login,
      register,
      logout,
      updateBalance,
      updateNotificationSettings,
    ],
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}
