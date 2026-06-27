"use client";

import { motion } from "framer-motion";
import { useState, useEffect, useMemo } from "react";
import { useTrendingSearches } from "@/hooks/useTrendingSearches";

const CATEGORIES = [
  { label: "📱 Celulares", query: "celular", color: "#f97316" },
  { label: "💻 Eletrônicos", query: "eletrônicos", color: "#f97316" },
  { label: "🏠 Casa", query: "casa e cozinha", color: "#f97316" },
  { label: "🎮 Games", query: "games", color: "#f97316" },
  { label: "👕 Moda", query: "moda", color: "#f97316" },
  { label: "🏋️ Esportes", query: "esportes", color: "#f97316" },
  { label: "📚 Livros", query: "livros", color: "#f97316" },
  { label: "🐾 Pets", query: "pets", color: "#f97316" },
];

const FALLBACK_PRODUCTS = [
  { emoji: "🎧", query: "fone bluetooth jbl" },
  { emoji: "🍟", query: "air fryer 5l" },
  { emoji: "⌚", query: "smartwatch xiaomi" },
  { emoji: "⌨️", query: "teclado mecânico redragon" },
  { emoji: "🖥️", query: "monitor gamer 27" },
  { emoji: "🤖", query: "aspirador robô" },
  { emoji: "📱", query: "iphone 16" },
  { emoji: "💡", query: "lâmpada smart" },
  { emoji: "🎮", query: "controle ps5" },
  { emoji: "📷", query: "câmera segurança" },
  { emoji: "🔊", query: "caixa de som bluetooth" },
  { emoji: "🖨️", query: "impressora multifuncional" },
];

const BRAND_COLORS = ["#7c3aed", "#f97316", "#1a1a2e", "#ec7000", "#8b5cf6", "#ea580c"];

interface ProductItem {
  emoji: string;
  query: string;
  label: string;
  color: string;
}

export default function FeaturedOffers({ onSearch }: { onSearch: (q: string) => void }) {
  const [hoveredChip, setHoveredChip] = useState<string | null>(null);
  const { data: trendingData } = useTrendingSearches(20);

  const products: ProductItem[] = useMemo(() => {
    const items = trendingData?.items ?? [];
    if (items.length >= 6) {
      // Use trending items dynamically
      return items.slice(0, 12).map((item, i) => ({
        emoji: FALLBACK_PRODUCTS[i % FALLBACK_PRODUCTS.length].emoji,
        query: item.query,
        label: item.query.length > 28 ? item.query.slice(0, 28) + "…" : item.query,
        color: BRAND_COLORS[i % BRAND_COLORS.length],
      }));
    }
    // Fallback: rotate through fixed list
    return FALLBACK_PRODUCTS.map((p, i) => ({
      ...p,
      label: p.query,
      color: BRAND_COLORS[i % BRAND_COLORS.length],
    }));
  }, [trendingData]);

  return (
    <div style={{ textAlign: "center" }}>
      {/* ── Category Chips ── */}
      <div style={{ marginBottom: 32 }}>
        <p style={{ fontSize: 12, color: "var(--muted2)", marginBottom: 12 }}>
          Ou escolha uma categoria:
        </p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            justifyContent: "center",
            maxWidth: 720,
            margin: "0 auto",
          }}
        >
          {CATEGORIES.map((cat) => (
            <button
              key={cat.query}
              onClick={() => onSearch(cat.query)}
              onMouseEnter={() => setHoveredChip(cat.query)}
              onMouseLeave={() => setHoveredChip(null)}
              style={{
                fontSize: 13,
                fontWeight: 600,
                padding: "8px 16px",
                borderRadius: 99,
                border: hoveredChip === cat.query
                  ? "1px solid #f97316"
                  : "1px solid #e0e0f0",
                background: hoveredChip === cat.query
                  ? "rgba(249,115,22,0.08)"
                  : "#fff",
                color: hoveredChip === cat.query ? "#f97316" : "var(--muted)",
                cursor: "pointer",
                transition: "all .15s",
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Featured Products ── */}
      <h2
        style={{
          fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
          fontSize: 22,
          fontWeight: 800,
          color: "#1a1a2e",
          marginBottom: 4,
        }}
      >
        <span style={{ color: "#f97316" }}>Ofertas</span> em destaque
      </h2>
      <p style={{ fontSize: 13, color: "rgba(26,26,46,0.45)", marginBottom: 24 }}>
        Produtos com maior economia agora. Clique pra ver o preço em tempo real.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 10,
        }}
      >
        {products.map((product, i) => (
          <motion.button
            key={product.query + i}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.04 + i * 0.04, duration: 0.3 }}
            onClick={() => onSearch(product.query)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 6,
              padding: "16px 10px",
              borderRadius: 14,
              border: "1px solid #e0e0f0",
              background: "#fff",
              cursor: "pointer",
              transition: "all .15s",
              textAlign: "center",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#f9731660";
              e.currentTarget.style.background = "#f9731608";
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = "0 8px 24px rgba(249,115,22,0.10)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#e0e0f0";
              e.currentTarget.style.background = "#fff";
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <span style={{ fontSize: 24 }}>{product.emoji}</span>
            <div>
              <div style={{
                fontSize: 11, fontWeight: 600, color: "#1a1a2e",
                lineHeight: 1.3, maxWidth: 140,
                overflow: "hidden", textOverflow: "ellipsis",
                display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
              }}>
                {product.label}
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
