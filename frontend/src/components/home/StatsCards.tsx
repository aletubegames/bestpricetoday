"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getStats } from "@/lib/mockData";
import { API_BASE, apiFetch } from "@/lib/api";
import styles from "./StatsCards.module.css";

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
    const resp = await apiFetch(`${API_BASE}/api/v1/stats`, {
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
    <div className={styles.grid}>
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 + i * 0.1, duration: 0.4 }}
          className={styles.card}
        >
          <div className={styles.value} style={{ color: card.color }}>
            {card.value}
          </div>
          <div className={styles.label}>
            {card.label}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
