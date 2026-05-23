export interface Subscription {
  id: string;
  fund_id: number;
  fund_nombre: string;
  amount: number;
  subscribed_at: string;
}

export interface SubscriptionListResponse {
  items: Subscription[];
  total: number;
  total_invested: number;
  current_balance: number;
}

export interface SubscribeRequest {
  amount?: number;
}

export interface SubscribeTransaction {
  id: string;
  type: "OPEN";
  amount: number;
}

export interface SubscribeResponse {
  subscription: Subscription;
  transaction: SubscribeTransaction;
  new_balance: number;
}

export interface CancelSubscriptionResponse {
  message: string;
  fund_nombre: string;
  amount_returned: number;
  new_balance: number;
  transaction_id: string;
}
