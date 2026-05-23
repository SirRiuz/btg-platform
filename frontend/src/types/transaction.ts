export type TransactionType = "OPEN" | "CANCEL";

export interface Transaction {
  id: string;
  type: TransactionType;
  fund_id: number;
  fund_nombre: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  timestamp: string;
}

export interface TransactionFilterParams {
  skip?: number;
  limit?: number;
  type?: TransactionType;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  skip: number;
  limit: number;
}
