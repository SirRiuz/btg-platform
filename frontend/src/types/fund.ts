export type Categoria = "FPV" | "FIC";

export type PerfilRiesgo = "BAJO" | "MODERADO" | "ALTO";

export interface Fund {
  id: number;
  nombre: string;
  monto_minimo: number;
  categoria: Categoria;
  descripcion?: string;
  perfil_riesgo?: PerfilRiesgo;
  activo: boolean;
}

export interface FundFilterParams {
  categoria?: Categoria;
  perfil_riesgo?: PerfilRiesgo;
  skip?: number;
  limit?: number;
}

export interface FundListResponse {
  items: Fund[];
  total: number;
  skip: number;
  limit: number;
}
