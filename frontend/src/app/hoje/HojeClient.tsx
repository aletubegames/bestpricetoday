"use client"

import type { MouseEvent } from "react"
import Header from "@/components/layout/Header"
import { openTrackedOffer } from "@/lib/tracking"
import type { TodayOffer } from "./page"
import styles from "./hoje.module.css"

const PROVIDER_EMOJI: Record<string, string> = {
  mercadolivre: "🟡",
  amazon: "📦",
}

const PROVIDER_LABEL: Record<string, string> = {
  mercadolivre: "Mercado Livre",
  amazon: "Amazon",
}

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

// Abre a loja com clique registrado — mesma rota /r/{code} dos cards de oferta.
// Fallback: affiliate_url direta se o tracking falhar (já carrega matt_* do ML).
function handleOpen(e: MouseEvent<HTMLAnchorElement>, offer: TodayOffer) {
  e.preventDefault()
  if (!offer.affiliate_url) return
  openTrackedOffer(
    {
      provider: offer.provider,
      title: offer.title,
      price: offer.final_price,
      final_price: offer.final_price,
      original_price: offer.original_price,
      affiliate_url: offer.affiliate_url,
      product_id: offer.id,
      image_url: offer.image_url ?? undefined,
      discount_percent: offer.discount_percent,
      coupon_discount: 0,
      cashback_percent: 0,
      shipping_price: 0,
      shipping_free: false,
      score: 0,
      is_fake_discount: false,
      economy: offer.economy,
    },
    "hoje"
  ).catch(() => {
    window.open(offer.affiliate_url, "_blank", "noopener,noreferrer")
  })
}

export default function HojeClient({ offers }: { offers: TodayOffer[] }) {
  const hoje = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  })

  return (
    <>
      <Header variant="default" />
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>
            <span className={styles.titleIcon}>🔥</span>
            Ofertas de Hoje
          </h1>
          <p className={styles.subtitle}>
            {hoje} — quedas de preço reais vs. o maior preço dos últimos 30 dias
          </p>
        </div>

        {offers.length === 0 ? (
          <div className={styles.empty}>
            <span className={styles.emptyIcon}>🔍</span>
            <p>Nenhuma queda de preço detectada hoje. Volte mais tarde!</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {offers.map((offer) => (
              <div key={offer.id} className={styles.card}>
                {offer.discount_percent > 0 && (
                  <span className={styles.discountBadge}>
                    -{offer.discount_percent}%
                  </span>
                )}
                <a
                  href={offer.affiliate_url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className={styles.imageLink}
                  onClick={(e) => handleOpen(e, offer)}
                >
                  {offer.image_url ? (
                    <img
                      src={offer.image_url}
                      alt={offer.title}
                      className={styles.image}
                      loading="lazy"
                    />
                  ) : (
                    <div className={styles.imagePlaceholder}>🛍️</div>
                  )}
                </a>
                <div className={styles.info}>
                  <a
                    href={offer.affiliate_url}
                    target="_blank"
                    rel="noopener noreferrer sponsored"
                    className={styles.productTitle}
                    onClick={(e) => handleOpen(e, offer)}
                  >
                    {offer.title}
                  </a>
                  <span className={styles.store}>
                    {PROVIDER_EMOJI[offer.provider] || "🏪"}{" "}
                    {PROVIDER_LABEL[offer.provider] || offer.store}
                  </span>
                  <div className={styles.priceRow}>
                    {offer.original_price &&
                      offer.original_price > offer.final_price && (
                        <span className={styles.priceOriginal}>
                          {fmt(offer.original_price)}
                        </span>
                      )}
                    <span className={styles.priceFinal}>
                      {fmt(offer.final_price)}
                    </span>
                  </div>
                  {offer.economy > 0 && (
                    <span className={styles.economy}>
                      💰 economize {fmt(offer.economy)} vs. pico de 30d
                    </span>
                  )}
                  <a
                    href={offer.affiliate_url}
                    target="_blank"
                    rel="noopener noreferrer sponsored"
                    className={styles.cta}
                    onClick={(e) => handleOpen(e, offer)}
                  >
                    🛒 Ver oferta
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        <p className={styles.footnote}>
          Curadoria automática: só produtos com queda real de preço medida pelo
          histórico dos últimos 30 dias. Atualizado a cada 30 minutos.
        </p>
      </div>
    </>
  )
}
