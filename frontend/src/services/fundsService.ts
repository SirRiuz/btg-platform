import type { AxiosResponse } from "axios";

import httpClient from "./httpClient";
import type { FundFilterParams, FundListResponse } from "../types/fund";

export function listFunds(
  filters?: FundFilterParams,
): Promise<AxiosResponse<FundListResponse>> {
  return httpClient.get<FundListResponse>("/funds", { params: filters });
}
