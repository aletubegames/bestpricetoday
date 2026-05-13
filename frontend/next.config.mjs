/** @type {import('next').NextConfig} */
const nextConfig = {
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

export default nextConfig;
