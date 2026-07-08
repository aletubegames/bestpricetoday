/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "http2.mlstatic.com" },
      { protocol: "https", hostname: "images-na.ssl-images-amazon.com" },
      { protocol: "https", hostname: "m.media-amazon.com" },
      { protocol: "https", hostname: "cf.shopee.com.br" },
      { protocol: "https", hostname: "images.kabum.com.br" },
      { protocol: "https", hostname: "ae01.alicdn.com" },
      { protocol: "https", hostname: "**.alicdn.com" },
      { protocol: "https", hostname: "**.aliexpress-media.com" },
      { protocol: "https", hostname: "**.vteximg.com.br" },
      { protocol: "https", hostname: "**.vtex.com.br" },
      { protocol: "https", hostname: "shopinfo.vteximg.com.br" },
      { protocol: "https", hostname: "api.alaserver.com.br" },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.clarity.ms https://scripts.clarity.ms https://static.cloudflareinsights.com",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' https: data: blob:",
              "font-src 'self' https://fonts.gstatic.com",
              "connect-src 'self' https://api.alaserver.com.br https://www.googletagmanager.com https://www.clarity.ms https://i.clarity.ms https://www.google-analytics.com https://www.google.com https://cloudflareinsights.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
