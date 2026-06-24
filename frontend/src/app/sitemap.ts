import type { MetadataRoute } from 'next'

const POPULAR_QUERIES = [
  "iphone-16-pro", "samsung-galaxy-s25", "notebook-gamer", "rtx-4070",
  "fone-bluetooth", "smartwatch", "tablet-android", "airfryer",
  "ar-condicionado-split", "smart-tv-55", "ssd-nvme-1tb",
  "playstation-5", "xbox-series-x", "kindle", "aspirador-robo",
]

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://bestpricetoday.vercel.app"
  const now = new Date()

  return [
    { url: base, lastModified: now, changeFrequency: "hourly", priority: 1 },
    { url: `${base}/alertas`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/terms`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/privacy`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    ...POPULAR_QUERIES.map(q => ({
      url: `${base}/produto/${q}`,
      lastModified: now,
      changeFrequency: "hourly" as const,
      priority: 0.8,
    })),
  ]
}
