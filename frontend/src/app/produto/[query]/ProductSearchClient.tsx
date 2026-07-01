"use client"
import { useCallback, useState } from "react"
import type { MouseEvent } from "react"
import Image from "next/image"
import { API_BASE as API, apiFetch } from "@/lib/api"
import { openTrackedOffer } from "@/lib/tracking"
import type { Offer } from "@/types"
import PriceHistoryPublic from "@/components/offers/PriceHistoryPublic"
import styles from "./ProductSearch.module.css"

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
    <div className={styles.empty}>
      <p className={styles.emptyEmoji}>😕</p>
      <p>Nenhum resultado encontrado para &quot;{query}&quot;.</p>
      <a href="/" className={styles.emptyBack}>← Voltar para busca</a>
    </div>
  )

  return (
    <div>
      <p className={styles.meta}>
        <span>
          <strong className={styles.metaCount}>{total}</strong> oferta{total !== 1 ? "s" : ""} encontrada{total !== 1 ? "s" : ""}
        </span>
        <button
          onClick={refetch}
          disabled={loading}
          className={styles.refreshBtn}
        >
          {loading ? "Atualizando..." : "↻ Atualizar"}
        </button>
      </p>
      <div className={`cq ${styles.grid}`}>
        {offers.map((offer, i) => {
          const isFirst = i === 0
          const logo = PROVIDER_LOGOS[offer.provider] || "🏪"
          const key = offerKey(offer, i)
          return (
            <div key={key} className={`${styles.card} ${isFirst ? styles.cardBest : ""}`}>
              {isFirst && <div className={styles.cardBestBar} />}
              <div className={styles.cardBody}>
                {isFirst && (
                  <div className={styles.cardBestLabel}>
                    ✓ MENOR PREÇO
                  </div>
                )}
                <div className={styles.cardHeader}>
                  <span className={styles.cardLogo}>{logo}</span>
                  <span className={styles.cardProvider}>
                    {offer.provider}
                  </span>
                  {offer.discount_percent >= 5 && !offer.is_fake_discount && (
                    <span className={styles.cardDiscount}>
                      -{Math.round(offer.discount_percent)}%
                    </span>
                  )}
                </div>
                {offer.image_url && (
                  <div className={styles.cardImage}>
                    <Image src={offer.image_url} alt={offer.title} fill
                      sizes="(max-width: 479px) 50vw, (max-width: 768px) 33vw, 25vw"
                      style={{ objectFit: "contain" }}
                      loading="lazy"
                    />
                  </div>
                )}
                <p className={styles.cardTitle}>
                  {offer.title?.slice(0, 80)}...
                </p>
                {typeof offer.original_price === "number" && typeof offer.final_price === "number" && offer.original_price > offer.final_price && (
                  <div className={styles.cardOriginalPrice}>
                    R$ {offer.original_price.toFixed(2)}
                  </div>
                )}
                <div className={styles.cardPrice}>
                  R$ {offer.final_price?.toFixed(2)}
                </div>
                {offer.shipping_free && (
                  <div className={styles.cardFreeShip}>✅ Frete grátis</div>
                )}
                <a href="#" target="_blank" rel="noopener noreferrer sponsored" onClick={event => handleOfferClick(event, offer, i)}
                  className={`${styles.cardCta} ${isFirst ? styles.cardCtaBest : ""}`}
                >
                  {openingOfferKey === key ? "Abrindo..." : "Ver oferta →"}
                </a>
                {(offer.provider === "mercadolivre" || offer.provider === "amazon") && offer.affiliate_url && (
                  <PriceHistoryPublic affiliateUrl={offer.affiliate_url} compact />
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Internal links for SEO */}
      <div className={styles.related}>
        <p className={styles.relatedTitle}>Buscas relacionadas:</p>
        <div className={styles.relatedList}>
          {[`${query} barato`, `${query} oferta`, `${query} desconto`, `melhor ${query}`].map(s => (
            <a key={s} href={`/produto/${encodeURIComponent(s)}`}
              className={styles.relatedLink}>
              {s}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
