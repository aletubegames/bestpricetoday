export interface Offer {
  provider: string;
  title: string;
  price: number;
  original_price?: number;
  discount_percent: number;
  coupon_code?: string;
  coupon_discount: number;
  cashback_percent: number;
  shipping_price: number;
  shipping_free: boolean;
  final_price: number;
  score: number;
  affiliate_url: string;
  image_url?: string;
  is_fake_discount: boolean;
  economy: number;
}

export interface SearchResponse {
  query: string;
  normalized_query: string;
  total: number;
  offers: Offer[];
  search_id?: string;
  cached: boolean;
  took_ms: number;
}
