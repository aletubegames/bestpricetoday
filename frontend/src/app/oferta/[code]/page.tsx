"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { API_BASE, SITE_BASE } from "@/lib/api"
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
      <meta name="robots" content="noindex, nofollow" />

      <header className={styles.header}>
        <div className={styles.headerInner}>
          <a href={SITE_BASE} className={styles.logo}>
            <span className={styles.logoBest}>BestPrice</span>
            <span className={styles.logoAccent}>Today</span>
          </a>
          <span className={styles.safeBadge}>🔒 Redirecionamento seguro</span>
        </div>
      </header>

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

              <p className={styles.disclosure}>
                O BestPriceToday é um comparador de preços. Ao clicar em "Ver oferta", você será
                direcionado para o site oficial da loja parceira. Podemos receber uma comissão
                pela indicação, sem nenhum custo adicional para você.
              </p>
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
