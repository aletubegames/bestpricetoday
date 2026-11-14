import type { Metadata } from "next"
import { API_BASE, SITE_BASE } from "@/lib/api"
import BlackFridayClient from "./BlackFridayClient"

// ISR: revalida a cada 30min (histórico de preço muda 1x/dia com o scraper)
export const revalidate = 1800

export const metadata: Metadata = {
  title: "Black Friday 2026: o desconto é real? Verificador de preços | BestPriceToday",
  description:
    "Digite o produto e veja o histórico de preço real desde outubro no Mercado Livre e na Amazon. Descubra se o desconto da Black Friday é de verdade.",
  openGraph: {
    title: "Black Friday 2026: o desconto é real? | BestPriceToday",
    description:
      "Histórico de preço real desde outubro no Mercado Livre e na Amazon. Descubra se o desconto é de verdade.",
    type: "website",
    url: `${SITE_BASE}/black-friday`,
  },
  alternates: {
    canonical: `${SITE_BASE}/black-friday`,
  },
}

export interface SparkPoint {
  d: string
  p: number
}

export interface VerdictResult {
  id: string
  title: string
  image_url: string | null
  affiliate_url: string
  provider: string
  verdict: string
  verdict_label: string
  current_price: number | null
  min_price: number | null
  min_date: string | null
  max_price: number | null
  median_30: number | null
  pct_vs_median: number | null
  days_monitored: number
  first_date: string | null
  rise_pct_21d: number | null
  sparkline: SparkPoint[]
}

export interface DestaquesData {
  monitored_products: number
  since: string | null
  results: VerdictResult[]
}

async function fetchDestaques(): Promise<DestaquesData> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/verificador/destaques?limit=12`, {
      next: { revalidate: 1800 },
    })
    if (!res.ok) return { monitored_products: 0, since: null, results: [] }
    return await res.json()
  } catch {
    return { monitored_products: 0, since: null, results: [] }
  }
}

async function fetchSearch(q: string): Promise<VerdictResult[]> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/verificador?q=${encodeURIComponent(q)}&limit=12`,
      { next: { revalidate: 300 } }
    )
    if (!res.ok) return []
    const data = await res.json()
    return data.results ?? []
  } catch {
    return []
  }
}

async function fetchProduto(id: string): Promise<VerdictResult | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/verificador/produto/${encodeURIComponent(id)}`,
      { next: { revalidate: 300 } }
    )
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export default async function BlackFridayPage({
  searchParams,
}: {
  searchParams: { q?: string; p?: string }
}) {
  const q = typeof searchParams?.q === "string" ? searchParams.q.trim() : ""
  const p = typeof searchParams?.p === "string" ? searchParams.p.trim() : ""

  const [destaques, searchResults, product] = await Promise.all([
    fetchDestaques(),
    q ? fetchSearch(q) : Promise.resolve([]),
    p ? fetchProduto(p) : Promise.resolve(null),
  ])

  const initialResults = product ? [product] : searchResults
  // key força remount quando a URL muda (?q= / ?p=) — estado inicial vem das props
  const remountKey = q ? `q:${q}` : p ? `p:${p}` : "home"

  return (
    <BlackFridayClient
      key={remountKey}
      destaques={destaques}
      initialQuery={q}
      initialResults={initialResults}
      hasSearch={Boolean(q || p)}
    />
  )
}
