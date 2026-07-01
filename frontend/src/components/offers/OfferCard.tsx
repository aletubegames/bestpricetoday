"use client";
import { useState, useCallback } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import type { Offer } from "@/types";
import { openTrackedOffer } from "@/lib/tracking";
import styles from "./OfferCard.module.css";

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

  return badges.sort((a, b) => a.priority - b.priority).slice(0, 3);
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 75 ? "#00e5a0" : score >= 50 ? "#fbbf24" : "#ff6b6b";
  const label = score >= 75 ? "Ótimo" : score >= 50 ? "Bom" : "Fraco";
  const circumference = 2 * Math.PI * 18;
  const dash = (score / 100) * circumference;

  return (
    <div className={styles.scoreRing}>
      <div className={styles.scoreRingWrap}>
        <svg width="48" height="48" className={styles.scoreRingWrap} style={{ transform: "rotate(-90deg)" }}>
          <circle cx="24" cy="24" r="18" fill="none" stroke="rgba(108,92,231,0.15)" strokeWidth="3" />
          <circle cx="24" cy="24" r="18" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round" />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 800, color }}>{Math.round(score)}</span>
        </div>
      </div>
      <span className={styles.scoreLabel} style={{ color }}>{label}</span>
    </div>
  );
}

interface Props {
  offer: Offer;
  rank: number;
  onCompare?: (offer: Offer) => void;
  compareMode?: boolean;
  isSelected?: boolean;
  hasCoupon?: boolean;
  couponText?: string;
}

export default function OfferCard({ offer, rank, onCompare, compareMode, isSelected, hasCoupon, couponText }: Props) {
  const p = PROVIDERS[offer.provider] ?? { name: offer.provider, color: "#a78bfa" };
  const logo = PROVIDER_LOGOS[offer.provider];
  const best = rank === 0;
  const badges = computeBadges(offer);
  const fmtPrice = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 });
  const [buyUrl, setBuyUrl] = useState<string>(offer.affiliate_url?.includes("/r/") ? offer.affiliate_url : offer.affiliate_url || "#");
  const [loadingUrl, setLoadingUrl] = useState(false);
  const [buyError, setBuyError] = useState(false);
  const [imgError, setImgError] = useState(false);

  // Adiciona badge de cupom se houver
  if (hasCoupon) {
    badges.push({ id: "coupon", label: `🏷️ Cupom ${couponText || ""}`.trim(), color: "#e11d48", bg: "rgba(225,29,72,.12)", border: "rgba(225,29,72,.3)", priority: 0.5 });
  }

  const handleBuy = useCallback(async (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    if (loadingUrl) return;
    setLoadingUrl(true);
    setBuyError(false);
    try {
      const url = await openTrackedOffer(offer);
      if (!url || url === "#") {
        setBuyError(true);
        setLoadingUrl(false);
        return;
      }
      setBuyUrl(url);
    } catch {
      setBuyError(true);
      setLoadingUrl(false);
    }
  }, [offer, loadingUrl]);

  const cardClass = [
    styles.card,
    isSelected ? styles.cardSelected : "",
  ].filter(Boolean).join(" ");

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.04, duration: 0.3 }}
      className={cardClass}
    >
      {best && <div className={styles.bestBorder} />}

      <div className={styles.body}>
        {/* Top bar: provider logo + compare button */}
        <div className={styles.topBar}>
          <div className={styles.providerGroup}>
            {logo && <div style={{ flexShrink: 0 }}>{logo}</div>}
            <span className={styles.providerName} style={{ color: p.color }}>
              {p.name}
            </span>
            {best && <span className={styles.bestBadge}>⚡ Melhor</span>}
          </div>
          {onCompare && (
            <button
              onClick={(e) => { e.preventDefault(); onCompare(offer); }}
              title="Comparar"
              aria-label="Adicionar à comparação"
              className={`${styles.compareBtn} ${isSelected ? styles.compareBtnSelected : ""}`}
            >
              ⊕
            </button>
          )}
        </div>

        {/* Fake discount alert */}
        {offer.is_fake_discount && (
          <div className={styles.fakeAlert}>
            ⚠️ Desconto possivelmente inflado
          </div>
        )}

        {/* Product image + title */}
        <div className={styles.productSection}>
          <div className={styles.imageWrap}>
            {offer.image_url && offer.image_url.startsWith("http") && !imgError ? (
              <Image src={offer.image_url} alt={offer.title} fill
                sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
                style={{ objectFit: "contain", padding: 8 }}
                loading="lazy"
                onError={() => setImgError(true)}
              />
            ) : (
              <span className={styles.imagePlaceholder}>🛍️</span>
            )}
          </div>
          <div>
            <p className={styles.title}>{offer.title}</p>
          </div>
        </div>

        {/* Price block */}
        <div className={styles.priceBlock}>
          <div>
            {offer.original_price && offer.final_price && offer.original_price > (offer.final_price + 0.5) && (
              <div className={styles.originalPrice}>
                R$ {fmtPrice(offer.original_price)}
              </div>
            )}
            <div className={styles.priceRow}>
              {offer.final_price && offer.final_price > 0.02 ? (
                <>
                  <span className={styles.currency}>R$</span>
                  <span className={styles.priceValue}>
                    {fmtPrice(offer.final_price)}
                  </span>
                </>
              ) : (
                <span className={styles.priceHidden}>🔥 Descubra o preço e fique surpreso!!</span>
              )}
            </div>
            {offer.economy > 0.5 && (
              <div className={styles.economy}>
                ↓ Economize R$ {fmtPrice(offer.economy)}
              </div>
            )}
          </div>
          <ScoreRing score={offer.score} />
        </div>
      </div>

      {/* Badges row */}
      {badges.length > 0 && (
        <div className={styles.badgesRow}>
          {badges.map(badge => (
            <span key={badge.id} className={styles.badge}
              style={{ color: badge.color, background: badge.bg, border: `1px solid ${badge.border}` }}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className={styles.ctaWrap}>
        {offer.affiliate_url ? (
          <a
            href={buyUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            onClick={handleBuy}
            className={[
              styles.cta,
              buyError ? styles.ctaError : best ? styles.ctaBest : "",
            ].filter(Boolean).join(" ")}
            style={{ opacity: loadingUrl ? 0.7 : 1 }}
          >
            {buyError ? "⚠️ Tente novamente" : loadingUrl ? "Carregando..." : "Ver oferta →"}
          </a>
        ) : (
          <div className={styles.ctaDisabled}>
            Link indisponível
          </div>
        )}
      </div>
    </motion.article>
  );
}
