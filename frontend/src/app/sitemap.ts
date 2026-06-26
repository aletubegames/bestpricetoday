import type { MetadataRoute } from 'next'
import { SITE_BASE, API_BASE } from '@/lib/api'
import { CATEGORIES } from '@/lib/categories'
import { BRANDS } from '@/lib/brands'

// Sitemap dinâmico: consome queries do backend (trending + curadoria)
// ISR: revalida a cada 6h (as queries populares mudam lentamente)
export const revalidate = 21600

interface SitemapQuery {
  query: string
  score: number
  source: string
}

async function fetchSitemapQueries(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/search/sitemap-queries?limit=5000`, {
      next: { revalidate: 21600 },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    return (data.queries as SitemapQuery[]).map(q => q.query)
  } catch {
    // Fallback: queries estáticas básicas
    return [
      "iphone-16-pro", "samsung-galaxy-s25", "notebook-gamer", "rtx-4070",
      "fone-bluetooth", "smartwatch", "tablet-android", "airfryer",
      "ar-condicionado-split", "smart-tv-55", "ssd-nvme-1tb",
      "playstation-5", "xbox-series-x", "kindle", "aspirador-robo",
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

  // Páginas de marca (hubs por fabricante)
  const brandPages: MetadataRoute.Sitemap = BRANDS.map(b => ({
    url: `${base}/marca/${b.slug}`,
    lastModified: now,
    changeFrequency: "daily" as const,
    priority: 0.85,
  }))

  const productPages: MetadataRoute.Sitemap = queries.map(q => ({
    url: `${base}/produto/${encodeURIComponent(q)}`,
    lastModified: now,
    changeFrequency: "hourly" as const,
    priority: 0.8,
  }))

  return [...staticPages, ...categoryPages, ...brandPages, ...productPages]
}
