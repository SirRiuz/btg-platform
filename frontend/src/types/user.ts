export type UserRole = "USER" | "ADMIN";

export interface NotificationSettings {
  allow_email: boolean;
  allow_sms: boolean;
}

export interface UserPublic {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  telefono: string;
  balance: number;
  role: UserRole;
}

export interface UserProfile extends UserPublic {
  settings: NotificationSettings;
  created_at?: string;
  updated_at?: string;
}

export interface UpdateNotificationRequest {
  enabled: boolean;
}

export interface UpdateNotificationResponse {
  settings: NotificationSettings;
  message: string;
}
