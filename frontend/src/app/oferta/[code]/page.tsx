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
  clicks: number | null
}

const PROVIDERS: Record<string, { name: string; bg: string; text: string; emoji: string; rating: string; trust: string }> = {
  amazon: {
    name: "Amazon",
    bg: "linear-gradient(135deg, #FF9900, #FFB73D)",
    text: "#111",
    emoji: "📦",
    rating: "4.8",
    trust: "Amazon Prime · Entrega garantida"
  },
  mercadolivre: {
    name: "Mercado Livre",
    bg: "linear-gradient(135deg, #FFE600, #FFF700)",
    text: "#111",
    emoji: "🛒",
    rating: "4.7",
    trust: "Mercado Pago · Compra protegida"
  },
  shopee: {
    name: "Shopee",
    bg: "linear-gradient(135deg, #EE4D2D, #F0633F)",
    text: "#fff",
    emoji: "🛍️",
    rating: "4.6",
    trust: "Shopee Guarantee · Reembolso garantido"
  },
  aliexpress: {
    name: "AliExpress",
    bg: "linear-gradient(135deg, #E62E04, #FF4719)",
    text: "#fff",
    emoji: "🌐",
    rating: "4.5",
    trust: "Buyer Protection · Reembolso em 15 dias"
  },
  kabum: {
    name: "KaBuM!",
    bg: "linear-gradient(135deg, #333, #555)",
    text: "#fff",
    emoji: "💻",
    rating: "4.7",
    trust: "Nota fiscal · Garantia oficial"
  },
  magazineluiza: {
    name: "Magalu",
    bg: "linear-gradient(135deg, #0086FF, #2196F3)",
    text: "#fff",
    emoji: "🔵",
    rating: "4.8",
    trust: "Magalu Entrega · Compra segura"
  },
  lomadee: {
    name: "Lomadee",
    bg: "linear-gradient(135deg, #333, #555)",
    text: "#fff",
    emoji: "🏷️",
    rating: "4.5",
    trust: "Lojas verificadas"
  },
}

function formatBRL(v: number) {
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function OfferPage() {
  const params = useParams()
  const code = params.code as string
  const [offer, setOffer] = useState<OfferInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [imgError, setImgError] = useState(false)
  const [timeLeft, setTimeLeft] = useState({ h: 23, m: 59, s: 59 })

  useEffect(() => {
    async function fetchOffer() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/r/${code}/info`)
        if (!res.ok) { setError(true); return }
        const data = await res.json()
        setOffer(data)
      } catch { setError(true) }
      finally { setLoading(false) }
    }
    if (code) fetchOffer()
  }, [code])

  // Countdown timer (cria urgência — oferta do dia)
  useEffect(() => {
    if (!offer) return
    const interval = setInterval(() => {
      setTimeLeft(prev => {
        let { h, m, s } = prev
        s--
        if (s < 0) { s = 59; m-- }
        if (m < 0) { m = 59; h-- }
        if (h < 0) { h = 0; m = 0; s = 0 }
        return { h, m, s }
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [offer])

  if (loading) {
    return (
      <div style={styles.loading}>
        <div style={styles.spinner} />
        <p style={{ color: "#94a3b8", fontSize: 15, marginTop: 16 }}>Buscando a melhor oferta...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  if (error || !offer) {
    return (
      <div style={styles.errorPage}>
        <div style={styles.errorCard}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>😕</div>
          <h1 style={{ color: "#fff", fontSize: 22, marginBottom: 8 }}>Oferta expirada</h1>
          <p style={{ color: "#94a3b8", marginBottom: 24 }}>Esta oferta já terminou, mas temos milhares de outras!</p>
          <a href={SITE_BASE} style={styles.errorBtn}>Ver ofertas ativas →</a>
        </div>
      </div>
    )
  }

  const p = PROVIDERS[offer.provider || ""] || {
    name: offer.provider || "Loja verificada",
    bg: "linear-gradient(135deg, #1e293b, #334155)",
    text: "#fff",
    emoji: "🏪",
    rating: "4.5",
    trust: "Loja verificada"
  }

  const goUrl = `${API_BASE}/api/v1/r/${code}/go`
  const discount = offer.original_price && offer.price && offer.original_price > offer.price
    ? Math.round((1 - offer.price / offer.original_price) * 100)
    : 0
  const economy = offer.original_price && offer.price && offer.original_price > offer.price
    ? offer.original_price - offer.price
    : 0
  const today = new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "long" })

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <a href={SITE_BASE} style={styles.logoLink}>
          <span style={styles.logoGreen}>BestPrice</span>
          <span style={styles.logoWhite}>Today</span>
        </a>
        <div style={styles.headerRight}>
          <span style={styles.headerBadge}>✓ Site seguro</span>
        </div>
      </header>

      {/* Urgency banner */}
      <div style={styles.urgencyBar}>
        <span>🔥 OFERTA DO DIA — {today}</span>
        <span style={styles.timer}>
          ⏰ Termina em {String(timeLeft.h).padStart(2, "0")}:{String(timeLeft.m).padStart(2, "0")}:{String(timeLeft.s).padStart(2, "0")}
        </span>
      </div>

      {/* Main content */}
      <main style={styles.main}>
        <div style={styles.card}>
          {/* Two columns: image + info */}
          <div style={styles.cardGrid}>
            {/* Left: Product image */}
            <div style={styles.imageSection}>
              {offer.image_url && !imgError ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={offer.image_url}
                  alt={offer.product_title || "Produto"}
                  style={styles.productImg}
                  onError={() => setImgError(true)}
                />
              ) : (
                <div style={styles.imgPlaceholder}>📦</div>
              )}
              {discount > 0 && (
                <div style={styles.discountBadge}>-{discount}%</div>
              )}
            </div>

            {/* Right: Product info */}
            <div style={styles.infoSection}>
              {/* Provider badge */}
              <div style={{ ...styles.providerBadge, background: p.bg, color: p.text }}>
                <span style={{ fontSize: 16 }}>{p.emoji}</span>
                <span style={{ fontWeight: 600 }}>{p.name}</span>
                <span style={{ opacity: 0.8, fontSize: 12 }}>★ {p.rating}</span>
              </div>

              {/* Title */}
              <h1 style={styles.title}>{offer.product_title || "Produto"}</h1>

              {/* Rating stars */}
              <div style={styles.stars}>
                {"★★★★★".split("").map((s, i) => (
                  <span key={i} style={{ color: i < 4 ? "#FFD700" : "#475569", fontSize: 18 }}>{s}</span>
                ))}
                <span style={{ color: "#64748b", fontSize: 13, marginLeft: 8 }}>
                  (4.{Math.floor(Math.random() * 9) + 1} · {Math.floor(Math.random() * 500) + 120} avaliações)
                </span>
              </div>

              {/* Price block */}
              <div style={styles.priceBlock}>
                {offer.original_price && offer.original_price > (offer.price || 0) && (
                  <p style={styles.priceOriginal}>R$ {formatBRL(offer.original_price)}</p>
                )}
                <div style={styles.priceRow}>
                  <span style={styles.priceLabel}>à vista</span>
                  <span style={styles.price}>R$ {formatBRL(offer.price || 0)}</span>
                </div>
                {discount > 0 && (
                  <div style={styles.discountTag}>
                    Economize R$ {formatBRL(economy)} ({discount}% OFF)
                  </div>
                )}
                <p style={styles.priceNote}>ou 12x sem juros no cartão</p>
              </div>

              {/* CTA button */}
              <a href={goUrl} style={styles.ctaBtn}>
                <span style={{ fontSize: 20 }}>🛒</span>
                <span>VER OFERTA NA {p.name.toUpperCase()}</span>
                <span style={{ fontSize: 20 }}>→</span>
              </a>

              {/* Trust indicators */}
              <div style={styles.trustGrid}>
                <div style={styles.trustItem}>
                  <span style={styles.trustIcon}>🔒</span>
                  <div>
                    <p style={styles.trustTitle}>Compra Segura</p>
                    <p style={styles.trustDesc}>Site oficial da loja</p>
                  </div>
                </div>
                <div style={styles.trustItem}>
                  <span style={styles.trustIcon}>✅</span>
                  <div>
                    <p style={styles.trustTitle}>Loja Verificada</p>
                    <p style={styles.trustDesc}>{p.trust}</p>
                  </div>
                </div>
                <div style={styles.trustItem}>
                  <span style={styles.trustIcon}>🚚</span>
                  <div>
                    <p style={styles.trustTitle}>Entrega Rápida</p>
                    <p style={styles.trustDesc}>Frete grátis disponível</p>
                  </div>
                </div>
                <div style={styles.trustItem}>
                  <span style={styles.trustIcon}>↩️</span>
                  <div>
                    <p style={styles.trustTitle}>Devolução Grátis</p>
                    <p style={styles.trustDesc}>7 dias para trocar</p>
                  </div>
                </div>
              </div>

              {/* Disclosure */}
              <p style={styles.disclosure}>
                ℹ️ BestPriceToday é um comparador de preços. Ao clicar em "Ver Oferta", você será
                direcionado para o site oficial da loja, onde pode comprar com segurança.
                Podemos receber uma comissão pela indicação, sem custo adicional para você.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom: more offers */}
        <div style={styles.bottomLinks}>
          <a href={SITE_BASE} style={styles.bottomLink}>
            ← Ver mais ofertas no BestPriceToday
          </a>
          <a href={`${SITE_BASE}/search`} style={styles.bottomLink}>
            Comparar preços de outros produtos →
          </a>
        </div>
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        <p>BestPriceToday — Menor Preço do Brasil · Comparação de preços em tempo real</p>
      </footer>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#0a0f1e",
    color: "#fff",
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    display: "flex",
    flexDirection: "column",
  },
  loading: {
    minHeight: "100vh",
    background: "#0a0f1e",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
  },
  spinner: {
    width: 48, height: 48,
    border: "4px solid #1e293b",
    borderTopColor: "#00e5a0",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  errorPage: {
    minHeight: "100vh",
    background: "#0a0f1e",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  errorCard: {
    textAlign: "center",
    maxWidth: 400,
  },
  errorBtn: {
    display: "inline-block",
    background: "#00e5a0",
    color: "#0a0f1e",
    padding: "12px 28px",
    borderRadius: 10,
    textDecoration: "none",
    fontWeight: 700,
    fontSize: 16,
  },
  header: {
    borderBottom: "1px solid #1e293b",
    padding: "14px 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    position: "sticky",
    top: 0,
    background: "#0a0f1e",
    zIndex: 10,
  },
  logoLink: { textDecoration: "none", display: "flex", alignItems: "center", gap: 2 },
  logoGreen: { fontSize: 22, fontWeight: 800, color: "#00e5a0" },
  logoWhite: { fontSize: 22, fontWeight: 800, color: "#fff" },
  headerRight: { display: "flex", gap: 12, alignItems: "center" },
  headerBadge: {
    fontSize: 12,
    color: "#00e5a0",
    background: "rgba(0, 229, 160, 0.1)",
    padding: "4px 12px",
    borderRadius: 20,
    border: "1px solid rgba(0, 229, 160, 0.2)",
  },
  urgencyBar: {
    background: "linear-gradient(90deg, #ef4444, #f97316)",
    padding: "10px 24px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 24,
    fontSize: 14,
    fontWeight: 600,
    color: "#fff",
    flexWrap: "wrap",
  },
  timer: {
    fontVariantNumeric: "tabular-nums",
    background: "rgba(0,0,0,0.2)",
    padding: "2px 10px",
    borderRadius: 6,
  },
  main: {
    flex: 1,
    maxWidth: 800,
    margin: "0 auto",
    padding: "32px 20px",
    width: "100%",
  },
  card: {
    background: "#111827",
    borderRadius: 20,
    overflow: "hidden",
    border: "1px solid #1e293b",
    boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
  },
  cardGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 0,
  },
  imageSection: {
    background: "#fff",
    padding: 32,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 320,
    position: "relative",
  },
  productImg: {
    maxHeight: 320,
    maxWidth: "100%",
    objectFit: "contain",
  },
  imgPlaceholder: { fontSize: 80, opacity: 0.3 },
  discountBadge: {
    position: "absolute",
    top: 16,
    right: 16,
    background: "#ef4444",
    color: "#fff",
    fontSize: 20,
    fontWeight: 800,
    padding: "8px 16px",
    borderRadius: 12,
    boxShadow: "0 4px 12px rgba(239, 68, 68, 0.4)",
  },
  infoSection: {
    padding: "28px 32px",
    display: "flex",
    flexDirection: "column",
  },
  providerBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 14px",
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 600,
    alignSelf: "flex-start",
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    lineHeight: 1.35,
    marginBottom: 12,
    color: "#fff",
    margin: "0 0 12px 0",
  },
  stars: {
    display: "flex",
    alignItems: "center",
    gap: 2,
    marginBottom: 20,
  },
  priceBlock: {
    background: "#0a0f1e",
    borderRadius: 12,
    padding: "16px 20px",
    marginBottom: 20,
    border: "1px solid #1e293b",
  },
  priceOriginal: {
    fontSize: 15,
    color: "#64748b",
    textDecoration: "line-through",
    margin: "0 0 4px 0",
  },
  priceRow: {
    display: "flex",
    alignItems: "baseline",
    gap: 8,
  },
  priceLabel: {
    fontSize: 13,
    color: "#94a3b8",
  },
  price: {
    fontSize: 34,
    fontWeight: 800,
    color: "#00e5a0",
    fontVariantNumeric: "tabular-nums",
  },
  discountTag: {
    display: "inline-block",
    background: "rgba(239, 68, 68, 0.15)",
    color: "#f87171",
    fontSize: 13,
    fontWeight: 600,
    padding: "4px 10px",
    borderRadius: 6,
    marginTop: 8,
  },
  priceNote: {
    fontSize: 12,
    color: "#64748b",
    margin: "8px 0 0 0",
  },
  ctaBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    background: "linear-gradient(135deg, #00e5a0, #00c896)",
    color: "#0a0f1e",
    fontSize: 17,
    fontWeight: 800,
    padding: "18px 28px",
    borderRadius: 14,
    textDecoration: "none",
    textAlign: "center",
    marginBottom: 24,
    boxShadow: "0 8px 24px rgba(0, 229, 160, 0.3)",
    transition: "transform 0.15s, box-shadow 0.15s",
    letterSpacing: 0.3,
  },
  trustGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginBottom: 20,
  },
  trustItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "10px 12px",
    background: "#0a0f1e",
    borderRadius: 10,
    border: "1px solid #1e293b",
  },
  trustIcon: { fontSize: 20, flexShrink: 0 },
  trustTitle: { fontSize: 13, fontWeight: 600, color: "#e2e8f0", margin: "0 0 2px 0" },
  trustDesc: { fontSize: 11, color: "#64748b", margin: 0, lineHeight: 1.4 },
  disclosure: {
    fontSize: 11,
    color: "#475569",
    lineHeight: 1.6,
    padding: "12px 16px",
    background: "#0a0f1e",
    borderRadius: 8,
    border: "1px solid #1e293b",
    margin: 0,
  },
  bottomLinks: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: 20,
    flexWrap: "wrap",
    gap: 12,
  },
  bottomLink: {
    color: "#64748b",
    fontSize: 14,
    textDecoration: "none",
    padding: "8px 0",
  },
  footer: {
    borderTop: "1px solid #1e293b",
    padding: "16px 24px",
    textAlign: "center",
  },
}

// Responsive
if (typeof window !== "undefined") {
  const style = document.createElement("style")
  style.textContent = `
    @media (max-width: 640px) {
      .cardGrid { grid-template-columns: 1fr !important; }
      .imageSection { min-height: 240px !important; padding: 20px !important; }
      .infoSection { padding: 20px !important; }
      .trustGrid { grid-template-columns: 1fr !important; }
      .price { font-size: 28px !important; }
      .ctaBtn { font-size: 15px !important; padding: 16px !important; }
    }
  `
  document.head.appendChild(style)
}
