"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import Header from "@/components/layout/Header"
import { API_BASE, SITE_BASE } from "@/lib/api"
import PriceHistoryPublic from "@/components/offers/PriceHistoryPublic"
import styles from "./OfferPage.module.css"

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
  is_dead?: boolean
}

interface CouponInfo {
  coupon_code: string
  store_name: string | null
  discount_text: string | null
  expires_at: string | null
}

const PROVIDERS: Record<string, { name: string; bg: string; text: string; emoji: string }> = {
  amazon: {
    name: "Amazon",
    bg: "linear-gradient(135deg, #FF9900, #FFB73D)",
    text: "#111",
    emoji: "📦",
  },
  mercadolivre: {
    name: "Mercado Livre",
    bg: "linear-gradient(135deg, #FFE600, #FFF700)",
    text: "#111",
    emoji: "🛒",
  },
  shopee: {
    name: "Shopee",
    bg: "linear-gradient(135deg, #EE4D2D, #F0633F)",
    text: "#fff",
    emoji: "🛍️",
  },
  aliexpress: {
    name: "AliExpress",
    bg: "linear-gradient(135deg, #E62E04, #FF4719)",
    text: "#fff",
    emoji: "🌐",
  },
  kabum: {
    name: "KaBuM!",
    bg: "linear-gradient(135deg, #333, #555)",
    text: "#fff",
    emoji: "💻",
  },
  magazineluiza: {
    name: "Magalu",
    bg: "linear-gradient(135deg, #0086FF, #2196F3)",
    text: "#fff",
    emoji: "🔵",
  },
  lomadee: {
    name: "Lomadee",
    bg: "linear-gradient(135deg, #7C3AED, #8B5CF6)",
    text: "#fff",
    emoji: "🏷️",
  },
  awin: {
    name: "Awin",
    bg: "linear-gradient(135deg, #60A5FA, #3B82F6)",
    text: "#fff",
    emoji: "🔗",
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
  const [reported, setReported] = useState(false)
  const [coupon, setCoupon] = useState<CouponInfo | null>(null)

  useEffect(() => {
    async function fetchOffer() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/r/${code}/info`)
        if (!res.ok) {
          setError(true)
          return
        }
        const data = await res.json()

        // Se nao tem imagem, busca da API pelo titulo
        if ((!data.image_url || data.image_url === "") && data.product_title) {
          try {
            const searchRes = await fetch(
              `${API_BASE}/api/v1/search?q=${encodeURIComponent(data.product_title.slice(0, 60))}&limit=5`
            )
            if (searchRes.ok) {
              const searchData = await searchRes.json()
              const match = searchData.offers?.find(
                (o: any) => o.affiliate_url === data.affiliate_url && o.image_url
              )
              if (match) {
                data.image_url = match.image_url
              } else if (searchData.offers?.[0]?.image_url) {
                data.image_url = searchData.offers[0].image_url
              }
            }
          } catch {
            // ignora erro de busca de imagem
          }
        }

        setOffer(data)

        // Busca cupom ativo para o provider da oferta
        if (data.provider) {
          try {
            const providerMap: Record<string, string> = {
              mercadolivre: "mercadolivre",
              amazon: "amazon",
            }
            const couponProvider = providerMap[data.provider]
            if (couponProvider) {
              const couponRes = await fetch(`${API_BASE}/api/v1/affiliate/coupons?provider=${couponProvider}&active_only=true&limit=1`)
              if (couponRes.ok) {
                const couponData = await couponRes.json()
                if (couponData.coupons?.[0]) {
                  setCoupon(couponData.coupons[0])
                }
              }
            }
          } catch {
            // ignora erro de cupom
          }
        }
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }
    if (code) fetchOffer()
  }, [code])

  async function reportDead() {
    try {
      await fetch(`${API_BASE}/api/v1/r/${code}/report-dead`, { method: "POST" })
      setReported(true)
    } catch {
      // ignora
    }
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <p style={{ color: "#64748b", fontSize: 15, marginTop: 16 }}>Buscando os detalhes da oferta...</p>
      </div>
    )
  }

  if (error || !offer) {
    return (
      <div className={styles.error}>
        <div className={styles.errorEmoji}>😕</div>
        <h2>Oferta não encontrada</h2>
        <p>Esse link expirou ou não existe. Veja outras ofertas no BestPriceToday.</p>
        <a href={SITE_BASE} className={styles.errorBtn}>Ver ofertas ativas</a>
      </div>
    )
  }

  // Oferta expirada (link quebrado reportado)
  if (offer.is_dead || reported) {
    const searchUrl = `${SITE_BASE}/?q=${encodeURIComponent(offer.product_title || "")}`
    return (
      <div className={styles.root}>
        <Header variant="minimal" />
        <main className={styles.main}>
          <div className={styles.card} style={{ textAlign: "center", padding: "48px 24px" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⏰</div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: "#1a1a2e", marginBottom: 8 }}>
              Esta oferta expirou
            </h1>
            <p style={{ fontSize: 15, color: "#64748b", marginBottom: 24, lineHeight: 1.6 }}>
              O produto <strong>{offer.product_title}</strong> não está mais disponível na loja.
              <br />
              Buscamos alternativas similares pra você:
            </p>
            <a href={searchUrl} className={styles.cta} style={{ display: "inline-flex", textDecoration: "none" }}>
              <span>🔍</span>
              <span>Buscar produtos similares</span>
              <span>→</span>
            </a>
            <div style={{ marginTop: 16 }}>
              <a href={SITE_BASE} className={styles.ctaSecondary}>
                ← Voltar para o BestPriceToday
              </a>
            </div>
          </div>
        </main>
      </div>
    )
  }

  const provider = PROVIDERS[offer.provider || ""] || {
    name: offer.provider || "Loja parceira",
    bg: "linear-gradient(135deg, #7c6aff, #a78bfa)",
    text: "#fff",
    emoji: "🏪",
  }

  const goUrl = `${API_BASE}/api/v1/r/${code}/go`
  const discount =
    offer.original_price && offer.price && offer.original_price > offer.price
      ? Math.round((1 - offer.price / offer.original_price) * 100)
      : 0
  const economy =
    offer.original_price && offer.price && offer.original_price > offer.price
      ? offer.original_price - offer.price
      : 0

  return (
    <div className={styles.root}>
      <Header variant="minimal" safeBadge="🔒 Redirecionamento seguro" />

      <main className={styles.main}>
        <div className={styles.redirectNotice}>
          <p className={styles.redirectTitle}>Você está indo para {provider.name}</p>
          <p>Confirme os dados do produto antes de continuar.</p>
        </div>

        <div className={styles.card}>
          <div className={styles.cardGrid}>
            <div className={styles.imageSection}>
              {offer.image_url && !imgError ? (
                <img
                  src={offer.image_url}
                  alt={offer.product_title || "Produto"}
                  className={styles.productImg}
                  onError={() => setImgError(true)}
                />
              ) : (
                <div className={styles.imgPlaceholder}>📦</div>
              )}
              {discount > 0 && <div className={styles.discountBadge}>-{discount}%</div>}
            </div>

            <div className={styles.infoSection}>
              <div
                className={styles.providerBadge}
                style={{ background: provider.bg, color: provider.text }}
              >
                <span>{provider.emoji}</span>
                <span>{provider.name}</span>
              </div>

              <h1 className={styles.title}>{offer.product_title || "Oferta"}</h1>

              <div className={styles.priceBlock}>
                {offer.original_price && offer.original_price > (offer.price || 0) && (
                  <p className={styles.originalPrice}>R$ {formatBRL(offer.original_price)}</p>
                )}
                <div className={styles.priceRow}>
                  <span className={styles.priceLabel}>Preço atual:</span>
                  <span className={styles.price}>R$ {formatBRL(offer.price || 0)}</span>
                </div>
                {discount > 0 && (
                  <div className={styles.discountTag}>
                    ↓ Economize R$ {formatBRL(economy)} ({discount}% OFF)
                  </div>
                )}
              </div>

              {coupon && (
                <div style={{
                  background: "linear-gradient(135deg, rgba(225,29,72,.08), rgba(225,29,72,.04))",
                  border: "1px solid rgba(225,29,72,.2)",
                  borderRadius: 12,
                  padding: "14px 16px",
                  marginBottom: 12,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}>
                  <span style={{ fontSize: 24 }}>🏷️</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 700, color: "#e11d48", margin: 0 }}>
                      Cupom disponível: {coupon.discount_text || "Desconto extra"}
                    </p>
                    <p style={{ fontSize: 12, color: "#64748b", margin: "2px 0 0 0" }}>
                      Use o código <strong style={{ color: "#e11d48", fontFamily: "monospace" }}>{coupon.coupon_code}</strong>
                      {coupon.expires_at && ` • Vence em ${new Date(coupon.expires_at).toLocaleDateString("pt-BR")}`}
                    </p>
                  </div>
                </div>
              )}

              <a
                href={goUrl}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className={styles.cta}
              >
                <span>🛒</span>
                <span>Ver oferta na {provider.name}</span>
                <span>→</span>
              </a>

              <a href={SITE_BASE} className={styles.ctaSecondary}>
                ← Voltar para o BestPriceToday
              </a>

              {(offer.provider === "mercadolivre" || offer.provider === "amazon") && offer.affiliate_url && (
                <PriceHistoryPublic affiliateUrl={offer.affiliate_url} />
              )}

              <p className={styles.disclosure}>
                O BestPriceToday compara preços em tempo real pra você economizar de verdade.
                Ao clicar em "Ver oferta", você vai direto pro site oficial da loja com o menor
                preço já garantido. Use nosso link — assim fortalecemos a parceria com as lojas
                e mantemos o serviço 100% gratuito pra você.
              </p>

              <button
                onClick={reportDead}
                style={{
                  marginTop: 12, background: "none", border: "none", cursor: "pointer",
                  color: "#94a3b8", fontSize: 12, textDecoration: "underline", padding: 0,
                }}
              >
                {reported ? "✓ Obrigado! Vamos verificar." : "Link quebrado? Avise-nos"}
              </button>
            </div>
          </div>
        </div>
      </main>

      <footer className={styles.footer}>
        <p>BestPriceToday — Comparação de preços em tempo real</p>
      </footer>
    </div>
  )
}
