"use client";
import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import type { Offer } from "@/types";
import TikTokPublisher from "@/components/TikTokPublisher";
import { openTrackedOffer } from "@/lib/tracking";

const PROVIDER_LOGOS: Record<string, React.ReactNode> = {
  aliexpress: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#FF4747"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">AE</text>
    </svg>
  ),
  shopee: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#EE4D2D"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">S</text>
    </svg>
  ),
  mercadolivre: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#FFE600"/>
      <text x="50%" y="65%" textAnchor="middle" fill="#333" fontSize="14" fontWeight="bold">ML</text>
    </svg>
  ),
  amazon: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#FF9900"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">amz</text>
    </svg>
  ),
  lomadee: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#7C3AED"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">L</text>
    </svg>
  ),
  kabum: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#FF6B00"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">K</text>
    </svg>
  ),
  awin: (
    <svg width="20" height="20" viewBox="0 0 40 40">
      <rect width="40" height="40" rx="8" fill="#60A5FA"/>
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">AW</text>
    </svg>
  ),
};

const PROVIDERS: Record<string, { name: string; color: string }> = {
  mercadolivre: { name: "Mercado Livre", color: "#FACC15" },
  amazon:       { name: "Amazon",        color: "#FB923C" },
  shopee:       { name: "Shopee",        color: "#F87171" },
  kabum:        { name: "KaBuM",         color: "#4ADE80" },
  aliexpress:   { name: "AliExpress",    color: "#F43F5E" },
  lomadee:      { name: "Lomadee",       color: "#C084FC" },
  awin:         { name: "Awin",          color: "#60A5FA" },
};

interface BadgeConfig {
  id: string;
  label: string;
  color: string;
  bg: string;
  border: string;
  priority: number;
}

function computeBadges(offer: Offer): BadgeConfig[] {
  const badges: BadgeConfig[] = [];

  if (offer.is_fake_discount) {
    badges.push({ id: "fake", label: "⚠️ Desconto Inflado", color: "#fb923c", bg: "rgba(251,146,60,.12)", border: "rgba(251,146,60,.3)", priority: 0 });
  }
  if (offer.discount_percent >= 30 && !offer.is_fake_discount) {
    badges.push({ id: "hot", label: "🔥 Oferta Quente", color: "#ff6b6b", bg: "rgba(255,107,107,.12)", border: "rgba(255,107,107,.3)", priority: 1 });
  }
  if (offer.score >= 80) {
    badges.push({ id: "best", label: "⭐ Melhor Preço", color: "#fbbf24", bg: "rgba(251,191,36,.12)", border: "rgba(251,191,36,.3)", priority: 2 });
  }
  if (offer.discount_percent > 0 && !offer.is_fake_discount) {
    badges.push({ id: "drop", label: `↓ -${Math.round(offer.discount_percent)}% hoje`, color: "#00e5a0", bg: "rgba(0,229,160,.1)", border: "rgba(0,229,160,.25)", priority: 3 });
  }
  if (offer.shipping_free) {
    badges.push({ id: "free_ship", label: "🚚 Frete Grátis", color: "#60a5fa", bg: "rgba(96,165,250,.1)", border: "rgba(96,165,250,.25)", priority: 4 });
  }
  if (offer.cashback_percent > 0) {
    badges.push({ id: "cashback", label: `💰 ${offer.cashback_percent}% Cashback`, color: "#a78bfa", bg: "rgba(167,139,250,.1)", border: "rgba(167,139,250,.25)", priority: 5 });
  }
  if (offer.coupon_code) {
    badges.push({ id: "coupon", label: `🏷️ ${offer.coupon_code}`, color: "#e879f9", bg: "rgba(232,121,249,.1)", border: "rgba(232,121,249,.25)", priority: 6 });
  }

  return badges.sort((a, b) => a.priority - b.priority).slice(0, 3);
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 75 ? "#00e5a0" : score >= 50 ? "#fbbf24" : "#ff6b6b";
  const label = score >= 75 ? "Ótimo" : score >= 50 ? "Bom" : "Fraco";
  const circumference = 2 * Math.PI * 18;
  const dash = (score / 100) * circumference;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
      <div style={{ position: "relative", width: 48, height: 48 }}>
        <svg width="48" height="48" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="24" cy="24" r="18" fill="none" stroke="#1e293b" strokeWidth="3" />
          <circle cx="24" cy="24" r="18" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round" />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 800, color }}>{Math.round(score)}</span>
        </div>
      </div>
      <span style={{ fontSize: 9, fontWeight: 700, color, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</span>
    </div>
  );
}

interface Props {
  offer: Offer;
  rank: number;
  onCompare?: (offer: Offer) => void;
  compareMode?: boolean;
  isSelected?: boolean;
}

export default function OfferCard({ offer, rank, onCompare, compareMode, isSelected }: Props) {
  const p = PROVIDERS[offer.provider] ?? { name: offer.provider, color: "#a78bfa" };
  const logo = PROVIDER_LOGOS[offer.provider];
  const best = rank === 0;
  const badges = computeBadges(offer);
  const fmtPrice = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 });
  const [buyUrl, setBuyUrl] = useState<string>(offer.affiliate_url?.includes("/r/") ? offer.affiliate_url : "#");
  const [loadingUrl, setLoadingUrl] = useState(false);

  const handleBuy = useCallback(async (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    if (!loadingUrl) {
      setLoadingUrl(true);
      const url = await openTrackedOffer(offer);
      setBuyUrl(url);
      setLoadingUrl(false);
    }
  }, [offer, loadingUrl]);

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.04, duration: 0.3 }}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 0,
        overflow: "hidden",
        position: "relative",
        background: "#ffffff",
        border: `1px solid ${isSelected ? "rgba(108,92,231,0.6)" : "rgba(108,92,231,0.15)"}`,
        borderRadius: 14,
        transition: "border-color 0.2s, box-shadow 0.2s, transform 0.15s",
        cursor: "default",
      }}
      whileHover={{
        y: -2,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.borderColor = "rgba(108,92,231,0.4)";
        (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 24px rgba(108,92,231,0.12)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.borderColor = isSelected ? "rgba(108,92,231,0.6)" : "rgba(108,92,231,0.15)";
        (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 8px rgba(0,0,0,0.06)";
      }}
    >
      {/* Best card top gradient border */}
      {best && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0,
          height: 3,
          background: "linear-gradient(90deg, #7c6aff, #a78bfa, #e879f9)",
        }} />
      )}

      <div style={{ padding: "20px 20px 0" }}>
        {/* Top bar: provider logo + compare button */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {logo && <div style={{ flexShrink: 0 }}>{logo}</div>}
            <span style={{
              fontSize: 12, fontWeight: 700,
              color: p.color,
              textTransform: "capitalize",
            }}>
              {p.name}
            </span>
            {best && (
              <span style={{
                fontSize: 10, fontWeight: 700, color: "#fff",
                background: "linear-gradient(135deg,#6c5ce7,#8b7cf8)",
                padding: "2px 8px", borderRadius: 99,
              }}>
                ⚡ Melhor
              </span>
            )}
          </div>
          {onCompare && (
            <button
              onClick={(e) => { e.preventDefault(); onCompare(offer); }}
              title="Comparar"
              style={{
                width: 28, height: 28, borderRadius: 6,
                background: isSelected ? "#7c6aff" : "rgba(124,106,255,0.15)",
                border: `1px solid ${isSelected ? "#7c6aff" : "rgba(124,106,255,0.3)"}`,
                color: isSelected ? "#fff" : "#7c6aff",
                fontSize: 14, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.2s",
                flexShrink: 0,
              }}
            >
              ⊕
            </button>
          )}
        </div>

        {/* Fake discount alert */}
        {offer.is_fake_discount && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 11, fontWeight: 600, color: "#fb923c",
            background: "rgba(251,146,60,.08)", border: "1px solid rgba(251,146,60,.2)",
            borderRadius: 8, padding: "5px 10px", marginBottom: 12,
          }}>
            ⚠️ Desconto possivelmente inflado
          </div>
        )}

        {/* Product image + title */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 12 }}>
          <div style={{
            width: "100%", height: 180, borderRadius: 10, overflow: "hidden",
            background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.1)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            {offer.image_url && offer.image_url.startsWith("http") ? (
              <img src={offer.image_url} alt={offer.title} loading="lazy"
                style={{ width: "100%", height: "100%", objectFit: "contain", padding: 8 }}
                onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ) : (
              <span style={{ fontSize: 40, opacity: 0.4 }}>🛍️</span>
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <p style={{
              fontSize: 12, lineHeight: 1.5,
              color: "rgba(26,26,46,0.75)",
              overflow: "hidden", display: "-webkit-box",
              WebkitLineClamp: 3, WebkitBoxOrient: "vertical" as const,
              margin: 0,
            }}>
              {offer.title}
            </p>
          </div>
        </div>

        {/* Price block */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12, marginBottom: 12 }}>
          <div>
            {offer.original_price && offer.final_price && offer.original_price > (offer.final_price + 0.5) && (
              <div style={{ fontSize: 12, color: "rgba(26,26,46,0.30)", textDecoration: "line-through", marginBottom: 2 }}>
                R$ {fmtPrice(offer.original_price)}
              </div>
            )}
            <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
              {offer.final_price && offer.final_price > 0.02 ? (
                <>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(26,26,46,0.45)" }}>R$</span>
                  <span style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-1px", lineHeight: 1, color: "#1a1a2e" }}>
                    {fmtPrice(offer.final_price)}
                  </span>
                </>
              ) : (
                <span style={{ fontSize: 13, fontWeight: 700, color: "#facc15", letterSpacing: "-0.3px" }}>🔥 Descubra o preço e fique surpreso!!</span>
              )}
            </div>
            {offer.economy > 0.5 && (
              <div style={{ fontSize: 12, fontWeight: 600, color: "#00e5a0", marginTop: 4 }}>
                ↓ Economize R$ {fmtPrice(offer.economy)}
              </div>
            )}
          </div>
          <ScoreRing score={offer.score} />
        </div>
      </div>

      {/* Badges row */}
      {badges.length > 0 && (
        <div style={{ display: "flex", gap: 6, padding: "0 20px 12px", flexWrap: "wrap" }}>
          {badges.map(badge => (
            <span key={badge.id} style={{
              fontSize: 11, fontWeight: 600,
              color: badge.color,
              background: badge.bg,
              border: `1px solid ${badge.border}`,
              padding: "3px 10px", borderRadius: 99,
              whiteSpace: "nowrap",
            }}>
              {badge.label}
            </span>
          ))}
        </div>
      )}

      {/* CTA */}
      <div style={{ padding: "0 16px 16px" }}>
        {offer.affiliate_url ? (
          <a
            href={buyUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleBuy}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "13px 20px", borderRadius: 12,
              fontSize: 14, fontWeight: 700, textDecoration: "none",
              background: best ? "linear-gradient(135deg,#7c6aff,#a78bfa)" : "#f5f7ff",
              color: best ? "#fff" : "rgba(26,26,46,0.7)",
              border: best ? "none" : "1px solid rgba(108,92,231,0.2)",
              transition: "filter .2s, transform .15s",
              opacity: loadingUrl ? 0.7 : 1,
            }}
            onMouseEnter={e => Object.assign(e.currentTarget.style, { filter: "brightness(1.12)", transform: "translateY(-1px)" })}
            onMouseLeave={e => Object.assign(e.currentTarget.style, { filter: "brightness(1)", transform: "translateY(0)" })}
          >
            {loadingUrl ? "Carregando..." : "Ver oferta →"}
          </a>
        ) : (
          <div style={{
            padding: "13px 20px", borderRadius: 12, fontSize: 14,
            textAlign: "center", color: "rgba(26,26,46,0.3)",
            background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.15)",
          }}>
            Link indisponível
          </div>
        )}
        <TikTokPublisher offer={offer} />
      </div>
    </motion.article>
  );
}

