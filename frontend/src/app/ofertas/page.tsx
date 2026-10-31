import type { Metadata } from "next"
import { API_BASE, SITE_BASE } from "@/lib/api"
import OfertasClient, { type SocialOffer } from "./OfertasClient"

const CHANNELS = ["all", "youtube", "instagram", "facebook", "telegram"] as const
type Channel = (typeof CHANNELS)[number]

export const metadata: Metadata = {
  title: "Ofertas das redes — links recentes | BestPriceToday",
  description:
    "Links recentes preparados para divulgação nas redes sociais do BestPriceToday. Encontre a oferta pelo nome do produto e confira o preço na loja.",
  openGraph: {
    title: "Ofertas das redes | BestPriceToday",
    description:
      "Links recentes de ofertas compartilhadas nas redes do BestPriceToday — procure pelo nome do produto.",
    url: `${SITE_BASE}/ofertas`,
    type: "website",
  },
  alternates: {
    canonical: `${SITE_BASE}/ofertas`,
  },
}

async function fetchSocialOffers(channel: Channel): Promise<{ offers: SocialOffer[]; ok: boolean }> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/links/social?channel=${channel}&limit=40`,
      { cache: "no-store" }
    )
    if (!res.ok) return { offers: [], ok: false }
    const data = await res.json()
    return { offers: Array.isArray(data?.offers) ? data.offers : [], ok: true }
  } catch {
    return { offers: [], ok: false }
  }
}

export default async function OfertasPage({
  searchParams,
}: {
  searchParams: { canal?: string }
}) {
  const raw = searchParams?.canal
  const channel: Channel = CHANNELS.includes(raw as Channel) ? (raw as Channel) : "all"
  const { offers, ok } = await fetchSocialOffers(channel)
  return <OfertasClient offers={offers} channel={channel} fetchOk={ok} />
}
