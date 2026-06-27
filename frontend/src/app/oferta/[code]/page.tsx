"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { API_BASE, SITE_BASE } from "@/lib/api"

interface OfferInfo {
  code: string
  product_title: string | null
  price: number | null
  original_price: number | null
  image_url: string | null
  provider: string | null
  affiliate_url: string | null
  source: string | null
}

const PROVIDER_LABELS: Record<string, { name: string; color: string; logo: string }> = {
  amazon:    { name: "Amazon",       color: "#FF9900", logo: "📦" },
  mercadolivre: { name: "Mercado Livre", color: "#FFE600", logo: "🛒" },
  shopee:    { name: "Shopee",       color: "#EE4D2D", logo: "🛍️" },
  aliexpress: { name: "AliExpress",  color: "#E62E04", logo: "🌐" },
  kabum:     { name: "KaBuM",        color: "#333333", logo: "💻" },
  magazineluiza: { name: "Magalu",   color: "#0086FF", logo: "🔵" },
  lomadee:   { name: "Lomadee",      color: "#333333", logo: "🏷️" },
}

export default function OfferPage() {
  const params = useParams()
  const code = params.code as string
  const [offer, setOffer] = useState<OfferInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    async function fetchOffer() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/r/${code}/info`)
        if (!res.ok) {
          setError(true)
          return
        }
        const data = await res.json()
        setOffer(data)
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }
    if (code) fetchOffer()
  }, [code])

  // Loading state
  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 48, height: 48, border: "4px solid #1e293b", borderTopColor: "#00e5a0", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ color: "#94a3b8", fontSize: 16 }}>Carregando oferta...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  // Error state
  if (error || !offer) {
    return (
      <div style={{ minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
        <div style={{ textAlign: "center", maxWidth: 400 }}>
          <h1 style={{ color: "#fff", fontSize: 24, marginBottom: 8 }}>Oferta não encontrada</h1>
          <p style={{ color: "#94a3b8", marginBottom: 24 }}>Esta oferta pode ter expirado ou o link está incorreto.</p>
          <a href={SITE_BASE} style={{ color: "#00e5a0", textDecoration: "underline" }}>
            Ver todas as ofertas →
          </a>
        </div>
      </div>
    )
  }

  const providerInfo = PROVIDER_LABELS[offer.provider || ""] || { name: offer.provider || "Loja", color: "#333", logo: "🏪" }
  const goUrl = `${API_BASE}/api/v1/r/${code}/go`
  const discount = offer.original_price && offer.price && offer.original_price > offer.price
    ? Math.round((1 - offer.price / offer.original_price) * 100)
    : 0

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#fff", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* Header */}
      <header style={{ borderBottom: "1px solid #1e293b", padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <a href={SITE_BASE} style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 22, fontWeight: 800, color: "#00e5a0" }}>BestPrice</span>
          <span style={{ fontSize: 22, fontWeight: 800, color: "#fff" }}>Today</span>
        </a>
        <span style={{ fontSize: 13, color: "#64748b" }}>Menor Preço do Brasil</span>
      </header>

      {/* Offer card */}
      <main style={{ maxWidth: 500, margin: "0 auto", padding: "32px 20px" }}>
        <div style={{
          background: "#1e293b",
          borderRadius: 16,
          overflow: "hidden",
          border: "1px solid #334155",
        }}>
          {/* Product image */}
          {offer.image_url && (
            <div style={{
              background: "#fff",
              padding: 20,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 200,
            }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={offer.image_url}
                alt={offer.product_title || "Produto"}
                style={{ maxHeight: 240, maxWidth: "100%", objectFit: "contain" }}
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
              />
            </div>
          )}

          {/* Content */}
          <div style={{ padding: "24px 28px" }}>
            {/* Provider badge */}
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "#0f172a",
              padding: "6px 14px",
              borderRadius: 20,
              fontSize: 13,
              color: "#94a3b8",
              marginBottom: 16,
            }}>
              <span>{providerInfo.logo}</span>
              <span>via {providerInfo.name}</span>
            </div>

            {/* Product title */}
            <h1 style={{
              fontSize: 20,
              fontWeight: 700,
              lineHeight: 1.4,
              marginBottom: 20,
              color: "#fff",
            }}>
              {offer.product_title || "Produto"}
            </h1>

            {/* Price */}
            {offer.price != null && (
              <div style={{ marginBottom: 24 }}>
                {offer.original_price && offer.original_price > offer.price && (
                  <p style={{
                    fontSize: 16,
                    color: "#64748b",
                    textDecoration: "line-through",
                    margin: "0 0 4px 0",
                  }}>
                    R$ {offer.original_price.toFixed(2).replace(".", ",")}
                  </p>
                )}
                <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                  <p style={{
                    fontSize: 32,
                    fontWeight: 800,
                    color: "#00e5a0",
                    margin: 0,
                  }}>
                    R$ {offer.price.toFixed(2).replace(".", ",")}
                  </p>
                  {discount > 0 && (
                    <span style={{
                      background: "#ef4444",
                      color: "#fff",
                      fontSize: 14,
                      fontWeight: 700,
                      padding: "4px 10px",
                      borderRadius: 8,
                    }}>
                      -{discount}%
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* CTA button */}
            <a
              href={goUrl}
              style={{
                display: "block",
                background: "#00e5a0",
                color: "#0f172a",
                fontSize: 18,
                fontWeight: 700,
                padding: "16px 32px",
                borderRadius: 12,
                textDecoration: "none",
                textAlign: "center",
                marginBottom: 16,
              }}
            >
              VER OFERTA →
            </a>

            {/* Trust signals */}
            <div style={{
              display: "flex",
              justifyContent: "center",
              gap: 16,
              fontSize: 12,
              color: "#64748b",
              marginTop: 20,
              flexWrap: "wrap",
            }}>
              <span>✅ Redirecionamento seguro</span>
              <span>✅ Sem cadastro</span>
              <span>✅ Melhor preço</span>
            </div>

            {/* Disclosure */}
            <p style={{
              fontSize: 11,
              color: "#475569",
              marginTop: 20,
              lineHeight: 1.5,
              textAlign: "center",
            }}>
              Este é um link de afiliado. Podemos receber uma comissão se você comprar, sem custo adicional para você.
            </p>
          </div>
        </div>

        {/* Footer link */}
        <div style={{ textAlign: "center", marginTop: 20 }}>
          <a href={SITE_BASE} style={{ color: "#64748b", fontSize: 14, textDecoration: "none" }}>
            ← Ver mais ofertas no BestPriceToday
          </a>
        </div>
      </main>
    </div>
  )
}
