import type { AxiosResponse } from "axios";

import httpClient from "./httpClient";
import type {
  CancelSubscriptionResponse,
  SubscribeRequest,
  SubscribeResponse,
  SubscriptionListResponse,
} from "../types/subscription";

export function subscribe(
  fundId: number,
  body?: SubscribeRequest,
): Promise<AxiosResponse<SubscribeResponse>> {
  return httpClient.post<SubscribeResponse>(
    `/funds/${fundId}/subscribe`,
    body ?? {},
  );
}

export function cancelSubscription(
  subscriptionId: string,
): Promise<AxiosResponse<CancelSubscriptionResponse>> {
  return httpClient.delete<CancelSubscriptionResponse>(
    `/subscriptions/${subscriptionId}`,
  );
}

export function listMySubscriptions(): Promise<
  AxiosResponse<SubscriptionListResponse>
> {
  return httpClient.get<SubscriptionListResponse>("/me/subscriptions");
}
