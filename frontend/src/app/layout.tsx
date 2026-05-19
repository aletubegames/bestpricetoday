import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "BestPriceToday — Menor Preço do Brasil",
  description: "Compare preços em Mercado Livre, Amazon, Shopee, KaBuM e mais. Cupons automáticos, cashback e histórico de preços. Economize na hora!",
  keywords: ["comparador de preços", "menor preço", "cupom", "cashback", "mercado livre", "amazon", "shopee", "promoções", "ofertas", "brasil"],
  authors: [{ name: "BestPriceToday", url: "https://bestpricetoday.vercel.app" }],
  creator: "AleTubeGames",
  publisher: "AleTubeGames",
  metadataBase: new URL("https://bestpricetoday.vercel.app"),
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://bestpricetoday.vercel.app",
    title: "BestPriceToday — Menor Preço do Brasil",
    description: "Busca automática do menor preço em todas as lojas. Cupons aplicados na hora.",
    siteName: "BestPriceToday",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "BestPriceToday" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "BestPriceToday — Menor Preço do Brasil",
    description: "Compare preços em Mercado Livre, Amazon, Shopee e mais.",
    creator: "@AleTubeGames",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true } },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32", type: "image/x-icon" },
      { url: "/favicon.png", sizes: "any", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
    shortcut: "/favicon.ico",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#f0f4ff",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <link rel="canonical" href="https://bestpricetoday.vercel.app" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
