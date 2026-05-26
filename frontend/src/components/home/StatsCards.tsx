"use client";

import { motion } from "framer-motion";
import { getStats } from "@/lib/mockData";

function formatNumber(n: number): string {
  if (n >= 1000) {
    return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1).replace(".", ",") + (n >= 10000 ? "k" : "k");
  }
  return n.toString();
}

export default function StatsCards() {
  const stats = getStats();

  const cards = [
    {
      value: `+${formatNumber(stats.productsMonitored)}`,
      label: "produtos monitorados",
      color: "#f97316",
    },
    {
      value: `+${formatNumber(stats.weeklySearches)}`,
      label: "buscas essa semana",
      color: "#7c3aed",
    },
    {
      value: `${stats.platforms}`,
      label: "plataformas comparadas",
      color: "#1a1a2e",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 16,
      }}
    >
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 + i * 0.1, duration: 0.4 }}
          style={{
            background: "#fff",
            border: "1px solid #e0e0f0",
            borderRadius: 16,
            padding: "28px 20px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: card.color,
              lineHeight: 1.1,
              marginBottom: 6,
            }}
          >
            {card.value}
          </div>
          <div
            style={{
              fontSize: 13,
              color: "rgba(26,26,46,0.55)",
              fontWeight: 500,
            }}
          >
            {card.label}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
