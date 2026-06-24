"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getStats } from "@/lib/mockData";
import { API_BASE } from "@/lib/api";

interface Stats {
  productsMonitored: number;
  weeklySearches: number;
  platforms: number;
}

function formatNumber(n: number): string {
  if (n >= 1000) {
    const divided = n / 1000;
    return (divided >= 10 ? Math.round(divided).toString() : divided.toFixed(1).replace(".", ",")) + "k";
  }
  return n.toString();
}

async function fetchStats(): Promise<Stats> {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/stats`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return {
      productsMonitored: data.total_products || 0,
      weeklySearches: data.weekly_searches || 0,
      platforms: data.platforms || 0,
    };
  } catch {
    // Fallback to mock
    return getStats();
  }
}

export default function StatsCards() {
  const [stats, setStats] = useState<Stats>({
    productsMonitored: 0,
    weeklySearches: 0,
    platforms: 0,
  });

  useEffect(() => {
    fetchStats().then(setStats);
  }, []);

  // If all zeros, use mock fallback
  const display =
    stats.productsMonitored === 0 && stats.weeklySearches === 0
      ? getStats()
      : stats;

  const cards = [
    {
      value: `+${formatNumber(display.productsMonitored)}`,
      label: "produtos monitorados",
      color: "#f97316",
    },
    {
      value: `+${formatNumber(display.weeklySearches)}`,
      label: "buscas essa semana",
      color: "#7c3aed",
    },
    {
      value: `${display.platforms}`,
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
