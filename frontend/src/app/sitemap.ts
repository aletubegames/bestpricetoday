import type { MetadataRoute } from 'next'
import { SITE_BASE, API_BASE } from '@/lib/api'
import { CATEGORIES } from '@/lib/categories'

// Sitemap dinâmico: consome queries do backend (trending + curadoria)
// ISR: revalida a cada 6h (as queries populares mudam lentamente)
// IMPORTANTE: só incluir queries que retornam ≥3 ofertas reais.
// Queries vazias = thin content = Google desindexa o site.
export const revalidate = 21600

interface SitemapQuery {
  query: string
  score: number
  source: string
}

async function fetchSitemapQueries(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/search/sitemap-queries?limit=500`, {
      next: { revalidate: 21600 },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    return (data.queries as SitemapQuery[]).map(q => q.query)
  } catch {
    // Fallback: queries que sabemos que têm produtos (airfryers)
    return [
      "airfryer", "airfryer-5l", "airfryer-britania", "airfryer-arno",
      "airfryer-cadence", "airfryer-electrolux", "airfryer-mondial",
      "abajur", "adaptador-usb-c",
    ]
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = SITE_BASE
  const now = new Date()
  const queries = await fetchSitemapQueries()

  const staticPages: MetadataRoute.Sitemap = [
    { url: base, lastModified: now, changeFrequency: "hourly", priority: 1 },
    { url: `${base}/alertas`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/terms`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/privacy`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
  ]

  // Páginas de categoria (hubs de nicho)
  const categoryPages: MetadataRoute.Sitemap = CATEGORIES.map(c => ({
    url: `${base}/categoria/${c.slug}`,
    lastModified: now,
    changeFrequency: "daily" as const,
    priority: 0.9,
  }))

  // Páginas de produto (só queries com ofertas reais)
  const productPages: MetadataRoute.Sitemap = queries.map(q => ({
    url: `${base}/produto/${encodeURIComponent(q)}`,
    lastModified: now,
    changeFrequency: "hourly" as const,
    priority: 0.8,
  }))

  // Nota: páginas de marca (/marca/[slug]) removidas do sitemap porque
  // nenhuma marca tem ofertas reais no catálogo atual (0 ofertas).
  // Re-adicionar quando o catálogo tiver produtos de marca.
  return [...staticPages, ...categoryPages, ...productPages]
}
