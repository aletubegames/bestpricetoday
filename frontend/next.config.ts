import type { NextConfig } from "next";
const withPWA = require("next-pwa")({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
});

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { hostname: "http2.mlstatic.com" },
      { hostname: "images-na.ssl-images-amazon.com" },
      { hostname: "cf.shopee.com.br" },
      { hostname: "images.kabum.com.br" },
      { hostname: "ae01.alicdn.com" },
    ],
  },
};

module.exports = withPWA(nextConfig);
