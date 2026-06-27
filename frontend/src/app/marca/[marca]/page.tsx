import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { API_BASE as API, SITE_BASE } from "@/lib/api"
import { BRANDS, getBrand, getAllBrandSlugs, type BrandConfig } from "@/lib/brands"
import type { Offer } from "@/types"

interface Props {
  params: { marca: string }
}

// ISR: revalida a cada 1h
export const revalidate = 3600

export function generateStaticParams() {
  return getAllBrandSlugs().map(slug => ({ marca: slug }))
}

async function fetchBrandOffers(queries: string[]): Promise<Record<string, Offer[]>> {
  const results: Record<string, Offer[]> = {}
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
  const brand = getBrand(params.marca)
  if (!brand) return { title: "Marca não encontrada" }

  return {
    title: `${brand.name} — Menores Preços | BestPriceToday`,
    description: brand.description,
    keywords: [brand.name, "ofertas", "menor preço", "cupom", "desconto", ...brand.queries.slice(0, 8)],
    openGraph: {
      title: `${brand.name} — Menores Preços Garantidos`,
      description: brand.description,
      url: `${SITE_BASE}/marca/${brand.slug}`,
    },
    alternates: {
      canonical: `${SITE_BASE}/marca/${brand.slug}`,
    },
  }
}

export default async function BrandPage({ params }: Props) {
  const brand = getBrand(params.marca)
  if (!brand) notFound()

  const offersByQuery = await fetchBrandOffers(brand.queries)
  const allOffers = Object.values(offersByQuery).flat()
  const bestPrice = allOffers.length > 0
    ? Math.min(...allOffers.map(o => o.final_price || o.price || Infinity))
    : 0

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": `Ofertas ${brand.name}`,
    "description": brand.description,
    "url": `${SITE_BASE}/marca/${brand.slug}`,
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
          "brand": { "@type": "Brand", "name": brand.name },
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

  // Marcas relacionadas
  const relatedBrands = brand.related
    .map(slug => getBrand(slug))
    .filter((b): b is BrandConfig => b !== undefined)

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
          <span style={{ fontSize: 16 }}>{brand.icon} {brand.name}</span>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 16px" }}>
        {/* Hero da marca */}
        <h1 style={{ fontSize: "clamp(1.5rem,4vw,2.5rem)", fontWeight: 900, marginBottom: 8 }}>
          {brand.icon} Ofertas {brand.name}
        </h1>
        <p style={{ color: "#4a4a6a", marginBottom: 32, fontSize: 16, maxWidth: 600 }}>
          {brand.description}
        </p>

        {/* Grid de ofertas por query */}
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
                      {offer.image_url && (
                        <img
                          src={offer.image_url}
                          alt={offer.title?.slice(0, 60)}
                          style={{ width: "100%", height: 140, objectFit: "cover" }}
                          loading="lazy"
                        />
                      )}
                      <div style={{ padding: 12 }}>
                        <div style={{ fontSize: 13, color: "#4a4a6a", marginBottom: 4 }}>
                          {logo} {offer.provider}
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.3, marginBottom: 8, height: 36, overflow: "hidden" }}>
                          {offer.title?.slice(0, 70)}
                        </div>
                        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                          <span style={{ fontSize: 18, fontWeight: 900, color: "#00b894" }}>
                            R$ {(offer.final_price || offer.price || 0).toFixed(2).replace(".", ",")}
                          </span>
                          {offer.original_price && offer.original_price > (offer.final_price || offer.price || 0) && (
                            <span style={{ fontSize: 12, color: "#999", textDecoration: "line-through" }}>
                              R$ {offer.original_price.toFixed(2).replace(".", ",")}
                            </span>
                          )}
                        </div>
                        {offer.discount_percent > 0 && (
                          <span style={{
                            display: "inline-block", marginTop: 4,
                            background: "rgba(0,229,160,0.15)", color: "#00a884",
                            fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 6,
                          }}>
                            -{Math.round(offer.discount_percent)}%
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        ))}

        {/* Marcas relacionadas */}
        {relatedBrands.length > 0 && (
          <section style={{ marginTop: 48, padding: 24, background: "#fff", borderRadius: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>Marcas relacionadas</h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              {relatedBrands.map(rb => (
                <a
                  key={rb.slug}
                  href={`/marca/${rb.slug}`}
                  style={{
                    padding: "8px 16px", background: "rgba(124,106,255,0.1)",
                    borderRadius: 10, textDecoration: "none", color: "#7c6aff",
                    fontWeight: 600, fontSize: 14,
                  }}
                >
                  {rb.icon} {rb.name}
                </a>
              ))}
            </div>
          </section>
        )}

        {/* Buscas populares da marca */}
        <section style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>Buscas populares {brand.name}</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {brand.queries.map(q => (
              <a
                key={q}
                href={`/produto/${encodeURIComponent(q)}`}
                style={{
                  padding: "6px 12px", background: "#fff", border: "1px solid rgba(124,106,255,0.2)",
                  borderRadius: 8, textDecoration: "none", color: "#4a4a6a", fontSize: 13,
                }}
              >
                {q.replace(/-/g, " ")}
              </a>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
