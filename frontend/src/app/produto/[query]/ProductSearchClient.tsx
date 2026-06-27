"use client"
import { useCallback, useState } from "react"
import type { MouseEvent } from "react"
import { API_BASE as API, apiFetch } from "@/lib/api"
import { openTrackedOffer } from "@/lib/tracking"
import type { Offer } from "@/types"

const PROVIDER_LOGOS: Record<string, string> = {
  aliexpress: "🔴", shopee: "🟠", mercadolivre: "🟡",
  amazon: "📦", lomadee: "🟣", kabum: "🟢",
}

interface Props {
  query: string
  initialOffers: Offer[]
  initialTotal: number
}

export default function ProductSearchClient({ query, initialOffers, initialTotal }: Props) {
  // Começa com as ofertas do SSR (já no HTML) — sem loading inicial
  const [offers, setOffers] = useState<Offer[]>(initialOffers)
  const [total, setTotal] = useState(initialTotal)
  const [loading, setLoading] = useState(false)
  const [openingOfferKey, setOpeningOfferKey] = useState<string | null>(null)

  const offerKey = useCallback((offer: Offer, index: number) => {
    return `${offer.provider}-${offer.product_id || offer.affiliate_url || index}`
  }, [])

  const handleOfferClick = useCallback(async (event: MouseEvent<HTMLAnchorElement>, offer: Offer, index: number) => {
    event.preventDefault()
    if (!offer.affiliate_url) return

    const key = offerKey(offer, index)
    setOpeningOfferKey(key)

    try {
      await openTrackedOffer(offer, "product_search")
    } finally {
      setOpeningOfferKey(null)
    }
  }, [offerKey])

  // Refetch manual (botão "atualizar") — opcional, não bloqueia render
  const refetch = useCallback(async () => {
    setLoading(true)
    try {
      const r = await apiFetch(`${API}/api/v1/search?q=${encodeURIComponent(query)}&limit=40`)
      const d = await r.json()
      setOffers(d.offers || [])
      setTotal(d.total || 0)
    } catch (error) {
      console.warn("Product search refetch failed:", error)
    } finally {
      setLoading(false)
    }
  }, [query])

  if (!offers.length) return (
    <div style={{ color: "#4a4a6a", padding: 40, textAlign: "center" }}>
      <p style={{ fontSize: 40 }}>😕</p>
      <p>Nenhum resultado encontrado para &quot;{query}&quot;.</p>
      <a href="/" style={{ color: "#7c6aff" }}>← Voltar para busca</a>
    </div>
  )

  return (
    <div>
      <p style={{ color: "#4a4a6a", marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
        <span>
          <strong style={{ color: "#1a1a2e" }}>{total}</strong> oferta{total !== 1 ? "s" : ""} encontrada{total !== 1 ? "s" : ""}
        </span>
        <button
          onClick={refetch}
          disabled={loading}
          style={{
            padding: "4px 12px", borderRadius: 8, border: "1px solid rgba(108,92,231,0.2)",
            background: "transparent", color: "#7c6aff", cursor: "pointer", fontSize: 12,
          }}
        >
          {loading ? "Atualizando..." : "↻ Atualizar"}
        </button>
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 16 }}>
        {offers.map((offer, i) => {
          const isFirst = i === 0
          const logo = PROVIDER_LOGOS[offer.provider] || "🏪"
          const key = offerKey(offer, i)
          return (
            <div key={key} style={{
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
                  <img src={offer.image_url} alt={offer.title} loading="lazy" fetchPriority="low"
                    style={{ width: "100%", height: 160, objectFit: "contain", borderRadius: 8, background: "#eef0ff", marginBottom: 12 }}
                    onError={e => { (e.target as HTMLImageElement).style.display = "none" }}
                  />
                )}
                <p style={{ fontSize: 13, color: "#4a4a6a", lineHeight: 1.5, marginBottom: 12, minHeight: 40 }}>
                  {offer.title?.slice(0, 80)}...
                </p>
                {typeof offer.original_price === "number" && typeof offer.final_price === "number" && offer.original_price > offer.final_price && (
                  <div style={{ fontSize: 12, color: "#475569", textDecoration: "line-through" }}>
                    R$ {offer.original_price.toFixed(2)}
                  </div>
                )}
                <div style={{ fontSize: 28, fontWeight: 900, color: "#1a1a2e", marginBottom: 4 }}>
                  R$ {offer.final_price?.toFixed(2)}
                </div>
                {offer.shipping_free && (
                  <div style={{ fontSize: 12, color: "#00e5a0", marginBottom: 12 }}>✅ Frete grátis</div>
                )}
                <a href="#" target="_blank" rel="noopener noreferrer" onClick={event => handleOfferClick(event, offer, i)}
                  style={{
                    display: "block", textAlign: "center",
                    padding: "12px", borderRadius: 10, fontWeight: 700,
                    background: isFirst ? "linear-gradient(135deg,#00e5a0,#0ea5e9)" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
                    color: isFirst ? "#000" : "#fff",
                    textDecoration: "none", fontSize: 14,
                  }}
                >
                  {openingOfferKey === key ? "Abrindo..." : "Ver oferta →"}
                </a>
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
