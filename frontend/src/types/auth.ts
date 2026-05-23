import type { UserPublic } from "./user";

export interface RegisterRequest {
  nombre: string;
  apellido: string;
  email: string;
  telefono: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export type RegisterResponse = TokenResponse & {
  user: UserPublic;
};

export interface LogoutResponse {
  message: string;
}
