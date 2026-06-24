"use client";

import { motion } from "framer-motion";

interface Store {
  name: string;
  domain: string;
}

const STORES: Store[] = [
  { name: "Shopee", domain: "shopee.com.br" },
  { name: "Mercado Livre", domain: "mercadolivre.com.br" },
  { name: "AliExpress", domain: "aliexpress.com" },
  { name: "Lomadee", domain: "lomadee.com" },
];

function FaviconImg({ domain }: { domain: string }) {
  const url = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  return (
    <img
      src={url}
      alt=""
      width={16}
      height={16}
      style={{ borderRadius: 3, flexShrink: 0 }}
      onError={(e) => {
        (e.target as HTMLImageElement).style.display = "none";
      }}
    />
  );
}

export default function StoreChips({ compact }: { compact?: boolean }) {
  const chipStyle = compact
    ? {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        background: "rgba(255,255,255,0.8)",
        border: "1px solid #e8e8f0",
        borderRadius: 99,
        padding: "4px 12px 4px 8px",
        fontSize: 12,
        fontWeight: 500,
        color: "#3a3a5c",
      } as React.CSSProperties
    : {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "#fff",
        border: "1px solid #e0e0f0",
        borderRadius: 99,
        padding: "8px 18px 8px 12px",
        fontSize: 14,
        fontWeight: 500,
        color: "#3a3a5c",
      } as React.CSSProperties;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: compact ? 6 : 10,
        justifyContent: "center",
      }}
    >
      {STORES.map((store, i) => (
        <motion.div
          key={store.name}
          initial={compact ? false : { opacity: 0, y: 12 }}
          animate={compact ? false : { opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + i * 0.08, duration: 0.35 }}
          style={chipStyle}
        >
          <FaviconImg domain={store.domain} />
          <span>{store.name}</span>
          {!compact && (
            <span
              className="pulse-dot"
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#00b894",
                flexShrink: 0,
              }}
            />
          )}
        </motion.div>
      ))}
    </div>
  );
}
