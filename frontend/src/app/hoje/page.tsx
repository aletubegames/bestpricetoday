import type { Metadata } from "next"
import { API_BASE, SITE_BASE } from "@/lib/api"
import HojeClient from "./HojeClient"

// ISR: revalida a cada 30min (as quedas de preço mudam com o scraper diário)
export const revalidate = 1800

export const metadata: Metadata = {
  title: "Ofertas de Hoje — menores preços em 30 dias | BestPriceToday",
  description:
    "As maiores quedas de preço reais de hoje no Mercado Livre e Amazon — comparadas com o histórico de 30 dias, não com preço inflado de loja.",
  openGraph: {
    title: "🔥 Ofertas de Hoje — menores preços em 30 dias",
    description:
      "Quedas de preço reais medidas pelo histórico de 30 dias. Ofertas novas todos os dias.",
    type: "website",
  },
  alternates: {
    canonical: `${SITE_BASE}/hoje`,
  },
}

export interface TodayOffer {
  id: string
  title: string
  price: number
  final_price: number
  original_price: number | null
  discount_percent: number
  economy: number
  affiliate_url: string
  image_url: string | null
  category: string | null
  provider: string
  store: string
  ml_code: string | null
}

async function fetchTodayOffers(): Promise<TodayOffer[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/offers/today?limit=12`, {
      next: { revalidate: 1800 },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.offers ?? []
  } catch {
    return []
  }
}

export default async function HojePage() {
  const offers = await fetchTodayOffers()
  return <HojeClient offers={offers} />
}
