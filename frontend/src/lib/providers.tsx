import type { ReactNode } from "react";

export interface ProviderConfig {
  name: string;
  color: string;
}

export const PROVIDERS: Record<string, ProviderConfig> = {
  mercadolivre: { name: "Mercado Livre", color: "#FACC15" },
  amazon:       { name: "Amazon",        color: "#FB923C" },
  shopee:       { name: "Shopee",        color: "#F87171" },
  kabum:        { name: "KaBuM",         color: "#4ADE80" },
  aliexpress:   { name: "AliExpress",    color: "#F43F5E" },
  lomadee:      { name: "Lomadee",       color: "#C084FC" },
  awin:         { name: "Awin",          color: "#60A5FA" },
  tiktokshop:   { name: "TikTok Shop",   color: "#00F2EA" },
};

export function getProviderName(provider: string): string {
  return PROVIDERS[provider]?.name ?? provider;
}

export function getProviderColor(provider: string): string {
  return PROVIDERS[provider]?.color ?? "#a78bfa";
}

export function ProviderLogo({ provider, size = 20 }: { provider: string; size?: number }) {
  const logo = LOGOS[provider];
  if (!logo) {
    return (
      <svg width={size} height={size} viewBox="0 0 40 40">
        <rect width="40" height="40" rx="8" fill="#a78bfa" />
        <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">
          {provider.slice(0, 2).toUpperCase()}
        </text>
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 40 40">
      {logo}
    </svg>
  );
}

const LOGOS: Record<string, ReactNode> = {
  aliexpress: (
    <>
      <rect width="40" height="40" rx="8" fill="#FF4747" />
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">AE</text>
    </>
  ),
  shopee: (
    <>
      <rect width="40" height="40" rx="8" fill="#EE4D2D" />
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">S</text>
    </>
  ),
  mercadolivre: (
    <>
      <rect width="40" height="40" rx="8" fill="#FFE600" />
      <text x="50%" y="65%" textAnchor="middle" fill="#333" fontSize="14" fontWeight="bold">ML</text>
    </>
  ),
  amazon: (
    <>
      <rect width="40" height="40" rx="8" fill="#131921" />
      <text x="50%" y="55%" textAnchor="middle" fill="#FF9900" fontSize="18" fontWeight="bold" fontStyle="italic">a</text>
      <path d="M12 28 Q20 32 28 28" stroke="#FF9900" strokeWidth="2" fill="none" strokeLinecap="round" />
    </>
  ),
  lomadee: (
    <>
      <rect width="40" height="40" rx="8" fill="#7C3AED" />
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">L</text>
    </>
  ),
  kabum: (
    <>
      <rect width="40" height="40" rx="8" fill="#FF6B00" />
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">K</text>
    </>
  ),
  awin: (
    <>
      <rect width="40" height="40" rx="8" fill="#60A5FA" />
      <text x="50%" y="65%" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">AW</text>
    </>
  ),
  tiktokshop: (
    <>
      <rect width="40" height="40" rx="8" fill="#000000" />
      <text x="50%" y="65%" textAnchor="middle" fill="#00F2EA" fontSize="20" fontWeight="bold">♪</text>
    </>
  ),
};

export const STORE_CHIPS = [
  { name: "Shopee", domain: "shopee.com.br" },
  { name: "Mercado Livre", domain: "mercadolivre.com.br" },
  { name: "Amazon", domain: "amazon.com.br" },
  { name: "AliExpress", domain: "aliexpress.com" },
  { name: "TikTok Shop", domain: "tiktok.com" },
];
