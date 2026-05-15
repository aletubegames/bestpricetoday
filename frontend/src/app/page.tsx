"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import SearchBar from "@/components/search/SearchBar";
import OfferGrid from "@/components/offers/OfferGrid";
import OfferSkeleton from "@/components/offers/OfferSkeleton";
import { useSearch } from "@/hooks/useSearch";
import { useTrendingSearches } from "@/hooks/useTrendingSearches";
import type { ProviderStatus } from "@/types";

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
  ok: {
    label: "OK",
    color: "var(--grn)",
    border: "1px solid rgba(0,229,160,0.2)",
    background: "rgba(0,229,160,0.08)",
  },
  no_results: {
    label: "0 resultados",
    color: "var(--muted)",
    border: "1px solid var(--bd)",
    background: "var(--s2)",
  },
  not_configured: {
    label: "Sem credencial",
    color: "#f59e0b",
    border: "1px solid rgba(245,158,11,0.25)",
    background: "rgba(245,158,11,0.08)",
  },
  blocked: {
    label: "Bloqueado",
    color: "var(--red)",
    border: "1px solid rgba(255,107,107,0.25)",
    background: "rgba(255,107,107,0.08)",
  },
  low_relevance: {
    label: "Baixa relevância",
    color: "#f59e0b",
    border: "1px solid rgba(245,158,11,0.25)",
    background: "rgba(245,158,11,0.08)",
  },
  error: {
    label: "Erro",
    color: "var(--red)",
    border: "1px solid rgba(255,107,107,0.25)",
    background: "rgba(255,107,107,0.08)",
  },
};

function formatProviderNumbers(status: ProviderStatus) {
  const parts: string[] = [];
  if (status.returned_count) parts.push(`${status.returned_count} relevantes`);
  if (status.filtered_count) parts.push(`${status.filtered_count} filtrados`);
  if (status.raw_count && !status.returned_count) parts.push(`${status.raw_count} brutos`);
  if (status.http_status) parts.push(`HTTP ${status.http_status}`);
  return parts.join(" • ");
}

function ProviderStatusGrid({ statuses }: { statuses: ProviderStatus[] }) {
  if (!statuses.length) return null;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: 12,
        marginBottom: 20,
      }}
    >
      {statuses.map((status) => {
        const meta = STATUS_META[status.status];
        const providerLabel = PROVIDER_LABELS[status.provider] || status.provider;
        const numbers = formatProviderNumbers(status);

        return (
          <div
            key={status.provider}
            style={{
              background: meta.background,
              border: meta.border,
              borderRadius: "var(--r)",
              padding: "14px 16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
              <strong style={{ fontSize: 14 }}>{providerLabel}</strong>
              <span style={{ fontSize: 11, fontWeight: 700, color: meta.color }}>{meta.label}</span>
            </div>
            {status.message && (
              <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
                {status.message}
              </p>
            )}
            {numbers && (
              <p style={{ fontSize: 11, color: "var(--muted2)", margin: "8px 0 0" }}>
                {numbers}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, error } = useSearch(query);
  const { data: trendingData } = useTrendingSearches(20);
  const trending = trendingData?.items ?? [];

  const plural = (n: number) => n === 1 ? "oferta encontrada" : "ofertas encontradas";

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>

      {/* ── TOPBAR ── */}
      <header style={{
        position: "sticky", top: 0, zIndex: 50,
        borderBottom: "1px solid var(--bd)",
        background: "rgba(7,7,15,0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 20px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 24 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 17, letterSpacing: "-0.4px" }}>
              BestPrice<span style={{ color: "var(--acc2)" }}>Today</span>
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              fontSize: 12, fontWeight: 500, color: "var(--grn)",
              background: "rgba(0,229,160,0.08)",
              border: "1px solid rgba(0,229,160,0.2)",
              padding: "4px 12px", borderRadius: 99,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--grn)", animation: "pulse 2s infinite" }} />
              7 lojas ao vivo
            </div>
            <a href="/alertas" style={{
              display: "flex", alignItems: "center", gap: 5,
              fontSize: 12, fontWeight: 600, color: "var(--muted)",
              background: "var(--s2)", border: "1px solid var(--bd)",
              padding: "4px 12px", borderRadius: 99, textDecoration: "none",
              transition: "color .15s",
            }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--txt)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--muted)")}>
              🔔 Alertas
            </a>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section style={{ maxWidth: 720, margin: "0 auto", padding: "56px 20px 40px", textAlign: "center" }}>
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>

          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 12, fontWeight: 600, letterSpacing: ".04em",
            color: "var(--acc2)",
            background: "rgba(124,106,255,0.1)",
            border: "1px solid rgba(124,106,255,0.2)",
            padding: "5px 14px", borderRadius: 99,
            marginBottom: 28, textTransform: "uppercase",
          }}>
            ⚡ Comparação em tempo real
          </div>

          <h1 style={{
            fontSize: "clamp(2.4rem, 7vw, 4.5rem)",
            fontWeight: 900,
            lineHeight: 1.05,
            letterSpacing: "-0.03em",
            marginBottom: 18,
          }}>
            <span style={{ color: "var(--txt)" }}>Menor preço</span><br />
            <span style={{
              background: "linear-gradient(135deg, #7c6aff 0%, #a78bfa 50%, #e879f9 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}>do Brasil.</span>
          </h1>

          <p style={{ fontSize: 16, color: "var(--muted)", lineHeight: 1.7, marginBottom: 40, maxWidth: 480, margin: "0 auto 40px" }}>
            Busca automática em Mercado Livre, Amazon, Shopee e mais.
            Cupons aplicados na hora. Score de oferta real.
          </p>

          <SearchBar onSearch={setQuery} isLoading={isLoading} />

          {/* Trending pills */}
          {!query && trending.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
              style={{ marginTop: 24, textAlign: "left" }}
            >
              <span style={{ fontSize: 12, color: "var(--muted2)", display: "block", marginBottom: 12, textAlign: "center" }}>
                Em alta:
              </span>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                  gap: 10,
                  width: "min(100%, 960px)",
                  margin: "0 auto",
                }}
              >
                {trending.map((item) => (
                  <button key={item.query} onClick={() => setQuery(item.query)}
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      padding: "10px 14px",
                      borderRadius: 14,
                      background: "var(--s2)",
                      border: "1px solid var(--bd)",
                      color: "var(--muted)",
                      cursor: "pointer",
                      transition: "all .15s",
                      textAlign: "left",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      minHeight: 42,
                    }}
                    title={item.query}
                    onMouseEnter={e => Object.assign(e.currentTarget.style, { borderColor: "rgba(124,106,255,.4)", color: "var(--acc2)", background: "rgba(124,106,255,.06)", transform: "translateY(-1px)" })}
                    onMouseLeave={e => Object.assign(e.currentTarget.style, { borderColor: "var(--bd)", color: "var(--muted)", background: "var(--s2)", transform: "translateY(0)" })}
                  >
                    {item.query}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* ── RESULTS ── */}
      <section style={{ maxWidth: 1200, margin: "0 auto", padding: "0 20px 80px" }}>
        <AnimatePresence mode="wait">
          {isLoading && <OfferSkeleton key="sk" />}

          {error && (
            <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ textAlign: "center", padding: "80px 20px" }}>
              <p style={{ fontSize: 40, marginBottom: 12 }}>😕</p>
              <p style={{ color: "var(--red)", fontSize: 14 }}>Erro ao buscar. Tente novamente.</p>
            </motion.div>
          )}

          {data && !isLoading && (
            <motion.div key="res" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              {/* Results header */}
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
                <p style={{ fontWeight: 700, fontSize: 15 }}>
                  {data.total} {plural(data.total)}
                </p>
                <span style={{
                  fontSize: 11, fontWeight: 600,
                  padding: "3px 10px", borderRadius: 99,
                  background: "var(--s2)", border: "1px solid var(--bd)",
                  color: "var(--muted2)",
                }}>
                  {data.took_ms}ms
                </span>
                {data.cached && (
                  <span style={{
                    fontSize: 11, fontWeight: 600,
                    padding: "3px 10px", borderRadius: 99,
                    background: "rgba(0,229,160,0.08)",
                    border: "1px solid rgba(0,229,160,0.2)",
                    color: "var(--grn)",
                  }}>⚡ cache</span>
                )}
              </div>
              <ProviderStatusGrid statuses={data.provider_statuses} />
              <OfferGrid offers={data.offers} />
            </motion.div>
          )}

          {/* Empty hero stats */}
          {!query && !isLoading && !data && (
            <motion.div key="hero-stats" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: 12, marginTop: 8,
              }}>
              {[
                { v: "7+", l: "Lojas" },
                { v: "<3s", l: "Resultado" },
                { v: "IA", l: "Anti-falso desc." },
                { v: "100%", l: "Gratuito" },
              ].map(s => (
                <div key={s.l} style={{
                  background: "var(--s2)", border: "1px solid var(--bd)",
                  borderRadius: "var(--r)", padding: "20px 16px", textAlign: "center",
                }}>
                  <div style={{ fontSize: 26, fontWeight: 900, color: "var(--acc2)", marginBottom: 4 }}>{s.v}</div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>{s.l}</div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{
        borderTop: "1px solid var(--bd)",
        background: "rgba(7,7,15,0.85)",
        padding: "20px",
        textAlign: "center",
      }}>
        <div style={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 24,
          flexWrap: "wrap",
          fontSize: 13,
          color: "var(--muted2)",
        }}>
          <span>© {new Date().getFullYear()} BestPriceToday</span>
          <span style={{ color: "var(--bd)" }}>|</span>
          <a href="/terms" style={{ color: "var(--muted2)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--acc2)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--muted2)")}
          >Termos de Uso</a>
          <span style={{ color: "var(--bd)" }}>|</span>
          <a href="/privacy" style={{ color: "var(--muted2)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--acc2)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--muted2)")}
          >Política de Privacidade</a>
          <span style={{ color: "var(--bd)" }}>|</span>
          <a href="mailto:aletubegames@gmail.com" style={{ color: "var(--muted2)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--acc2)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--muted2)")}
          >Contato</a>
        </div>
      </footer>
    </div>
  );
}
