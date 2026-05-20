import type { Offer } from "@/types";
import { API_BASE } from "@/lib/api";

export const trackClick = (offer: Offer) => {
  fetch(`${API_BASE}/api/v1/clicks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      offer_id: offer.product_id || "",
      provider: offer.provider,
      product_title: offer.title,
      price: offer.final_price,
      affiliate_url: offer.affiliate_url || "",
      source: "web",
    }),
  }).catch((error: unknown) => {
    console.warn("Click tracking failed:", error);
  });
};

export const getTrackedUrl = async (offer: Offer, campaign = "offer_card"): Promise<string> => {
  if (offer.affiliate_url?.includes("/r/")) return offer.affiliate_url;
  if (!offer.affiliate_url) return "#";

  try {
    const res = await fetch(`${API_BASE}/api/v1/links/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        affiliate_url: offer.affiliate_url,
        provider: offer.provider,
        product_title: offer.title,
        price: offer.final_price,
        source: "web",
        campaign,
      }),
    });

    if (res.status === 429) {
      console.warn("Short link creation rate limited; using original affiliate URL.");
      return offer.affiliate_url || "#";
    }

    if (res.ok) {
      const data = await res.json();
      return data.url || data.short_url || offer.affiliate_url || "#";
    }
    console.warn("Short link creation failed:", res.status);
  } catch (error: unknown) {
    console.warn("Short link creation failed:", error);
  }

  return offer.affiliate_url || "#";
};

export const openTrackedOffer = async (offer: Offer, campaign = "offer_card"): Promise<string> => {
  const popup = window.open("about:blank", "_blank");
  if (popup) popup.opener = null;

  trackClick(offer);
  const url = await getTrackedUrl(offer, campaign);

  if (popup) {
    popup.location.href = url;
  } else {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return url;
};