import type { AxiosResponse } from "axios";

import httpClient from "./httpClient";
import type {
  TransactionFilterParams,
  TransactionListResponse,
} from "../types/transaction";

export function listMyTransactions(
  params?: TransactionFilterParams,
): Promise<AxiosResponse<TransactionListResponse>> {
  return httpClient.get<TransactionListResponse>("/me/transactions", {
    params,
  });
}
