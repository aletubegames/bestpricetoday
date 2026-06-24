export interface Offer {
  provider: string;
  title: string;
  price: number | null;
  original_price?: number | null;
  discount_percent: number;
  coupon_code?: string;
  coupon_discount: number;
  cashback_percent: number;
  shipping_price: number;
  shipping_free: boolean;
  final_price: number | null;
  score: number;
  product_id?: string;
  product_url?: string;
  affiliate_url?: string;
  tracking_id?: string;
  image_url?: string;
  is_fake_discount: boolean;
  economy: number;
}

export type ProviderSearchState =
  | "ok"
  | "no_results"
  | "not_configured"
  | "blocked"
  | "low_relevance"
  | "error";

export interface ProviderStatus {
  provider: string;
  status: ProviderSearchState;
  message?: string | null;
  http_status?: number | null;
  raw_count: number;
  returned_count: number;
  filtered_count: number;
}

export interface SearchResponse {
  query: string;
  normalized_query: string;
  total: number;
  offers: Offer[];
  provider_statuses: ProviderStatus[];
  search_id?: string;
  cached: boolean;
  took_ms: number;
}

export interface TrendingSearchItem {
  query: string;
  score: number;
}

export interface TrendingSearchResponse {
  items: TrendingSearchItem[];
}
