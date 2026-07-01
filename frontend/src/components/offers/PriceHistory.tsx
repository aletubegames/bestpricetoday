"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import styles from "./PriceHistory.module.css";

interface PricePoint {
  price: number;
  recorded_at: string;
  provider: string;
}

interface PriceStats {
  current_price: number;
  min_price: number;
  max_price: number;
  avg_price: number;
  history_count: number;
  is_best_price: boolean;
  best_price: number;
  title: string;
}

interface Props {
  productId: string;
  provider?: string;
}

export default function PriceHistory({ productId }: Props) {
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [stats, setStats] = useState<PriceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;

    async function fetchHistory() {
      try {
        setLoading(true);
        const [histRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/affiliate/products/${productId}/history?days=365`),
          fetch(`${API_BASE}/api/v1/affiliate/products/${productId}/stats`),
        ]);

        if (!histRes.ok || !statsRes.ok) throw new Error("Falha ao carregar histórico");

        const histData: PricePoint[] = await histRes.json();
        const statsData: PriceStats = await statsRes.json();

        if (!cancelled) {
          setHistory(histData);
          setStats(statsData);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro ao carregar");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchHistory();
    return () => { cancelled = true; };
  }, [isOpen, productId]);

  // Calcula dimensões do gráfico SVG
  const W = 600;
  const H = 180;
  const PAD = 40;

  const points = history.length > 1 ? history : [];
  const prices = points.map((p) => p.price);
  const minP = Math.min(...prices, stats?.min_price || Infinity);
  const maxP = Math.max(...prices, stats?.max_price || 0);
  const range = maxP - minP || 1;

  const pathData = points.length > 0
    ? points
        .map((p, i) => {
          const x = PAD + (i / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
          const y = H - PAD - ((p.price - minP) / range) * (H - 2 * PAD);
          return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
        })
        .join(" ")
    : "";

  const areaPath = points.length > 0
    ? `${pathData} L ${(PAD + (W - 2 * PAD)).toFixed(1)} ${H - PAD} L ${PAD} ${H - PAD} Z`
    : "";

  function fmtBRL(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function fmtDate(iso: string) {
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  }

  return (
    <div className={styles.wrapper}>
      <button
        className={styles.toggle}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className={styles.icon}>📈</span>
        <span>Histórico de Preços</span>
        <span className={styles.chevron}>{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && (
        <div className={styles.panel}>
          {loading && <div className={styles.loading}>Carregando histórico...</div>}

          {error && <div className={styles.error}>Erro: {error}</div>}

          {!loading && !error && history.length === 0 && (
            <div className={styles.empty}>
              <p>📊 Ainda não há histórico suficiente para este produto.</p>
              <p className={styles.hint}>
                O histórico é construído automaticamente a cada atualização de preço
                (scrapers rodam diariamente).
              </p>
            </div>
          )}

          {!loading && !error && history.length > 0 && stats && (
            <>
              {/* Stats cards */}
              <div className={styles.statsRow}>
                <div className={`${styles.statCard} ${stats.is_best_price ? styles.bestPrice : ""}`}>
                  <span className={styles.statLabel}>Preço Atual</span>
                  <span className={styles.statValue}>{fmtBRL(stats.current_price)}</span>
                  {stats.is_best_price && (
                    <span className={styles.badge}>Menor preço histórico!</span>
                  )}
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Menor Preço</span>
                  <span className={styles.statValue}>{fmtBRL(stats.min_price)}</span>
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Maior Preço</span>
                  <span className={styles.statValue}>{fmtBRL(stats.max_price)}</span>
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Preço Médio</span>
                  <span className={styles.statValue}>{fmtBRL(stats.avg_price)}</span>
                </div>
              </div>

              {/* SVG Chart */}
              {points.length > 1 && (
                <div className={styles.chartContainer}>
                  <svg viewBox={`0 0 ${W} ${H}`} className={styles.chart} preserveAspectRatio="xMidYMid meet">
                    {/* Grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((t) => {
                      const y = PAD + t * (H - 2 * PAD);
                      const val = maxP - t * range;
                      return (
                        <g key={t}>
                          <line
                            x1={PAD} y1={y} x2={W - PAD} y2={y}
                            stroke="rgba(26,26,46,0.1)" strokeWidth={1}
                          />
                          <text
                            x={PAD - 8} y={y + 4} textAnchor="end"
                            fill="#6b6b8a" fontSize={10}
                          >
                            {fmtBRL(val)}
                          </text>
                        </g>
                      );
                    })}

                    {/* Area */}
                    <path d={areaPath} fill="url(#grad)" opacity={0.3} />
                    <defs>
                      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4ade80" />
                        <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
                      </linearGradient>
                    </defs>

                    {/* Line */}
                    <path d={pathData} fill="none" stroke="#4ade80" strokeWidth={2} />

                    {/* Points */}
                    {points.map((p, i) => {
                      const x = PAD + (i / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
                      const y = H - PAD - ((p.price - minP) / range) * (H - 2 * PAD);
                      return (
                        <circle
                          key={i}
                          cx={x} cy={y} r={3}
                          fill="#4ade80"
                          className={styles.point}
                        >
                          <title>{`${fmtBRL(p.price)} — ${fmtDate(p.recorded_at)}`}</title>
                        </circle>
                      );
                    })}

                    {/* X-axis labels (first, middle, last) */}
                    {points.length > 0 && [
                      { idx: 0, label: fmtDate(points[0].recorded_at) },
                      { idx: Math.floor(points.length / 2), label: fmtDate(points[Math.floor(points.length / 2)].recorded_at) },
                      { idx: points.length - 1, label: fmtDate(points[points.length - 1].recorded_at) },
                    ].map(({ idx, label }) => {
                      const x = PAD + (idx / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
                      return (
                        <text
                          key={idx}
                          x={x} y={H - PAD + 16} textAnchor="middle"
                          fill="#6b6b8a" fontSize={10}
                        >
                          {label}
                        </text>
                      );
                    })}
                  </svg>
                </div>
              )}

              <p className={styles.disclaimer}>
                * Menor preço histórico refere-se ao período monitorado pelo BestPriceToday,
                não necessariamente ao menor preço desde o lançamento do produto.
              </p>

              {/* History table */}
              <details className={styles.details}>
                <summary className={styles.summary}>
                  Ver todos os {history.length} registros
                </summary>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Preço</th>
                      <th>Variação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].reverse().map((p, i, arr) => {
                      const prev = arr[i + 1];
                      const diff = prev ? p.price - prev.price : 0;
                      const pct = prev ? ((p.price - prev.price) / prev.price) * 100 : 0;
                      return (
                        <tr key={i}>
                          <td>{new Date(p.recorded_at).toLocaleDateString("pt-BR")}</td>
                          <td className={styles.priceCell}>{fmtBRL(p.price)}</td>
                          <td className={diff < 0 ? styles.down : diff > 0 ? styles.up : styles.neutral}>
                            {diff !== 0 ? `${diff > 0 ? "+" : ""}${fmtBRL(diff)} (${pct > 0 ? "+" : ""}${pct.toFixed(1)}%)` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </details>
            </>
          )}
        </div>
      )}
    </div>
  );
}
