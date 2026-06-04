import type { Metadata, Viewport } from "next";
import { Syne, DM_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BestPriceToday — Menor Preço do Brasil",
  description:
    "Compare preços em Mercado Livre, Amazon, Shopee, KaBuM e mais. Cupons automáticos, cashback e histórico de preços. Economize na hora!",
  keywords: [
    "comparador de preços",
    "menor preço",
    "cupom",
    "cashback",
    "mercado livre",
    "amazon",
    "shopee",
    "promoções",
    "ofertas",
    "brasil",
  ],
  authors: [
    { name: "BestPriceToday", url: "https://bestpricetoday.vercel.app" },
  ],
  creator: "AleTubeGames",
  publisher: "AleTubeGames",
  metadataBase: new URL("https://bestpricetoday.vercel.app"),
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://bestpricetoday.vercel.app",
    title: "BestPriceToday — Menor Preço do Brasil",
    description:
      "Busca automática do menor preço em todas as lojas. Cupons aplicados na hora.",
    siteName: "BestPriceToday",
    images: [
      { url: "/og-image.png", width: 1200, height: 630, alt: "BestPriceToday" },
    ],
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
      { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/favicon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
    shortcut: "/favicon.ico",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#eeeef8",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      suppressHydrationWarning
      className={`${syne.variable} ${dmSans.variable}`}
    >
      <head>
        <link rel="canonical" href="https://bestpricetoday.vercel.app" />
      </head>
      <body className={dmSans.className}>
        <Providers>{children}</Providers>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
