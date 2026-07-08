import type { Metadata } from "next"
import Header from "@/components/layout/Header"
import ProductSearchClient from "./ProductSearchClient"
import { API_BASE as API, SITE_BASE } from "@/lib/api"
import type { Offer } from "@/types"
import styles from "./ProductSearch.module.css"

interface Props {
  params: { query: string }
}

// ISR: revalida a cada 30 minutos (1800s)
// As ofertas mudam ao longo do dia, mas 30min é um bom balanceamento
// entre frescor e custo de API/crawler.
export const revalidate = 1800

// Pré-busca as ofertas no server (SSR/ISR) para SEO
async function fetchOffers(query: string): Promise<{ offers: Offer[]; total: number }> {
  try {
    const res = await fetch(
      `${API}/api/v1/search?q=${encodeURIComponent(query)}&limit=40`,
      { next: { revalidate: 1800 } }
    )
    if (!res.ok) return { offers: [], total: 0 }
    const data = await res.json()
    return { offers: data.offers || [], total: data.total || 0 }
  } catch {
    return { offers: [], total: 0 }
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const q = decodeURIComponent(params.query)
  return {
    title: `${q} — Menor Preço | BestPriceToday`,
    description: `Compare preços de ${q} em AliExpress, Shopee, Mercado Livre e mais. Cupons automáticos aplicados. Economize agora!`,
    keywords: [q, "menor preço", "comparar preços", "oferta", "desconto", "afiliado"],
    openGraph: {
      title: `${q} — Menor Preço Garantido`,
      description: `Busca automática do menor preço de ${q} em todas as lojas.`,
      url: `${SITE_BASE}/produto/${params.query}`,
    },
    alternates: {
      canonical: `${SITE_BASE}/produto/${params.query}`,
    },
  }
}

export default async function ProductPage({ params }: Props) {
  const q = decodeURIComponent(params.query)

  // Busca ofertas no server (SSR/ISR) — o HTML já vem com preços
  const { offers: initialOffers, total: initialTotal } = await fetchOffers(q)

  // JSON-LD Product + Offer para SEO (rich snippets)
  // Usa o produto com menor preço (primeiro da lista)
  const bestOffer = initialOffers[0]
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": q,
    "description": `Compare preços de ${q} nas melhores lojas do Brasil`,
    "url": `${SITE_BASE}/produto/${params.query}`,
  }

  if (bestOffer) {
    jsonLd["offers"] = {
      "@type": "AggregateOffer",
      "priceCurrency": "BRL",
      "lowPrice": bestOffer.final_price || bestOffer.price || 0,
      "highPrice": initialOffers[initialOffers.length - 1]?.final_price || bestOffer.final_price || 0,
      "offerCount": initialTotal || initialOffers.length,
      "offers": initialOffers.slice(0, 10).map((o) => ({
        "@type": "Offer",
        "price": o.final_price || o.price || 0,
        "priceCurrency": "BRL",
        "availability": "https://schema.org/InStock",
        "seller": {
          "@type": "Organization",
          "name": o.provider,
        },
      })),
    }
    if (bestOffer.image_url) {
      jsonLd["image"] = bestOffer.image_url
    }
  }

  return (
    <div className={styles.root}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <Header variant="default" />

      <div className={styles.container}>
        <h1 className={styles.title}>
          Menor preço: <span className={styles.titleAccent}>{q}</span>
        </h1>
        <p className={styles.subtitle}>
          Comparação em tempo real em AliExpress, Shopee, Mercado Livre e mais lojas.
        </p>

        {/* Ofertas SSR (visíveis no HTML sem JS) + hidratação client para interação */}
        <ProductSearchClient
          query={q}
          initialOffers={initialOffers}
          initialTotal={initialTotal}
        />
      </div>
    </div>
  )
}
