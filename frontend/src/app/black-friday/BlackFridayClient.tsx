"use client"

import { useState } from "react"
import type { FormEvent, MouseEvent } from "react"
import { useRouter } from "next/navigation"
import Header from "@/components/layout/Header"
import { openTrackedOffer } from "@/lib/tracking"
import { API_BASE } from "@/lib/api"
import type { DestaquesData, VerdictResult } from "./page"
import styles from "./black-friday.module.css"

const PROVIDER_LABEL: Record<string, string> = {
  mercadolivre: "Mercado Livre",
  amazon: "Amazon",
}

const VERDICT_CLASS: Record<string, string> = {
  menor_preco: styles.badgeMenor,
  abaixo_media: styles.badgeAbaixo,
  normal: styles.badgeNormal,
  acima_media: styles.badgeAcima,
  sem_historico: styles.badgeSemHistorico,
}

function fmt(v: number | null | undefined) {
  if (v === null || v === undefined) return "—"
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

// "YYYY-MM-DD" → "dd/mm"
function fmtDay(iso: string | null | undefined) {
  if (!iso) return "—"
  const [y, m, d] = iso.split("-")
  return `${d}/${m}`
}

// Percentual pt-BR: 38.9 → "38,9"
function fmtPct(v: number) {
  return v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })
}

// Abre a loja com clique registrado — mesma rota /r/{code} dos cards de oferta.
// Fallback: affiliate_url direta se o tracking falhar.
function handleOpen(e: MouseEvent<HTMLAnchorElement>, item: VerdictResult) {
  e.preventDefault()
  if (!item.affiliate_url) return
  const current = item.current_price ?? 0
  openTrackedOffer(
    {
      provider: item.provider,
      title: item.title,
      price: current,
      final_price: current,
      original_price: item.max_price,
      affiliate_url: item.affiliate_url,
      product_id: item.id,
      image_url: item.image_url ?? undefined,
      discount_percent: 0,
      coupon_discount: 0,
      cashback_percent: 0,
      shipping_price: 0,
      shipping_free: false,
      score: 0,
      is_fake_discount: false,
      economy: Math.max(0, (item.max_price ?? 0) - current),
    },
    "blackfriday"
  ).catch(() => {
    window.open(item.affiliate_url, "_blank", "noopener,noreferrer")
  })
}

function Sparkline({ points }: { points: { d: string; p: number }[] }) {
  if (!points || points.length < 2) return null
  const vals = points.map((pt) => pt.p)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  const coords = points
    .map((pt, i) => {
      const x = (i / (points.length - 1)) * 100
      const y = 30 - ((pt.p - min) / range) * 26 - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  const last = points[points.length - 1]
  const trendUp = points.length > 1 && last.p > points[0].p
  return (
    <svg
      viewBox="0 0 100 32"
      preserveAspectRatio="none"
      className={`${styles.sparkline} ${trendUp ? styles.sparkUp : styles.sparkDown}`}
      aria-hidden="true"
    >
      <polyline
        points={coords}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}

function VerdictCard({ item }: { item: VerdictResult }) {
  const badgeClass = VERDICT_CLASS[item.verdict] || VERDICT_CLASS.sem_historico
  return (
    <div className={styles.card}>
      <a
        href={item.affiliate_url}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className={styles.imageLink}
        onClick={(e) => handleOpen(e, item)}
      >
        {item.image_url ? (
          <img src={item.image_url} alt={item.title} className={styles.image} loading="lazy" />
        ) : (
          <div className={styles.imagePlaceholder}>🛍️</div>
        )}
      </a>
      <div className={styles.info}>
        <span className={`${styles.verdictBadge} ${badgeClass}`}>
          {item.verdict_label}
        </span>
        {item.rise_pct_21d !== null && item.rise_pct_21d !== undefined && (
          <span className={styles.riseBadge}>
            ⚠️ Chegou a subir {fmtPct(item.rise_pct_21d)}% nas últimas 3 semanas
          </span>
        )}
        <a
          href={item.affiliate_url}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className={styles.productTitle}
          onClick={(e) => handleOpen(e, item)}
        >
          {item.title}
        </a>
        <span className={styles.store}>
          {item.provider === "amazon" ? "📦 Amazon" : "🟡 Mercado Livre"}
        </span>
        <div className={styles.priceRow}>
          <span className={styles.priceFinal}>{fmt(item.current_price)}</span>
        </div>
        <span className={styles.statsLine}>
          Menor: {fmt(item.min_price)} ({fmtDay(item.min_date)}) · Média 30d:{" "}
          {fmt(item.median_30)} · Monitorado há {item.days_monitored} dias
        </span>
        {item.sparkline && item.sparkline.length > 1 && (
          <Sparkline points={item.sparkline} />
        )}
        <div className={styles.actions}>
          <a
            href={item.affiliate_url}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className={styles.cta}
            onClick={(e) => handleOpen(e, item)}
          >
            🛒 Ver na loja
          </a>
          <a
            href={`https://t.me/BestPriceToday_bot?start=bf_${item.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.alertBtn}
          >
            🔔 Avise-me se baixar
          </a>
        </div>
      </div>
    </div>
  )
}

export default function BlackFridayClient({
  destaques,
  initialQuery,
  initialResults,
  hasSearch,
}: {
  destaques: DestaquesData
  initialQuery: string
  initialResults: VerdictResult[]
  hasSearch: boolean
}) {
  const router = useRouter()
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<VerdictResult[]>(initialResults)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(hasSearch)

  const monitored = (destaques.monitored_products || 0).toLocaleString("pt-BR")
  const sinceLabel = fmtDay(destaques.since)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (q.length < 3) return
    setLoading(true)
    setSearched(true)
    router.replace(`/black-friday?q=${encodeURIComponent(q)}`)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/verificador?q=${encodeURIComponent(q)}&limit=12`
      )
      const data = await res.json()
      setResults(data.results ?? [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header variant="default" />
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>
            <span className={styles.titleIcon}>🔍</span>
            Esse desconto da Black Friday é real?
          </h1>
          <p className={styles.subtitle}>
            Monitoramos {monitored} produtos do Mercado Livre e da Amazon todos
            os dias desde {sinceLabel}.
          </p>
        </div>

        <form className={styles.searchForm} onSubmit={submit}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Digite o produto (ex: air fryer, fone bluetooth, tv 50)…"
            className={styles.searchInput}
            minLength={3}
            maxLength={80}
          />
          <button type="submit" className={styles.searchBtn} disabled={loading}>
            {loading ? "Verificando…" : "Verificar"}
          </button>
        </form>

        {searched && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              {results.length > 0
                ? query.trim()
                  ? `Resultado para “${query.trim()}”`
                  : "Veredito do produto"
                : loading
                  ? "Verificando…"
                  : `Nenhum produto monitorado para “${query.trim()}”`}
            </h2>
            {results.length > 0 && (
              <div className={styles.grid}>
                {results.map((item) => (
                  <VerdictCard key={item.id} item={item} />
                ))}
              </div>
            )}
          </section>
        )}

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Descontos reais verificados hoje</h2>
          {destaques.results.length === 0 ? (
            <div className={styles.empty}>
              <span className={styles.emptyIcon}>📉</span>
              <p>
                Nenhum desconto real detectado hoje. Volte amanhã — a coleta roda
                1×/dia.
              </p>
            </div>
          ) : (
            <div className={styles.grid}>
              {destaques.results.map((item) => (
                <VerdictCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>

        <p className={styles.footnote}>
          Preços coletados automaticamente 1×/dia desde {sinceLabel}. Mostramos o
          preço exibido pela loja no momento da coleta — confira o valor final
          antes de comprar. Links de afiliado: podemos receber comissão, sem
          custo extra para você.
        </p>
      </div>
    </>
  )
}
