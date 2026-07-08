"use client";

import { motion } from "framer-motion";
import styles from "./StoreChips.module.css";

interface Store {
  name: string;
  domain: string;
}

const STORES: Store[] = [
  { name: "Shopee", domain: "shopee.com.br" },
  { name: "Mercado Livre", domain: "mercadolivre.com.br" },
  { name: "Amazon", domain: "amazon.com.br" },
  { name: "AliExpress", domain: "aliexpress.com" },
  { name: "TikTok Shop", domain: "tiktok.com" },
  { name: "Lomadee", domain: "lomadee.com" },
];

function FaviconImg({ domain }: { domain: string }) {
  const url = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={`Favicon ${domain}`}
      width={16}
      height={16}
      className={styles.favicon}
      onError={(e) => {
        (e.target as HTMLImageElement).style.display = "none";
      }}
    />
  );
}

export default function StoreChips({ compact }: { compact?: boolean }) {
  return (
    <div className={`${styles.root} ${compact ? styles.rootCompact : styles.rootNormal}`}>
      {STORES.map((store, i) => (
        <motion.div
          key={store.name}
          initial={compact ? false : { opacity: 0, y: 12 }}
          animate={compact ? false : { opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + i * 0.08, duration: 0.35 }}
          className={`${styles.chip} ${compact ? styles.chipCompact : styles.chipNormal}`}
        >
          <FaviconImg domain={store.domain} />
          <span>{store.name}</span>
          {!compact && <span className={styles.pulseDot} />}
        </motion.div>
      ))}
    </div>
  );
}
