import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { API_BASE as API, SITE_BASE } from "@/lib/api"
import { CATEGORIES, getCategory, getAllCategorySlugs } from "@/lib/categories"
import type { Offer } from "@/types"

interface Props {
  params: { cat: string }
}

// ISR: revalida a cada 1h (ofertas mudam, mas categoria é mais estável)
export const revalidate = 3600

// Pré-gerar as categorias estáticas no build
export function generateStaticParams() {
  return getAllCategorySlugs().map(slug => ({ cat: slug }))
}

// Busca top ofertas para a categoria (agrega múltiplas queries)
async function fetchCategoryOffers(queries: string[]): Promise<Record<string, Offer[]>> {
  const results: Record<string, Offer[]> = {}

  // Busca em paralelo as top 4 queries da categoria (limite para não sobrecarregar)
  const topQueries = queries.slice(0, 4)
  const responses = await Promise.allSettled(
    topQueries.map(q =>
      fetch(`${API}/api/v1/search?q=${encodeURIComponent(q)}&limit=6`, {
        next: { revalidate: 3600 },
      }).then(r => r.ok ? r.json() : null)
    )
  )

  responses.forEach((res, i) => {
    if (res.status === "fulfilled" && res.value?.offers) {
      results[topQueries[i]] = res.value.offers
    }
  })

  return results
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const cat = getCategory(params.cat)
  if (!cat) return { title: "Categoria não encontrada" }

  return {
    title: `${cat.name} — Menores Preços | BestPriceToday`,
    description: cat.description,
    keywords: [cat.name, "ofertas", "menor preço", "cupom", "desconto", ...cat.queries.slice(0, 8)],
    openGraph: {
      title: `${cat.name} — Menores Preços Garantidos`,
      description: cat.description,
      url: `${SITE_BASE}/categoria/${cat.slug}`,
    },
    alternates: {
      canonical: `${SITE_BASE}/categoria/${cat.slug}`,
    },
  }
}

export default async function CategoryPage({ params }: Props) {
  const cat = getCategory(params.cat)
  if (!cat) notFound()

  const offersByQuery = await fetchCategoryOffers(cat.queries)

  // Aggregate all offers for JSON-LD
  const allOffers = Object.values(offersByQuery).flat()
  const bestPrice = allOffers.length > 0
    ? Math.min(...allOffers.map(o => o.final_price || o.price || Infinity))
    : 0

  // JSON-LD CollectionPage + ItemList
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": cat.name,
    "description": cat.description,
    "url": `${SITE_BASE}/categoria/${cat.slug}`,
    "mainEntity": {
      "@type": "ItemList",
      "numberOfItems": allOffers.length,
      "itemListElement": allOffers.slice(0, 20).map((o, i) => ({
        "@type": "ListItem",
        "position": i + 1,
        "item": {
          "@type": "Product",
          "name": o.title?.slice(0, 80),
          "image": o.image_url,
          "offers": {
            "@type": "Offer",
            "price": o.final_price || o.price || 0,
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "seller": { "@type": "Organization", "name": o.provider },
          },
        },
      })),
    },
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
          <span style={{ color: "#4a4a6a", fontSize: 14 }}>›</span>
          <span style={{ fontSize: 16 }}>{cat.icon} {cat.name}</span>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 16px" }}>
        {/* Hero da categoria */}
        <h1 style={{ fontSize: "clamp(1.5rem,4vw,2.5rem)", fontWeight: 900, marginBottom: 8 }}>
          {cat.icon} {cat.name}
        </h1>
        <p style={{ color: "#4a4a6a", marginBottom: 32, fontSize: 16, maxWidth: 600 }}>
          {cat.description}
        </p>

        {/* Grid de ofertas por sub-query */}
        {Object.entries(offersByQuery).map(([query, offers]) => (
          offers.length > 0 && (
            <section key={query} style={{ marginBottom: 48 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "#1a1a2e" }}>
                  {query.replace(/-/g, " ")}
                </h2>
                <a
                  href={`/produto/${encodeURIComponent(query)}`}
                  style={{ color: "#7c6aff", fontSize: 14, fontWeight: 600, textDecoration: "none" }}
                >
                  Ver todas →
                </a>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
                {offers.slice(0, 6).map((offer, i) => {
                  const isFirst = i === 0
                  const logo = offer.provider === "aliexpress" ? "🔴"
                    : offer.provider === "shopee" ? "🟠"
                    : offer.provider === "mercadolivre" ? "🟡"
                    : offer.provider === "amazon" ? "📦" : "🏪"
                  return (
                    <div key={`${query}-${i}`} style={{
                      background: "#fff",
                      border: `1px solid ${isFirst ? "rgba(0,229,160,0.4)" : "rgba(124,106,255,0.15)"}`,
                      borderRadius: 14, overflow: "hidden",
                    }}>
                      {isFirst && (
                        <div style={{ background: "linear-gradient(90deg,#00e5a0,#0ea5e9)", height: 3 }} />
                      )}
                      <div style={{ padding: 14 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                          <span style={{ fontSize: 14 }}>{logo}</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", textTransform: "capitalize" }}>
                            {offer.provider}
                          </span>
                          {offer.discount_percent >= 5 && !offer.is_fake_discount && (
                            <span style={{ fontSize: 10, fontWeight: 700, color: "#ff6b6b", background: "rgba(255,107,107,.12)", padding: "2px 6px", borderRadius: 99 }}>
                              -{Math.round(offer.discount_percent)}%
                            </span>
                          )}
                        </div>
                        {offer.image_url && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={offer.image_url}
                            alt={offer.title}
                            loading="lazy"
                            style={{ width: "100%", height: 140, objectFit: "contain", borderRadius: 8, background: "#eef0ff", marginBottom: 10 }}
                          />
                        )}
                        <p style={{ fontSize: 12, color: "#4a4a6a", lineHeight: 1.4, marginBottom: 8, minHeight: 34, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                          {offer.title}
                        </p>
                        {typeof offer.original_price === "number" && typeof offer.final_price === "number" && offer.original_price > offer.final_price && (
                          <div style={{ fontSize: 11, color: "#475569", textDecoration: "line-through" }}>
                            R$ {offer.original_price.toFixed(2)}
                          </div>
                        )}
                        <div style={{ fontSize: 22, fontWeight: 900, color: "#1a1a2e", marginBottom: 8 }}>
                          R$ {offer.final_price?.toFixed(2)}
                        </div>
                        <a
                          href={`/produto/${encodeURIComponent(query)}`}
                          style={{
                            display: "block", textAlign: "center",
                            padding: "10px", borderRadius: 10, fontWeight: 700,
                            background: isFirst ? "linear-gradient(135deg,#00e5a0,#0ea5e9)" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
                            color: isFirst ? "#000" : "#fff",
                            textDecoration: "none", fontSize: 13,
                          }}
                        >
                          Ver oferta →
                        </a>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        ))}

        {/* Links internos: todas as queries da categoria (link juice) */}
        <section style={{ marginTop: 48, paddingTop: 32, borderTop: "1px solid rgba(108,92,231,0.15)" }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>
            🔍 Buscas populares em {cat.name}
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {cat.queries.map(q => (
              <a
                key={q}
                href={`/produto/${encodeURIComponent(q)}`}
                style={{
                  padding: "8px 16px", borderRadius: 99,
                  background: "#fff", border: "1px solid rgba(108,92,231,0.2)",
                  color: "#4a4a6a", textDecoration: "none", fontSize: 13,
                  transition: "all 0.2s",
                }}
              >
                {q.replace(/-/g, " ")}
              </a>
            ))}
          </div>
        </section>

        {/* Categorias relacionadas */}
        <section style={{ marginTop: 40, paddingTop: 32, borderTop: "1px solid rgba(108,92,231,0.15)" }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>
            📂 Categorias relacionadas
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {cat.related.map(slug => {
              const related = getCategory(slug)
              if (!related) return null
              return (
                <a
                  key={slug}
                  href={`/categoria/${slug}`}
                  style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "12px 20px", borderRadius: 14,
                    background: "#fff", border: "1px solid rgba(124,106,255,0.15)",
                    color: "#1a1a2e", textDecoration: "none", fontSize: 14, fontWeight: 600,
                  }}
                >
                  <span style={{ fontSize: 20 }}>{related.icon}</span>
                  {related.name}
                </a>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}
