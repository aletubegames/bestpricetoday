"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import styles from "./PriceHistoryPublic.module.css";

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
  title: string;
}

interface Props {
  affiliateUrl: string;
  compact?: boolean;
}

export default function PriceHistoryPublic({ affiliateUrl, compact = false }: Props) {
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [stats, setStats] = useState<PriceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;

    async function fetchHistory() {
      try {
        setLoading(true);
        const res = await fetch(
          `${API_BASE}/api/v1/affiliate/history-by-url?url=${encodeURIComponent(affiliateUrl)}&days=365`
        );
        if (!res.ok) throw new Error("Falha");
        const data = await res.json();
        if (!cancelled) {
          setHistory(data.history || []);
          setStats(data.stats || null);
        }
      } catch {
        if (!cancelled) setHistory([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchHistory();
    return () => { cancelled = true; };
  }, [isOpen, affiliateUrl]);

  function fmtBRL(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function fmtDate(iso: string) {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  }

  // SVG chart
  const W = 500;
  const H = compact ? 120 : 160;
  const PAD = 35;
  const points = history.length > 1 ? history : [];
  const prices = points.map((p) => p.price);
  const minP = Math.min(...prices, stats?.min_price || Infinity);
  const maxP = Math.max(...prices, stats?.max_price || 0);
  const range = maxP - minP || 1;

  const pathData = points.length > 0
    ? points.map((p, i) => {
        const x = PAD + (i / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
        const y = H - PAD - ((p.price - minP) / range) * (H - 2 * PAD);
        return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(" ")
    : "";

  const areaPath = points.length > 0
    ? `${pathData} L ${(PAD + (W - 2 * PAD)).toFixed(1)} ${H - PAD} L ${PAD} ${H - PAD} Z`
    : "";

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

          {!loading && history.length === 0 && (
            <div className={styles.empty}>
              <p>📊 Ainda não há histórico suficiente para este produto.</p>
              <p className={styles.hint}>
                O histórico é construído automaticamente com atualizações diárias de preço.
              </p>
            </div>
          )}

          {!loading && history.length > 0 && stats && (
            <>
              {/* Stats */}
              <div className={styles.statsRow}>
                <div className={`${styles.statCard} ${stats.is_best_price ? styles.bestPrice : ""}`}>
                  <span className={styles.statLabel}>Atual</span>
                  <span className={styles.statValue}>{fmtBRL(stats.current_price)}</span>
                  {stats.is_best_price && <span className={styles.badge}>Menor preço!</span>}
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Mínimo</span>
                  <span className={styles.statValue}>{fmtBRL(stats.min_price)}</span>
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Máximo</span>
                  <span className={styles.statValue}>{fmtBRL(stats.max_price)}</span>
                </div>
                <div className={styles.statCard}>
                  <span className={styles.statLabel}>Média</span>
                  <span className={styles.statValue}>{fmtBRL(stats.avg_price)}</span>
                </div>
              </div>

              {/* Chart */}
              {points.length > 1 && (
                <div className={styles.chartContainer}>
                  <svg viewBox={`0 0 ${W} ${H}`} className={styles.chart} preserveAspectRatio="xMidYMid meet">
                    {[0, 0.5, 1].map((t) => {
                      const y = PAD + t * (H - 2 * PAD);
                      const val = maxP - t * range;
                      return (
                        <g key={t}>
                          <line x1={PAD} y1={y} x2={W - PAD} y2={y} stroke="rgba(26,26,46,0.1)" strokeWidth={1} />
                          <text x={PAD - 6} y={y + 3} textAnchor="end" fill="#6b6b8a" fontSize={9}>
                            {fmtBRL(val)}
                          </text>
                        </g>
                      );
                    })}
                    <path d={areaPath} fill="url(#gradPub)" opacity={0.3} />
                    <defs>
                      <linearGradient id="gradPub" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4ade80" />
                        <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <path d={pathData} fill="none" stroke="#4ade80" strokeWidth={2} />
                    {points.map((p, i) => {
                      const x = PAD + (i / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
                      const y = H - PAD - ((p.price - minP) / range) * (H - 2 * PAD);
                      return (
                        <circle key={i} cx={x} cy={y} r={3} fill="#4ade80" className={styles.point}>
                          <title>{`${fmtBRL(p.price)} — ${fmtDate(p.recorded_at)}`}</title>
                        </circle>
                      );
                    })}
                    {points.length > 0 && [
                      { idx: 0, label: fmtDate(points[0].recorded_at) },
                      { idx: points.length - 1, label: fmtDate(points[points.length - 1].recorded_at) },
                    ].map(({ idx, label }) => {
                      const x = PAD + (idx / Math.max(points.length - 1, 1)) * (W - 2 * PAD);
                      return (
                        <text key={idx} x={x} y={H - PAD + 14} textAnchor="middle" fill="#6b6b8a" fontSize={9}>
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
            </>
          )}
        </div>
      )}
    </div>
  );
}
