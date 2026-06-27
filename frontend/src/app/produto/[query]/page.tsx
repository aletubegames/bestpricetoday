import type { Metadata } from "next"
import ProductSearchClient from "./ProductSearchClient"
import { API_BASE as API, SITE_BASE } from "@/lib/api"
import type { Offer } from "@/types"

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
    <div style={{ minHeight: "100vh", background: "#f0f4ff", color: "#1a1a2e", fontFamily: "system-ui" }}>
      <script type="application/ld+json">
        {JSON.stringify(jsonLd)}
      </script>

      {/* Header */}
      <header style={{ borderBottom: "1px solid rgba(108,92,231,0.2)", padding: "16px 24px", background: "rgba(255,255,255,0.97)" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", alignItems: "center", gap: 12 }}>
          <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 24 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 17, color: "#7c6aff" }}>BestPriceToday</span>
          </a>
        </div>
      </header>

      <div style={{ maxWidth: 1600, margin: "0 auto", padding: "40px 16px" }}>
        <h1 style={{ fontSize: "clamp(1.5rem,4vw,2.5rem)", fontWeight: 900, marginBottom: 8 }}>
          Menor preço: <span style={{ color: "#7c6aff" }}>{q}</span>
        </h1>
        <p style={{ color: "#4a4a6a", marginBottom: 40 }}>
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
