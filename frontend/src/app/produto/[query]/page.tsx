import type { Metadata } from "next"
import ProductSearchClient from "./ProductSearchClient"
import { API_BASE as API } from "@/lib/api"

interface Props {
  params: { query: string }
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
      url: `https://bestpricetoday.vercel.app/produto/${params.query}`,
    },
    alternates: {
      canonical: `https://bestpricetoday.vercel.app/produto/${params.query}`,
    },
  }
}

export default function ProductPage({ params }: Props) {
  const q = decodeURIComponent(params.query)

  return (
    <div style={{ minHeight: "100vh", background: "#07070f", color: "#fff", fontFamily: "system-ui" }}>
      {/* SEO structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SearchResultsPage",
            "name": `Menor preço ${q}`,
            "description": `Compare preços de ${q} nas melhores lojas do Brasil`,
            "url": `https://bestpricetoday.vercel.app/produto/${params.query}`,
          })
        }}
      />

      {/* Header */}
      <header style={{ borderBottom: "1px solid #1e293b", padding: "16px 24px", background: "rgba(7,7,15,0.95)" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", alignItems: "center", gap: 12 }}>
          <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 24 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 17, color: "#7c6aff" }}>BestPriceToday</span>
          </a>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
        <h1 style={{ fontSize: "clamp(1.5rem,4vw,2.5rem)", fontWeight: 900, marginBottom: 8 }}>
          Menor preço: <span style={{ color: "#7c6aff" }}>{q}</span>
        </h1>
        <p style={{ color: "#94a3b8", marginBottom: 40 }}>
          Comparação em tempo real em AliExpress, Shopee, Mercado Livre e mais lojas.
        </p>

        <ProductSearchClient query={q} />
      </div>
    </div>
  )
}
