"use client"
import { useEffect, useState } from "react"
import { API_BASE as API } from "@/lib/api"
import TikTokPublisher from "@/components/TikTokPublisher"

const PROVIDER_LOGOS: Record<string, string> = {
  aliexpress: "🔴", shopee: "🟠", mercadolivre: "🟡",
  amazon: "📦", lomadee: "🟣", kabum: "🟢",
}

export default function ProductSearchClient({ query }: { query: string }) {
  const [offers, setOffers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    fetch(`${API}/api/v1/search?q=${encodeURIComponent(query)}&limit=10`)
      .then(r => r.json())
      .then(d => {
        setOffers(d.offers || [])
        setTotal(d.total || 0)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [query])

  if (loading) return (
    <div style={{ color: "#4a4a6a", padding: 40, textAlign: "center" }}>
      🔍 Buscando melhores preços...
    </div>
  )

  if (!offers.length) return (
    <div style={{ color: "#4a4a6a", padding: 40, textAlign: "center" }}>
      <p style={{ fontSize: 40 }}>😕</p>
      <p>Nenhum resultado encontrado para &quot;{query}&quot;.</p>
      <a href="/" style={{ color: "#7c6aff" }}>← Voltar para busca</a>
    </div>
  )

  return (
    <div>
      <p style={{ color: "#4a4a6a", marginBottom: 20 }}>
        <strong style={{ color: "#1a1a2e" }}>{total}</strong> oferta{total !== 1 ? "s" : ""} encontrada{total !== 1 ? "s" : ""}
      </p>
      <div style={{ display: "grid", gap: 16 }} className="offer-grid">
        {offers.map((offer, i) => {
          const isFirst = i === 0
          const logo = PROVIDER_LOGOS[offer.provider] || "🏪"
          return (
            <div key={i} style={{
              background: "#ffffff",
              border: `1px solid ${isFirst ? "rgba(0,229,160,0.4)" : "rgba(124,106,255,0.15)"}`,
              borderRadius: 14, overflow: "hidden",
            }}>
              {isFirst && (
                <div style={{ background: "linear-gradient(90deg,#00e5a0,#0ea5e9)", height: 3 }} />
              )}
              <div style={{ padding: 16 }}>
                {isFirst && (
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#00e5a0", marginBottom: 8 }}>
                    ✓ MENOR PREÇO
                  </div>
                )}
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <span style={{ fontSize: 16 }}>{logo}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#a78bfa", textTransform: "capitalize" }}>
                    {offer.provider}
                  </span>
                  {offer.discount_percent >= 5 && !offer.is_fake_discount && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: "#ff6b6b", background: "rgba(255,107,107,.12)", padding: "2px 8px", borderRadius: 99 }}>
                      -{Math.round(offer.discount_percent)}%
                    </span>
                  )}
                </div>
                {offer.image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={offer.image_url} alt={offer.title}
                    style={{ width: "100%", height: 160, objectFit: "contain", borderRadius: 8, background: "#eef0ff", marginBottom: 12 }}
                    onError={e => { (e.target as HTMLImageElement).style.display = "none" }}
                  />
                )}
                <p style={{ fontSize: 13, color: "#4a4a6a", lineHeight: 1.5, marginBottom: 12, minHeight: 40 }}>
                  {offer.title?.slice(0, 80)}...
                </p>
                {offer.original_price > offer.final_price && (
                  <div style={{ fontSize: 12, color: "#475569", textDecoration: "line-through" }}>
                    R$ {offer.original_price?.toFixed(2)}
                  </div>
                )}
                <div style={{ fontSize: 28, fontWeight: 900, color: "#1a1a2e", marginBottom: 4 }}>
                  R$ {offer.final_price?.toFixed(2)}
                </div>
                {offer.shipping_free && (
                  <div style={{ fontSize: 12, color: "#00e5a0", marginBottom: 12 }}>✅ Frete grátis</div>
                )}
                <a href={offer.affiliate_url} target="_blank" rel="noopener noreferrer"
                  style={{
                    display: "block", textAlign: "center",
                    padding: "12px", borderRadius: 10, fontWeight: 700,
                    background: isFirst ? "linear-gradient(135deg,#00e5a0,#0ea5e9)" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
                    color: isFirst ? "#000" : "#fff",
                    textDecoration: "none", fontSize: 14,
                  }}
                >
                  Ver oferta →
                </a>
                <TikTokPublisher offer={offer} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Internal links for SEO */}
      <div style={{ marginTop: 40, paddingTop: 24, borderTop: "1px solid #1e293b" }}>
        <p style={{ color: "#475569", fontSize: 13, marginBottom: 12 }}>Buscas relacionadas:</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[`${query} barato`, `${query} oferta`, `${query} desconto`, `melhor ${query}`].map(s => (
            <a key={s} href={`/produto/${encodeURIComponent(s)}`}
              style={{ padding: "6px 14px", borderRadius: 99, background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", color: "#4a4a6a", textDecoration: "none", fontSize: 13 }}>
              {s}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
