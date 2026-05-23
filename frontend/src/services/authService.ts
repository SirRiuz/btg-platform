import type { AxiosResponse } from "axios";

import httpClient from "./httpClient";
import type {
  LoginRequest,
  LogoutResponse,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
} from "../types/auth";
import type { UserPublic, UserRole } from "../types/user";

// Backend usa convención snake_case en inglés (first_name, last_name, phone);
// la UI se mantiene en español. Esta capa de mapping es el anti-corruption
// layer entre ambos contratos.

interface BackendUserPublic {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  balance: number;
  role: UserRole;
}

interface BackendRegisterResponse {
  access_token: string;
  token_type: "bearer";
  user: BackendUserPublic;
}

function mapUserPublic(u: BackendUserPublic): UserPublic {
  return {
    id: u.id,
    nombre: u.first_name,
    apellido: u.last_name,
    email: u.email,
    telefono: u.phone,
    balance: u.balance,
    role: u.role,
  };
}

export function register(
  params: RegisterRequest,
): Promise<AxiosResponse<RegisterResponse>> {
  const backendPayload = {
    first_name: params.nombre,
    last_name: params.apellido,
    email: params.email,
    phone: params.telefono,
    password: params.password,
  };
  return httpClient
    .post<BackendRegisterResponse>("/auth/register", backendPayload)
    .then((res) => ({
      ...res,
      data: {
        access_token: res.data.access_token,
        token_type: res.data.token_type,
        user: mapUserPublic(res.data.user),
      },
    }));
}

export function login(
  params: LoginRequest,
): Promise<AxiosResponse<TokenResponse>> {
  // Sin mismatch: el contrato es { email, password } en ambos lados.
  return httpClient.post<TokenResponse>("/auth/login", params);
}

export function logout(): Promise<AxiosResponse<LogoutResponse>> {
  return httpClient.post<LogoutResponse>("/auth/logout");
}
