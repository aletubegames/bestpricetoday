import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { Syne, DM_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";
import { SITE_BASE } from "@/lib/api";

// Analytics IDs (setar no .env.local)
const GA4_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA4_ID || "";
const CLARITY_ID = process.env.NEXT_PUBLIC_CLARITY_ID || "";
const FB_PIXEL_ID = process.env.NEXT_PUBLIC_FB_PIXEL_ID || "";

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
    "Compare preços em Mercado Livre, Amazon, Shopee, KaBuM e mais. Histórico de preços, alertas de queda e melhores ofertas. Economize na hora!",
  keywords: [
    "comparador de preços",
    "menor preço",
    "histórico de preços",
    "alerta de preço",
    "mercado livre",
    "amazon",
    "shopee",
    "promoções",
    "ofertas",
    "brasil",
  ],
  authors: [
    { name: "BestPriceToday", url: SITE_BASE },
  ],
  creator: "AleTubeGames",
  publisher: "AleTubeGames",
  metadataBase: new URL(SITE_BASE),
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: SITE_BASE,
    title: "BestPriceToday — Menor Preço do Brasil",
    description:
      "Busca automática do menor preço em todas as lojas. Histórico de preços e alertas de queda.",
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
  verification: {
    other: {
      "msvalidate.01": "7DD0E45802E8267028890F5130C9326E",
    },
  },
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
        <link rel="canonical" href={SITE_BASE} />
      </head>
      <body className={dmSans.className}>
        <Providers>{children}</Providers>

        {/* Google Analytics 4 (GA4) */}
        {GA4_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA4_MEASUREMENT_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA4_MEASUREMENT_ID}', { page_path: window.location.pathname });
              `}
            </Script>
          </>
        )}

        {/* Microsoft Clarity (heatmaps + session recordings) */}
        {CLARITY_ID && (
          <Script id="clarity-init" strategy="afterInteractive">
            {`
              (function(c,l,a,r,i,t,y){
                c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
                t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
                y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
              })(window,document,"clarity","script","${CLARITY_ID}");
            `}
          </Script>
        )}

        {/* Meta (Facebook) Pixel */}
        {FB_PIXEL_ID && (
          <>
            <Script id="fb-pixel-init" strategy="afterInteractive">
              {`
                !function(f,b,e,v,n,t,s)
                {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
                n.callMethod.apply(n,arguments):n.queue.push(arguments)};
                if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
                n.queue=[];t=b.createElement(e);t.async=!0;
                t.src=v;s=b.getElementsByTagName(e)[0];
                s.parentNode.insertBefore(t,s)}(window,document,'script',
                'https://connect.facebook.net/en_US/fbevents.js');
                fbq('init', '${FB_PIXEL_ID}');
                fbq('track', 'PageView');
              `}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
