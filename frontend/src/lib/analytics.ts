/**
 * Analytics helper — GA4 event tracking + Meta Pixel.
 *
 * Usa as variáveis de ambiente:
 * - NEXT_PUBLIC_GA4_ID (Google Analytics 4)
 * - NEXT_PUBLIC_FB_PIXEL_ID (Meta/Facebook Pixel)
 *
 * Se não estiverem setadas, as funções são no-op (não quebram o app).
 */

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    fbq?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

type EventParams = Record<string, string | number | boolean | undefined>;

/**
 * Envia um evento para o Google Analytics 4.
 * Não faz nada se GA4 não estiver configurado.
 */
export const trackEvent = (event: string, params?: EventParams): void => {
  if (typeof window === "undefined") return;
  if (typeof window.gtag !== "function") return;
  window.gtag("event", event, params || {});
};

/**
 * Envia um evento para o Meta (Facebook) Pixel.
 * Não faz nada se o Pixel não estiver configurado.
 */
export const trackPixelEvent = (event: string, params?: EventParams): void => {
  if (typeof window === "undefined") return;
  if (typeof window.fbq !== "function") return;
  window.fbq("track", event, params || {});
};

// ─── Eventos específicos (tipados para consistência) ──────────────────────────

/** Usuário clicou em "Ver oferta" / "Comprar" */
export const trackClickOffer = (params: {
  provider?: string;
  product_title?: string;
  price?: number;
  source?: string;
}): void => {
  trackEvent("click_offer", params);
  trackPixelEvent("ViewContent", {
    content_name: params.product_title,
    value: params.price,
    currency: "BRL",
  });
};

/** Usuário copiou um cupom */
export const trackCopyCoupon = (params: {
  coupon_code?: string;
  discount_text?: string;
  store_name?: string;
}): void => {
  trackEvent("copy_coupon", params);
};

/** Usuário criou um alerta de preço */
export const trackCreateAlert = (params: {
  product?: string;
  target_price?: number;
}): void => {
  trackEvent("create_alert", params);
  trackPixelEvent("Lead", {
    content_name: params.product,
    value: params.target_price,
    currency: "BRL",
  });
};

/** Usuário fez uma busca */
export const trackSearch = (query: string): void => {
  trackEvent("search", { search_term: query });
};

/** Usuário se cadastrou */
export const trackSignUp = (method = "email"): void => {
  trackEvent("sign_up", { method });
  trackPixelEvent("CompleteRegistration", { method });
};

/** Usuário fez login */
export const trackLogin = (method = "email"): void => {
  trackEvent("login", { method });
};
