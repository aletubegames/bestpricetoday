"use client";

import { useState, useEffect } from "react";
import type { MouseEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import SearchBar from "@/components/search/SearchBar";
import OfferGrid from "@/components/offers/OfferGrid";
import { openTrackedOffer } from "@/lib/tracking";
import OfferSkeleton from "@/components/offers/OfferSkeleton";
import { useSearch } from "@/hooks/useSearch";
import { useTrendingSearches } from "@/hooks/useTrendingSearches";
import type { Offer, ProviderStatus } from "@/types";

import StoreChips from "@/components/home/StoreChips";
import StatsCards from "@/components/home/StatsCards";
import SearchesChart from "@/components/home/SearchesChart";
import TrustBadges from "@/components/home/TrustBadges";
import Testimonials from "@/components/home/Testimonials";
import FAQ from "@/components/home/FAQ";
import HowItWorks from "@/components/home/HowItWorks";
import FeaturedOffers from "@/components/home/FeaturedOffers";
import { CATEGORIES } from "@/lib/categories";
import { getChartData } from "@/lib/mockData";
import { API_BASE, apiFetch } from "@/lib/api";
import type { ChartDay } from "@/components/home/SearchesChart";
import styles from "./page.module.css";

type StoredUser = { name: string; is_admin: boolean };

function readStoredUser(): StoredUser | null {
  try {
    const stored = localStorage.getItem("bpt_user");
    if (!stored) return null;
    const parsed = JSON.parse(stored) as Partial<StoredUser>;
    if (parsed && typeof parsed === "object" && typeof parsed.name === "string" && typeof parsed.is_admin === "boolean") {
      return parsed as StoredUser;
    }
  } catch (error: unknown) {
    console.warn("Stored user could not be read:", error);
  }
  return null;
}

function AuthButton() {
  const [user, setUser] = useState<StoredUser | null>(null);
  useEffect(() => {
    setUser(readStoredUser());
  }, []);
  if (user) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {user.is_admin && (
          <a href="/afiliados" style={{
            display: "flex", alignItems: "center", gap: 5,
            fontSize: 12, fontWeight: 700, color: "#00e5a0",
            background: "rgba(0,229,160,0.1)", border: "1px solid rgba(0,229,160,0.3)",
            padding: "4px 12px", borderRadius: 99, textDecoration: "none",
          }}>
            💰 Afiliados
          </a>
        )}
        {user.is_admin && (
          <a href="/aletubegames" style={{
            display: "flex", alignItems: "center", gap: 5,
            fontSize: 12, fontWeight: 700, color: "#facc15",
            background: "rgba(250,204,21,0.1)", border: "1px solid rgba(250,204,21,0.3)",
            padding: "4px 12px", borderRadius: 99, textDecoration: "none",
          }}>
            🎥 AleTubeGames
          </a>
        )}
        <a href={user.is_admin ? "/admin" : "/dashboard"} style={{
          display: "flex", alignItems: "center", gap: 5,
          fontSize: 12, fontWeight: 700, color: "#a78bfa",
          background: "rgba(124,106,255,0.1)", border: "1px solid rgba(124,106,255,0.25)",
          padding: "4px 12px", borderRadius: 99, textDecoration: "none",
        }}>
          {user.is_admin ? "📊" : "👤"} {user.is_admin ? "Painel" : user.name.split(" ")[0]}
        </a>
      </div>
    );
  }
  return (
    <a href="/login" style={{
      display: "flex", alignItems: "center", gap: 5,
      fontSize: 12, fontWeight: 600, color: "var(--muted)",
      background: "var(--s2)", border: "1px solid var(--bd)",
      padding: "4px 12px", borderRadius: 99, textDecoration: "none",
    }}>
      Entrar
    </a>
  );
}

const PROVIDER_LABELS: Record<string, string> = {
  mercadolivre: "Mercado Livre",
  amazon: "Amazon",
  shopee: "Shopee",
  aliexpress: "AliExpress",
  lomadee: "Lomadee",
  awin: "Awin",
  kabum: "KaBuM",
};

const STATUS_META: Record<ProviderStatus["status"], { label: string; color: string; border: string; background: string }> = {
  ok: { label: "OK", color: "var(--grn)", border: "1px solid rgba(0,229,160,0.2)", background: "rgba(0,229,160,0.08)" },
  no_results: { label: "0 resultados", color: "var(--muted)", border: "1px solid var(--bd)", background: "var(--s2)" },
  not_configured: { label: "Sem credencial", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.25)", background: "rgba(245,158,11,0.08)" },
  blocked: { label: "Bloqueado", color: "var(--red)", border: "1px solid rgba(255,107,107,0.25)", background: "rgba(255,107,107,0.08)" },
  low_relevance: { label: "Baixa relevância", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.25)", background: "rgba(245,158,11,0.08)" },
  error: { label: "Erro", color: "var(--red)", border: "1px solid rgba(255,107,107,0.25)", background: "rgba(255,107,107,0.08)" },
};

const HIDDEN_STATUSES = new Set(["blocked", "not_configured", "error"]);

function ProviderStatusGrid({ statuses, offers }: { statuses: ProviderStatus[]; offers?: Offer[] }) {
  // Conta ofertas reais exibidas por provider (não o returned_count bruto do backend)
  const realCounts: Record<string, number> = {};
  if (offers) {
    for (const o of offers) {
      realCounts[o.provider] = (realCounts[o.provider] || 0) + 1;
    }
  }
  const visible = (statuses || []).filter(s => {
    const count = realCounts[s.provider] ?? 0;
    return count > 0;
  });
  if (!visible.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
      {visible.map((status) => {
        const meta = STATUS_META[status.status];
        const providerLabel = PROVIDER_LABELS[status.provider] || status.provider;
        const count = realCounts[status.provider] ?? 0;
        return (
          <div key={status.provider} style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: meta.background, border: meta.border,
            borderRadius: 99, padding: "6px 14px 6px 8px",
          }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{providerLabel}</span>
            {status.status === "ok" && (
              <span style={{ fontSize: 11, fontWeight: 700, color: meta.color, background: `${meta.color}18`, borderRadius: 99, padding: "1px 8px" }}>
                {count}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ children, maxWidth = 960 }: { children: React.ReactNode; maxWidth?: number }) {
  return (
    <section style={{ maxWidth, margin: "0 auto", padding: "0 20px" }}>
      {children}
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// HOME PAGE
// ═══════════════════════════════════════════════════════════════════════════════
async function fetchChartData(): Promise<ChartDay[]> {
  try {
    const resp = await apiFetch(`${API_BASE}/api/v1/stats`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const daily = data.daily_searches;
    if (daily && daily.length > 0 && daily.some((d: ChartDay) => d.value > 0)) {
      return daily;
    }
  } catch {
    // fallback to mock
  }
  return getChartData();
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, error } = useSearch(query);
  const { data: trendingData } = useTrendingSearches(20);
  const trending = trendingData?.items ?? [];
  const [compareList, setCompareList] = useState<Offer[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [openingCompareKey, setOpeningCompareKey] = useState<string | null>(null);
  const [compareErrorKey, setCompareErrorKey] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDay[]>(getChartData());

  useEffect(() => {
    fetchChartData().then(setChartData);
  }, []);

  const compareOfferKey = (offer: Offer, index: number) =>
    `${offer.provider}-${offer.product_id || offer.affiliate_url || index}`;

  const handleCompareOfferClick = async (event: MouseEvent<HTMLAnchorElement>, offer: Offer, index: number) => {
    event.preventDefault();
    if (!offer.affiliate_url) return;
    const key = compareOfferKey(offer, index);
    setOpeningCompareKey(key);
    setCompareErrorKey(null);
    try {
      await openTrackedOffer(offer, "compare_modal");
    } catch (error: unknown) {
      console.warn("Compare offer opening failed:", error);
      setCompareErrorKey(key);
    } finally {
      setOpeningCompareKey(null);
    }
  };

  const handleCompare = (offer: Offer) => {
    setCompareList(prev => {
      const current = prev || [];
      if (current.find(o => o.affiliate_url === offer.affiliate_url)) {
        return current.filter(o => o.affiliate_url !== offer.affiliate_url);
      }
      if (current.length >= 3) return current;
      return [...current, offer];
    });
  };

  const plural = (n: number) => n === 1 ? "oferta encontrada" : "ofertas encontradas";
  const showLanding = !query && !isLoading && !data;

  return (
    <div className={styles.root}>
      {/* Animações do logo */}
      <style>{`
        @keyframes logoFloat {
          0%, 100% { transform: perspective(900px) rotateY(-18deg) rotateX(10deg) translateY(0px); }
          50% { transform: perspective(900px) rotateY(-18deg) rotateX(10deg) translateY(-10px); }
        }
        @keyframes pulseGlow {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.08); }
        }
      `}</style>

      {/* ── HEADER ── */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.headerLeft}>
            <div className={styles.logoWrap}>
              <img
                src="/favicon-192.png"
                alt="BestPriceToday"
                width={124}
                height={124}
                className={styles.logoImg}
              />
              <div className={styles.logoText}>
                <span className={styles.logoBest}>BestPrice</span>
                <span className={styles.logoToday}>Today</span>
              </div>
            </div>
          </div>
          <div className={styles.headerRight}>
            <div className={styles.headerBadge}>
              <span className={styles.pulseDot} />
              Busca multi-loja
            </div>
            <a href="/alertas" className={styles.headerLink}>
              🔔 <span>Alertas</span>
            </a>
            <AuthButton />
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className={styles.hero}>
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className={styles.heroBadge}>
            ⚡ Comparação em tempo real
          </div>

          <div className={styles.heroGrid}>
            {/* Logo com glow ring + animação */}
            <div className={styles.heroLogoWrap}>
              <div className={styles.heroGlow} />
              <div className={styles.heroRing} />
              <img
                src="/logo.png"
                alt="BestPriceToday"
                width={157}
                height={157}
                className={styles.heroLogo}
              />
            </div>

            <div className={styles.heroText}>
              <h1 className={styles.heroTitle}>
                <span className={styles.heroTitleMain}>Menor preço</span><br />
                <span className={styles.heroTitleAccent}>do Brasil.</span>
              </h1>

              <p className={styles.heroSubtitle}>
                Busca automática em Mercado Livre, Amazon, Shopee e mais.
                Cupons aplicados na hora. Score de oferta real.
              </p>
            </div>
          </div>

          <SearchBar onSearch={setQuery} isLoading={isLoading} />

          {/* Trending pills */}
          {showLanding && trending.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} style={{ marginTop: 24 }}>
              <span style={{ fontSize: 12, color: "var(--muted2)", display: "block", marginBottom: 12, textAlign: "center" }}>
                Em alta:
              </span>
              <div style={{
                display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: 10, width: "min(100%, 960px)", margin: "0 auto",
              }}>
                {trending.map((item) => (
                  <button key={item.query} onClick={() => setQuery(item.query)}
                    style={{
                      fontSize: 12, fontWeight: 600, padding: "10px 14px", borderRadius: 14,
                      background: "#fff", border: "1px solid #e0e0f0",
                      color: "var(--muted)", cursor: "pointer", transition: "all .15s",
                      textAlign: "left", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minHeight: 42,
                    }}
                    title={item.query}
                    onMouseEnter={e => Object.assign(e.currentTarget.style, { borderColor: "rgba(124,58,237,.35)", color: "#7c3aed", background: "rgba(124,58,237,.04)", transform: "translateY(-1px)" })}
                    onMouseLeave={e => Object.assign(e.currentTarget.style, { borderColor: "#e0e0f0", color: "var(--muted)", background: "#fff", transform: "translateY(0)" })}
                  >
                    {item.query}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Store chips inline */}
          {showLanding && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
              style={{ marginTop: 20, display: "flex", alignItems: "center", justifyContent: "center", gap: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, color: "var(--muted2)" }}>Buscamos em:</span>
              <StoreChips compact />
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* ── LANDING SECTIONS (only when no search active) ── */}
      {showLanding && (
        <>
          {/* ── FEATURED OFFERS + CATEGORIES ── */}
          <section className={styles.section}>
            <FeaturedOffers onSearch={setQuery} />
          </section>

          {/* ── CATEGORIES HUB ── */}
          <section className={styles.section}>
            <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 20, textAlign: "center" }}>
              📂 Compre por categoria
            </h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
              {CATEGORIES.map(cat => (
                <a
                  key={cat.slug}
                  href={`/categoria/${cat.slug}`}
                  style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "12px 20px", borderRadius: 14,
                    background: "rgba(255,255,255,0.8)",
                    border: "1px solid rgba(108,92,231,0.15)",
                    color: "#1a1a2e", textDecoration: "none",
                    fontSize: 14, fontWeight: 600,
                  }}
                >
                  <span style={{ fontSize: 20 }}>{cat.icon}</span>
                  {cat.name}
                </a>
              ))}
            </div>
          </section>

          {/* ── HOW IT WORKS ── */}
          <section className={styles.section}>
            <HowItWorks />
          </section>
        </>
      )}

      {/* ── RESULTS ── */}
      {(isLoading || error || data) && (
      <section className={styles.searchSection}>
        <AnimatePresence mode="wait">
          {isLoading && <OfferSkeleton key="sk" />}

          {error && (
            <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className={styles.errorState}>
              <p className={styles.errorEmoji}>😕</p>
              <p className={styles.errorText}>Erro ao buscar. Tente novamente.</p>
            </motion.div>
          )}

          {data && !isLoading && (
            <motion.div key="res" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <div className={styles.resultMeta}>
                <p className={styles.resultCount}>{data.total} {plural(data.total)}</p>
                <span className={styles.resultBadge}>
                  {data.took_ms}ms
                </span>
                {data.cached && (
                  <span className={styles.resultCached}>⚡ cache</span>
                )}
              </div>
              <ProviderStatusGrid statuses={data.provider_statuses} offers={data.offers} />
              <OfferGrid offers={data.offers} onCompare={handleCompare} compareSelected={compareList.map(o => o.affiliate_url || "")} />
            </motion.div>
          )}
        </AnimatePresence>
      </section>
      )}

      {/* ── STATS + CHART ── */}
      {showLanding && (
        <section className={styles.statsSection}>
          <div className={styles.statsInner}>
            <h2 className={styles.statsTitle}>
              Em <span style={{ color: "#f97316" }}>números</span>
            </h2>
            <StatsCards />
            <div style={{ marginTop: 32 }}>
              <SearchesChart data={chartData} />
            </div>
          </div>
        </section>
      )}

      {/* ── TESTIMONIALS ── */}
      <section className={styles.section}>
        <Testimonials />
      </section>

      {/* ── FAQ ── */}
      <section className={styles.sectionBg}>
        <div className={styles.section}>
          <FAQ />
        </div>
      </section>

      {/* ── TRUST BADGES ── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Segurança e <span style={{ color: "#7c3aed" }}>confiança</span>
        </h2>
        <TrustBadges />
      </section>

      {/* ── FOOTER ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span>© {new Date().getFullYear()} BestPriceToday</span>
          <span className={styles.footerSeparator}>|</span>
          <a href="/terms" className={styles.footerLink}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Termos de Uso</a>
          <span className={styles.footerSeparator}>|</span>
          <a href="/privacy" className={styles.footerLink}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Política de Privacidade</a>
          <span className={styles.footerSeparator}>|</span>
          <a href="/deletion-status" className={styles.footerLink}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Solicitação de Exclusão</a>
          <span className={styles.footerSeparator}>|</span>
          <a href="mailto:aletubegames@gmail.com" className={styles.footerLink}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Contato</a>
        </div>
      </footer>

      {/* ── COMPARE BAR ── */}
      {compareList.length > 0 && (
        <div className={styles.compareBar}>
          <span className={styles.compareLabel}>
            ⊕ {compareList.length} selecionado{compareList.length > 1 ? "s" : ""}
          </span>
          {compareList.map(o => (
            <span key={o.affiliate_url} className={styles.compareChip}>
              {o.provider} — R${o.final_price?.toFixed(2)}
              <button onClick={() => handleCompare(o)} className={styles.compareChipBtn}>×</button>
            </span>
          ))}
          {compareList.length >= 2 && (
            <button onClick={() => setShowCompare(true)} className={styles.compareBtn}>
              Comparar →
            </button>
          )}
          <button onClick={() => setCompareList([])} className={styles.compareClear}>Limpar</button>
        </div>
      )}

      {/* ── COMPARE MODAL ── */}
      {showCompare && compareList.length >= 2 && (
        <div className={styles.compareOverlay} onClick={() => setShowCompare(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={styles.compareModal}
            style={{ "--cols": compareList.length } as React.CSSProperties}
            onClick={e => e.stopPropagation()}
          >
            <div className={styles.compareModalHeader}>
              <h2 className={styles.compareModalTitle}>
                Comparar ofertas
              </h2>
              <button onClick={() => setShowCompare(false)} className={styles.compareModalClose}>✕</button>
            </div>
            <div className={styles.compareModalGrid}>
              {compareList.map((offer, i) => (
                <div key={offer.affiliate_url} className={styles.compareItem}>
                  {offer.image_url && (
                    <img src={offer.image_url} alt="" className={styles.compareItemImg} />
                  )}
                  <p className={styles.compareItemTitle}>
                    {offer.title}
                  </p>
                  <div className={styles.compareItemPrice}>
                    R$ {offer.final_price?.toFixed(2) ?? "—"}
                  </div>
                  {offer.economy > 0.5 && (
                    <div className={styles.compareItemEconomy}>
                      ↓ Economize R$ {offer.economy.toFixed(2)}
                    </div>
                  )}
                  <a
                    href={offer.affiliate_url ?? "#"}
                    onClick={(e) => handleCompareOfferClick(e, offer, i)}
                    target="_blank"
                    rel="noopener noreferrer sponsored"
                    className={styles.compareItemLink}
                    style={{
                      background: i === 0 ? "linear-gradient(135deg,#7c3aed,#a78bfa)" : "#f5f5ff",
                      color: i === 0 ? "#fff" : "#7c3aed",
                      border: i === 0 ? "none" : "1px solid rgba(124,58,237,0.2)",
                    }}
                  >
                    {openingCompareKey === compareOfferKey(offer, i) ? "Abrindo..." : "Ver oferta →"}
                  </a>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
