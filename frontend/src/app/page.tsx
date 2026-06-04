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
          {user.is_admin ? "👑" : "👤"} {user.name.split(" ")[0]}
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

function ProviderStatusGrid({ statuses }: { statuses: ProviderStatus[] }) {
  const visible = statuses.filter(s => (s.returned_count ?? 0) > 0);
  if (!visible.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
      {visible.map((status) => {
        const meta = STATUS_META[status.status];
        const providerLabel = PROVIDER_LABELS[status.provider] || status.provider;
        const count = status.returned_count || 0;
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
export default function HomePage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, error } = useSearch(query);
  const { data: trendingData } = useTrendingSearches(20);
  const trending = trendingData?.items ?? [];
  const [compareList, setCompareList] = useState<Offer[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [openingCompareKey, setOpeningCompareKey] = useState<string | null>(null);
  const [compareErrorKey, setCompareErrorKey] = useState<string | null>(null);

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
      if (prev.find(o => o.affiliate_url === offer.affiliate_url)) {
        return prev.filter(o => o.affiliate_url !== offer.affiliate_url);
      }
      if (prev.length >= 3) return prev;
      return [...prev, offer];
    });
  };

  const plural = (n: number) => n === 1 ? "oferta encontrada" : "ofertas encontradas";

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>

      {/* ── HEADER ── */}
      <header style={{
        position: "sticky", top: 0, zIndex: 50,
        borderBottom: "1px solid var(--bd)",
        background: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}>
        <div style={{
          maxWidth: 1200, margin: "0 auto", padding: "0 20px", height: 60,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <img src="/logo.png" alt="BestPriceToday" width={56} height={56} style={{ borderRadius: 8, objectFit: "contain" }} />
            <div style={{
              fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
              fontWeight: 900, fontSize: 20, letterSpacing: "-0.6px",
              display: "flex", flexDirection: "column", gap: 0, lineHeight: 0.9, textAlign: "center",
            }}>
              <span style={{
                background: "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>BestPrice</span>
              <span style={{ color: "#000000", fontSize: 18, fontWeight: 900 }}>Today</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              fontSize: 12, fontWeight: 500, color: "#7c3aed",
              background: "rgba(124,58,237,0.08)",
              border: "1px solid rgba(124,58,237,0.18)",
              padding: "4px 12px", borderRadius: 99,
            }}>
              <span className="pulse-dot" style={{
                width: 6, height: 6, borderRadius: "50%", background: "#00b894",
              }} />
              Busca multi-loja
            </div>
            <a href="/alertas" style={{
              display: "flex", alignItems: "center", gap: 5,
              fontSize: 12, fontWeight: 600, color: "var(--muted)",
              background: "var(--s2)", border: "1px solid var(--bd)",
              padding: "4px 12px", borderRadius: 99, textDecoration: "none",
              transition: "color .15s",
            }}>
              🔔 Alertas
            </a>
            <AuthButton />
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section style={{ maxWidth: 720, margin: "0 auto", padding: "56px 20px 40px", textAlign: "center" }}>
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 12, fontWeight: 600, letterSpacing: ".04em",
            color: "#7c3aed",
            background: "rgba(124,58,237,0.08)",
            border: "1px solid rgba(124,58,237,0.18)",
            padding: "5px 14px", borderRadius: 99,
            marginBottom: 28, textTransform: "uppercase",
          }}>
            ⚡ Comparação em tempo real
          </div>

          <h1 style={{
            fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
            fontSize: "clamp(2.4rem, 7vw, 4.5rem)",
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: "-0.03em",
            marginBottom: 18,
          }}>
            <span style={{ color: "var(--txt)" }}>Menor preço</span><br />
            <span style={{
              background: "linear-gradient(135deg, #7c3aed 0%, #a78bfa 50%, #c084fc 100%)",
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
        </motion.div>
      </section>

      {/* ── STORE CHIPS ── */}
      <section style={{ padding: "0 20px 32px", maxWidth: 800, margin: "0 auto" }}>
        <StoreChips />
      </section>

      {/* ── STATS CARDS ── */}
      <section style={{ maxWidth: 800, margin: "0 auto", padding: "0 20px 32px" }}>
        <StatsCards />
      </section>

      {/* ── RESULTS ── */}
      <section style={{ maxWidth: 1200, margin: "0 auto", padding: "0 20px 32px" }}>
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
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
                <p style={{ fontWeight: 700, fontSize: 15 }}>{data.total} {plural(data.total)}</p>
                <span style={{ fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 99, background: "var(--s2)", border: "1px solid var(--bd)", color: "var(--muted2)" }}>
                  {data.took_ms}ms
                </span>
                {data.cached && (
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 99, background: "rgba(0,229,160,0.08)", border: "1px solid rgba(0,229,160,0.2)", color: "var(--grn)" }}>⚡ cache</span>
                )}
              </div>
              <ProviderStatusGrid statuses={data.provider_statuses} />
              <OfferGrid offers={data.offers} onCompare={handleCompare} compareSelected={compareList.map(o => o.affiliate_url || "")} />
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* ── SEARCHES CHART ── */}
      {!query && !isLoading && !data && (
        <section style={{ maxWidth: 800, margin: "0 auto", padding: "0 20px 32px" }}>
          <SearchesChart />
        </section>
      )}

      {/* ── TRUST BADGES ── */}
      <section style={{ maxWidth: 960, margin: "0 auto", padding: "0 20px 32px" }}>
        <TrustBadges />
      </section>

      {/* ── TESTIMONIALS ── */}
      <section style={{ maxWidth: 960, margin: "0 auto", padding: "0 20px 32px" }}>
        <Testimonials />
      </section>

      {/* ── FAQ ── */}
      <section style={{ maxWidth: 960, margin: "0 auto", padding: "0 20px 60px" }}>
        <FAQ />
      </section>

      {/* ── FOOTER ── */}
      <footer style={{
        borderTop: "1px solid #e0e0f0",
        background: "#fff",
        padding: "24px 20px",
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
          color: "rgba(26,26,46,0.45)",
        }}>
          <span>© {new Date().getFullYear()} BestPriceToday</span>
          <span style={{ color: "rgba(26,26,46,0.15)" }}>|</span>
          <a href="/terms" style={{ color: "rgba(26,26,46,0.45)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Termos de Uso</a>
          <span style={{ color: "rgba(26,26,46,0.15)" }}>|</span>
          <a href="/privacy" style={{ color: "rgba(26,26,46,0.45)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Política de Privacidade</a>
          <span style={{ color: "rgba(26,26,46,0.15)" }}>|</span>
          <a href="/deletion-status" style={{ color: "rgba(26,26,46,0.45)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Solicitação de Exclusão</a>
          <span style={{ color: "rgba(26,26,46,0.15)" }}>|</span>
          <a href="mailto:aletubegames@gmail.com" style={{ color: "rgba(26,26,46,0.45)", textDecoration: "none" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#7c3aed")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,46,0.45)")}
          >Contato</a>
        </div>
      </footer>

      {/* ── COMPARE BAR ── */}
      {compareList.length > 0 && (
        <div style={{
          position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 100,
          background: "rgba(255,255,255,0.97)", backdropFilter: "blur(20px)",
          borderTop: "1px solid rgba(124,58,237,0.3)",
          padding: "12px 24px", display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap",
        }}>
          <span style={{ color: "#7c3aed", fontWeight: 700, fontSize: 14 }}>
            ⊕ {compareList.length} selecionado{compareList.length > 1 ? "s" : ""}
          </span>
          {compareList.map(o => (
            <span key={o.affiliate_url} style={{
              background: "#f5f5ff", border: "1px solid rgba(124,58,237,0.2)",
              borderRadius: 8, padding: "4px 10px", fontSize: 12, color: "#1a1a2e",
              display: "flex", alignItems: "center", gap: 6,
            }}>
              {o.provider} — R${o.final_price?.toFixed(2)}
              <button onClick={() => handleCompare(o)} style={{ background: "none", border: "none", color: "#6b6b8a", cursor: "pointer", fontSize: 14 }}>×</button>
            </span>
          ))}
          {compareList.length >= 2 && (
            <button onClick={() => setShowCompare(true)} style={{
              marginLeft: "auto", padding: "8px 20px", borderRadius: 10,
              background: "linear-gradient(135deg,#7c3aed,#a78bfa)",
              color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer",
            }}>
              Comparar →
            </button>
          )}
          <button onClick={() => setCompareList([])} style={{ background: "none", border: "none", color: "#6b6b8a", cursor: "pointer", fontSize: 14 }}>Limpar</button>
        </div>
      )}

      {/* ── COMPARE MODAL ── */}
      {showCompare && compareList.length >= 2 && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(0,0,0,0.5)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
        }} onClick={() => setShowCompare(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              background: "#fff", borderRadius: 20, padding: "32px",
              maxWidth: 900, width: "100%", maxHeight: "80vh", overflowY: "auto",
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif", fontSize: 22, fontWeight: 800, color: "#1a1a2e" }}>
                Comparar ofertas
              </h2>
              <button onClick={() => setShowCompare(false)} style={{
                background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6b6b8a",
              }}>✕</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${compareList.length}, 1fr)`, gap: 16 }}>
              {compareList.map((offer, i) => (
                <div key={offer.affiliate_url} style={{
                  border: "1px solid #e0e0f0", borderRadius: 14, padding: 16,
                }}>
                  {offer.image_url && (
                    <img src={offer.image_url} alt="" style={{ width: "100%", height: 120, objectFit: "contain", borderRadius: 8, marginBottom: 12 }} />
                  )}
                  <p style={{ fontSize: 13, fontWeight: 600, color: "#1a1a2e", marginBottom: 8, lineHeight: 1.4 }}>
                    {offer.title}
                  </p>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "#7c3aed", marginBottom: 4 }}>
                    R$ {offer.final_price?.toFixed(2) ?? "—"}
                  </div>
                  {offer.economy > 0.5 && (
                    <div style={{ fontSize: 12, color: "#00b894", fontWeight: 600, marginBottom: 8 }}>
                      ↓ Economize R$ {offer.economy.toFixed(2)}
                    </div>
                  )}
                  <a
                    href={offer.affiliate_url ?? "#"}
                    onClick={(e) => handleCompareOfferClick(e, offer, i)}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "block", textAlign: "center", padding: "10px",
                      background: i === 0 ? "linear-gradient(135deg,#7c3aed,#a78bfa)" : "#f5f5ff",
                      color: i === 0 ? "#fff" : "#7c3aed",
                      borderRadius: 10, textDecoration: "none", fontWeight: 700, fontSize: 13,
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
