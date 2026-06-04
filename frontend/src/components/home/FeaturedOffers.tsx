"use client";

import { motion } from "framer-motion";
import { useState } from "react";

const CATEGORIES = [
  { label: "📱 Celulares", query: "celular" },
  { label: "💻 Eletrônicos", query: "eletrônicos" },
  { label: "🏠 Casa", query: "casa e cozinha" },
  { label: "🎮 Games", query: "games" },
  { label: "👕 Moda", query: "moda" },
  { label: "🏋️ Esportes", query: "esportes" },
  { label: "📚 Livros", query: "livros" },
  { label: "🐾 Pets", query: "pets" },
];

const FEATURED_PRODUCTS = [
  {
    title: "Fone Bluetooth JBL Tune 510BT",
    desc: "Até R$ 55 mais barato",
    emoji: "🎧",
    color: "#7c3aed",
    query: "fone bluetooth jbl",
  },
  {
    title: "Air Fryer 5L Mondial",
    desc: "Economia de até R$ 98",
    emoji: "🍟",
    color: "#f97316",
    query: "air fryer 5l",
  },
  {
    title: "Smartwatch Xiaomi",
    desc: "A partir de R$ 149",
    emoji: "⌚",
    color: "#00b894",
    query: "smartwatch xiaomi",
  },
  {
    title: "Teclado Mecânico Redragon",
    desc: "R$ 67 mais barato",
    emoji: "⌨️",
    color: "#e74c3c",
    query: "teclado mecânico redragon",
  },
  {
    title: "Monitor Gamer 27\"",
    desc: "Economia de até R$ 320",
    emoji: "🖥️",
    color: "#8b5cf6",
    query: "monitor gamer 27",
  },
  {
    title: "Aspirador Robô",
    desc: "Metade do preço da loja",
    emoji: "🤖",
    color: "#10b981",
    query: "aspirador robô",
  },
];

export default function FeaturedOffers({ onSearch }: { onSearch: (q: string) => void }) {
  const [hoveredChip, setHoveredChip] = useState<string | null>(null);

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
            maxWidth: 680,
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
                  ? "1px solid rgba(124,58,237,0.4)"
                  : "1px solid #e0e0f0",
                background: hoveredChip === cat.query
                  ? "rgba(124,58,237,0.06)"
                  : "#fff",
                color: hoveredChip === cat.query ? "#7c3aed" : "var(--muted)",
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
        Ofertas em destaque
      </h2>
      <p style={{ fontSize: 13, color: "rgba(26,26,46,0.45)", marginBottom: 24 }}>
        Produtos com maior economia. Clique pra ver o preço em tempo real.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        {FEATURED_PRODUCTS.map((product, i) => (
          <motion.button
            key={product.query}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 + i * 0.06, duration: 0.35 }}
            onClick={() => onSearch(product.query)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              padding: "20px 14px",
              borderRadius: 14,
              border: "1px solid #e0e0f0",
              background: "#fff",
              cursor: "pointer",
              transition: "all .15s",
              textAlign: "center",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = `${product.color}40`;
              e.currentTarget.style.background = `${product.color}06`;
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 8px 24px ${product.color}12`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#e0e0f0";
              e.currentTarget.style.background = "#fff";
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <span style={{ fontSize: 28 }}>{product.emoji}</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a2e", lineHeight: 1.3 }}>
                {product.title}
              </div>
              <div style={{ fontSize: 11, color: product.color, fontWeight: 500, marginTop: 3 }}>
                {product.desc}
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
