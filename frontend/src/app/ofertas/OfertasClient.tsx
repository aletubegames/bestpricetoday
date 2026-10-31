"use client"

import { useState } from "react"
import Link from "next/link"
import { Search, Send, Tag } from "lucide-react"
import Header from "@/components/layout/Header"
import styles from "./ofertas.module.css"

export interface SocialOffer {
  code: string
  title: string
  provider: string | null
  price: number | null
  image_url: string | null
  created_at: string | null
  source: string
  url: string
}

const CHANNEL_LABELS: Record<string, string> = {
  all: "Todas",
  youtube: "YouTube",
  instagram: "Instagram",
  facebook: "Facebook",
  telegram: "Telegram",
}
const CHANNELS = ["all", "youtube", "instagram", "facebook", "telegram"]

const PROVIDER_LABEL: Record<string, string> = {
  mercadolivre: "Mercado Livre",
  amazon: "Amazon",
  shopee: "Shopee",
  aliexpress: "AliExpress",
  lomadee: "Lomadee",
  kabum: "KaBuM!",
  awin: "Awin",
}

function fmtPrice(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

function fmtDate(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "America/Sao_Paulo",
  })
}

export default function OfertasClient({
  offers,
  channel,
  fetchOk,
}: {
  offers: SocialOffer[]
  channel: string
  fetchOk: boolean
}) {
  const [query, setQuery] = useState("")
  const q = query.trim().toLowerCase()
  const filtered = q
    ? offers.filter((o) => o.title.toLowerCase().includes(q))
    : offers

  return (
    <>
      <Header variant="default" />
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Ofertas das redes</h1>
          <p className={styles.subtitle}>
            Links recentes preparados para divulgação nas nossas redes sociais.
          </p>
        </div>

        <div className={styles.channelBar}>
          {CHANNELS.map((c) => (
            <Link
              key={c}
              href={`/ofertas?canal=${c}`}
              className={`${styles.channelChip} ${channel === c ? styles.channelChipActive : ""}`}
            >
              {CHANNEL_LABELS[c]}
            </Link>
          ))}
        </div>

        <div className={styles.searchBox}>
          <Search size={16} className={styles.searchIcon} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar pelo nome do produto..."
            className={styles.searchInput}
            aria-label="Buscar oferta pelo nome do produto"
          />
        </div>

        {!fetchOk ? (
          <div className={styles.empty}>
            <h2>Ofertas indisponíveis no momento</h2>
            <p>Não foi possível carregar a lista agora. Tente novamente em instantes.</p>
          </div>
        ) : offers.length === 0 ? (
          <div className={styles.empty}>
            <h2>Nenhuma oferta recente</h2>
            <p>Ainda não há links preparados para divulgação neste canal. Volte em breve.</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className={styles.empty}>
            <h2>Nenhum resultado</h2>
            <p>Nenhuma oferta corresponde à busca “{query}”.</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {filtered.map((offer) => {
              const date = fmtDate(offer.created_at)
              return (
                <div key={offer.code} className={styles.card}>
                  <a
                    href={offer.url}
                    target="_blank"
                    rel="noopener noreferrer sponsored"
                    className={styles.imageLink}
                  >
                    {offer.image_url ? (
                      <img
                        src={offer.image_url}
                        alt={offer.title}
                        className={styles.image}
                        loading="lazy"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none"
                        }}
                      />
                    ) : (
                      <div className={styles.imagePlaceholder}>
                        <Tag size={28} />
                      </div>
                    )}
                  </a>
                  <div className={styles.info}>
                    <a
                      href={offer.url}
                      target="_blank"
                      rel="noopener noreferrer sponsored"
                      className={styles.productTitle}
                    >
                      {offer.title}
                    </a>
                    {offer.provider && (
                      <span className={styles.provider}>
                        {PROVIDER_LABEL[offer.provider] || offer.provider}
                      </span>
                    )}
                    {offer.price != null && (
                      <span className={styles.price}>{fmtPrice(offer.price)}</span>
                    )}
                    {date && (
                      <span className={styles.priceDate}>
                        {offer.price != null
                          ? `Preço informado em ${date}`
                          : `Adicionado em ${date}`}
                      </span>
                    )}
                    <a
                      href={offer.url}
                      target="_blank"
                      rel="noopener noreferrer sponsored"
                      className={styles.cta}
                    >
                      Ver oferta
                    </a>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <p className={styles.disclaimer}>
          Preços, estoque e elegibilidade podem variar — confira sempre o valor
          final na loja antes de comprar.
        </p>

        <div className={styles.socialLinks}>
          <a
            href="https://t.me/bestpricetodayBr"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.socialLink}
          >
            <Send size={15} /> Canal no Telegram
          </a>
          <Link href="/cupons" className={styles.socialLink}>
            <Tag size={15} /> Cupons ativos
          </Link>
        </div>
      </div>
    </>
  )
}
