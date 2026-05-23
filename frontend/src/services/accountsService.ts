import type { AxiosResponse } from "axios";

import httpClient from "./httpClient";
import type {
  NotificationSettings,
  UpdateNotificationResponse,
  UserProfile,
  UserRole,
} from "../types/user";

// Backend devuelve el perfil en snake_case inglés (first_name, last_name, phone);
// la UI lo consume en español. Este mapper es el anti-corruption layer.

interface BackendUserProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  balance: number;
  role: UserRole;
  settings: NotificationSettings;
  created_at?: string;
  updated_at?: string;
}

function mapUserProfile(u: BackendUserProfile): UserProfile {
  return {
    id: u.id,
    nombre: u.first_name,
    apellido: u.last_name,
    email: u.email,
    telefono: u.phone,
    balance: u.balance,
    role: u.role,
    settings: u.settings,
    created_at: u.created_at,
    updated_at: u.updated_at,
  };
}

export function getMyProfile(): Promise<AxiosResponse<UserProfile>> {
  return httpClient
    .get<BackendUserProfile>("/accounts/me")
    .then((res) => ({
      ...res,
      data: mapUserProfile(res.data),
    }));
}

export function updateEmailNotifications(
  enabled: boolean,
): Promise<AxiosResponse<UpdateNotificationResponse>> {
  // Body { enabled } y response { settings, message } no tienen mismatch.
  return httpClient.put<UpdateNotificationResponse>(
    "/accounts/me/settings/email-notifications",
    { enabled },
  );
}

export function updateSmsNotifications(
  enabled: boolean,
): Promise<AxiosResponse<UpdateNotificationResponse>> {
  return httpClient.put<UpdateNotificationResponse>(
    "/accounts/me/settings/sms-notifications",
    { enabled },
  );
}
