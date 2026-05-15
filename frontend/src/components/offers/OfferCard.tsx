"use client";
import { motion } from "framer-motion";
import { ExternalLink, Truck, Tag, TrendingDown, AlertTriangle, Zap, Star } from "lucide-react";
import type { Offer } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://alessandro2090-bestpricetoday-api.hf.space';

function trackClick(offer: Offer) {
  fetch(`${API_URL}/api/v1/admin/clicks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      offer_id: offer.product_id || '',
      provider: offer.provider,
      product_title: offer.title,
      price: offer.final_price,
      affiliate_url: offer.affiliate_url,
      source: 'web',
    }),
  }).catch(() => {}); // fire and forget
}

const PROVIDERS: Record<string, { name: string; color: string; bg: string; emoji: string }> = {
  mercadolivre: { name: "Mercado Livre", color: "#FACC15", bg: "rgba(250,204,21,.1)",  emoji: "🟡" },
  amazon:       { name: "Amazon",        color: "#FB923C", bg: "rgba(251,146,60,.1)",  emoji: "📦" },
  shopee:       { name: "Shopee",        color: "#F87171", bg: "rgba(248,113,113,.1)", emoji: "🟠" },
  kabum:        { name: "KaBuM",         color: "#4ADE80", bg: "rgba(74,222,128,.1)",  emoji: "🟢" },
  aliexpress:   { name: "AliExpress",    color: "#F43F5E", bg: "rgba(244,63,94,.1)",   emoji: "🔴" },
  lomadee:      { name: "Lomadee",       color: "#C084FC", bg: "rgba(192,132,252,.1)", emoji: "🟣" },
  awin:         { name: "Awin",          color: "#60A5FA", bg: "rgba(96,165,250,.1)",  emoji: "🔵" },
};

interface Props { offer: Offer; rank: number; }

export default function OfferCard({ offer, rank }: Props) {
  const p = PROVIDERS[offer.provider] ?? { name: offer.provider, color: "#a78bfa", bg: "rgba(167,139,250,.1)", emoji: "🏪" };
  const best = rank === 0;
  const scoreColor = offer.score >= 70 ? "#00e5a0" : offer.score >= 45 ? "#fbbf24" : "#f87171";
  const fmtPrice = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 });

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.04, duration: 0.3 }}
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 0, overflow: "hidden", position: "relative" }}
    >
      {/* Best badge */}
      {best && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0,
          height: 3,
          background: "linear-gradient(90deg, #7c6aff, #a78bfa, #e879f9)",
        }} />
      )}

      <div style={{ padding: "20px 20px 16px" }}>

        {/* Fake discount alert */}
        {offer.is_fake_discount && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 11, fontWeight: 600, color: "#fb923c",
            background: "rgba(251,146,60,.08)", border: "1px solid rgba(251,146,60,.2)",
            borderRadius: 8, padding: "5px 10px", marginBottom: 12,
          }}>
            <AlertTriangle size={11} /> Desconto possivelmente inflado
          </div>
        )}

        {/* Provider + best */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            fontSize: 12, fontWeight: 700,
            color: p.color, background: p.bg,
            padding: "3px 10px", borderRadius: 99,
          }}>
            {p.emoji} {p.name}
          </span>
          {best && (
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              fontSize: 11, fontWeight: 700, color: "#fff",
              background: "linear-gradient(135deg,#7c6aff,#a78bfa)",
              padding: "3px 10px", borderRadius: 99,
            }}>
              <Zap size={10} fill="#fff" /> Melhor
            </span>
          )}
        </div>

        {/* Image + title row */}
        <div style={{ display: "flex", gap: 14, marginBottom: 18 }}>
          <div style={{
            width: 72, height: 72, borderRadius: 12, overflow: "hidden", flexShrink: 0,
            background: "var(--s3)", border: "1px solid var(--bd)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            {offer.image_url && offer.image_url.startsWith("http") ? (
              <img src={offer.image_url} alt={offer.title} loading="lazy"
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            ) : (
              <span style={{ fontSize: 28 }}>{p.emoji}</span>
            )}
          </div>
          <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--muted)", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical" as const }}>
            {offer.title}
          </p>
        </div>

        {/* Price block */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12 }}>
          <div>
            {offer.original_price && offer.price && offer.original_price > offer.price + 0.5 && (
              <div style={{ fontSize: 12, color: "var(--muted2)", textDecoration: "line-through", marginBottom: 2 }}>
                R$ {fmtPrice(offer.original_price)}
              </div>
            )}
            <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
              {offer.final_price && offer.final_price > 0.02
                ? <><span style={{ fontSize: 13, fontWeight: 600, color: "var(--muted)" }}>R$</span>
                   <span style={{ fontSize: 34, fontWeight: 900, letterSpacing: "-1px", lineHeight: 1, color: "var(--txt)" }}>{fmtPrice(offer.final_price)}</span></>
                : <span style={{ fontSize: 15, color: "var(--muted2)" }}>Preço indisponível</span>
              }
            </div>
            {offer.economy > 0.5 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: "var(--grn)", marginTop: 4 }}>
                <TrendingDown size={12} /> Economize R$ {fmtPrice(offer.economy)}
              </div>
            )}
          </div>

          {/* Score badge */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
            <div style={{
              width: 52, height: 52, borderRadius: 12, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              background: `${scoreColor}15`, border: `1.5px solid ${scoreColor}40`,
            }}>
              <span style={{ fontSize: 20, fontWeight: 900, color: scoreColor, lineHeight: 1 }}>
                {Math.round(offer.score)}
              </span>
              <span style={{ fontSize: 9, fontWeight: 600, color: scoreColor, opacity: 0.7, textTransform: "uppercase", letterSpacing: ".04em" }}>score</span>
            </div>
          </div>
        </div>
      </div>

      {/* Badges */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 20px 16px" }}>
        {offer.shipping_free && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: "var(--grn)", background: "rgba(0,229,160,.08)", border: "1px solid rgba(0,229,160,.2)", padding: "3px 10px", borderRadius: 99 }}>
            <Truck size={10} /> Frete grátis
          </span>
        )}
        {offer.discount_percent >= 3 && !offer.is_fake_discount && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700, color: "#fff", background: "linear-gradient(135deg,#7c6aff,#a78bfa)", padding: "3px 10px", borderRadius: 99 }}>
            <Star size={10} fill="#fff" /> -{Math.round(offer.discount_percent)}%
          </span>
        )}
        {offer.coupon_code && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: "#c084fc", background: "rgba(192,132,252,.08)", border: "1px solid rgba(192,132,252,.2)", padding: "3px 10px", borderRadius: 99 }}>
            <Tag size={10} /> {offer.coupon_code}
          </span>
        )}
        {offer.cashback_percent > 0 && (
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--ylw)", background: "rgba(251,191,36,.08)", border: "1px solid rgba(251,191,36,.2)", padding: "3px 10px", borderRadius: 99 }}>
            💰 {offer.cashback_percent}% cashback
          </span>
        )}
      </div>

      {/* CTA */}
      <div style={{ padding: "0 16px 16px" }}>
        {offer.affiliate_url ? (
          <a href={offer.affiliate_url} target="_blank" rel="noopener noreferrer"
          onClick={() => trackClick(offer)}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            padding: "13px 20px", borderRadius: 12,
            fontSize: 14, fontWeight: 700, textDecoration: "none",
            background: best ? "linear-gradient(135deg,#7c6aff,#a78bfa)" : "var(--s3)",
            color: best ? "#fff" : "var(--muted)",
            border: best ? "none" : "1px solid var(--bd)",
            transition: "filter .2s, transform .15s",
          }}
          onMouseEnter={e => Object.assign(e.currentTarget.style, { filter: "brightness(1.12)", transform: "translateY(-1px)" })}
          onMouseLeave={e => Object.assign(e.currentTarget.style, { filter: "brightness(1)", transform: "translateY(0)" })}
        >
          Ver oferta <ExternalLink size={14} />
        </a>
        ) : (
          <div style={{ padding: "13px 20px", borderRadius: 12, fontSize: 14, textAlign: "center", color: "var(--muted2)", background: "var(--s3)", border: "1px solid var(--bd)" }}>
            Link indisponível
          </div>
        )}
      </div>
    </motion.article>
  );
}
