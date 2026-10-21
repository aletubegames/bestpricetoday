import type { Metadata } from "next"
import { SITE_BASE } from "@/lib/api"
import CuponsClient from "./CuponsClient"

export const metadata: Metadata = {
  title: "Cupons Mercado Livre — descontos ativos hoje | BestPriceToday",
  description:
    "Todos os cupons de desconto do Mercado Livre ativos agora: percentuais OFF, cupons de loja e frete. Atualizado diariamente.",
  openGraph: {
    title: "🏷️ Cupons Mercado Livre ativos hoje",
    description:
      "Centenas de cupons de desconto ativos no Mercado Livre — ative na sua conta e economize no checkout.",
    url: `${SITE_BASE}/cupons`,
    type: "website",
  },
  alternates: {
    canonical: `${SITE_BASE}/cupons`,
  },
}

export default function CuponsPage() {
  return <CuponsClient />
}
