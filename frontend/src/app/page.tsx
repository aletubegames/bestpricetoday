"use client";

import { useState, useEffect } from "react";
import type { MouseEvent } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import Header from "@/components/layout/Header";
import SearchBar from "@/components/search/SearchBar";
import OfferGrid from "@/components/offers/OfferGrid";
import { openTrackedOffer } from "@/lib/tracking";
import { trackSearch } from "@/lib/analytics";
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
import WhyUs from "@/components/home/WhyUs";
import { CATEGORIES } from "@/lib/categories";
import { getChartData } from "@/lib/mockData";
import { API_BASE, apiFetch } from "@/lib/api";
import type { ChartDay } from "@/components/home/SearchesChart";
import styles from "./page.module.css";

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
    <div className={styles.providerGrid}>
      {visible.map((status) => {
        const meta = STATUS_META[status.status];
        const providerLabel = PROVIDER_LABELS[status.provider] || status.provider;
        const count = realCounts[status.provider] ?? 0;
        return (
          <div key={status.provider} className={styles.providerChip} style={{ background: meta.background, border: meta.border }}>
            <span className={styles.providerName}>{providerLabel}</span>
            {status.status === "ok" && (
              <span className={styles.providerCount} style={{ color: meta.color, background: `${meta.color}18` }}>
                {count}
              </span>
            )}
          </div>
        );
      })}
    </div>
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
  const handleSearch = (q: string) => {
    if (q && q.trim()) trackSearch(q.trim());
    setQuery(q);
  };
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

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      { "@type": "Question", "name": "O preço aqui é maior do que na loja?", "acceptedAnswer": { "@type": "Answer", "text": "Não. O link leva direto pra plataforma oficial pelo mesmo preço. Nunca cobramos nada a mais." } },
      { "@type": "Question", "name": "Como vocês ganham dinheiro?", "acceptedAnswer": { "@type": "Answer", "text": "Recebemos comissão da plataforma quando você compra pelo nosso link. Esse valor é pago pela loja, não por você." } },
      { "@type": "Question", "name": "Os preços são atualizados em tempo real?", "acceptedAnswer": { "@type": "Answer", "text": "Sim. Nossa busca roda automaticamente e exibe o preço atual de cada plataforma no momento da sua pesquisa." } },
      { "@type": "Question", "name": "A compra é feita aqui no site?", "acceptedAnswer": { "@type": "Answer", "text": "Não. Você é redirecionado para Shopee, Mercado Livre, AliExpress ou Lomadee e compra com toda a proteção e garantia delas." } },
      { "@type": "Question", "name": "Vocês têm todos os produtos?", "acceptedAnswer": { "@type": "Answer", "text": "Monitoramos mais de 10.000 produtos. Se não encontrar, tente termos diferentes ou volte em breve — adicionamos novos regularmente." } },
      { "@type": "Question", "name": "É seguro comprar pelo link de vocês?", "acceptedAnswer": { "@type": "Answer", "text": "Sim. Você compra diretamente na plataforma oficial. Nós apenas mostramos onde está mais barato." } },
    ],
  };

  return (
    <div className={styles.root}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <Header variant="default" />

      <main>
      {/* ── HERO ── */}
      <section className={styles.hero}>
        <motion.div className={styles.heroInner} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className={styles.heroBadge}>
            ⚡ Comparação em tempo real
          </div>

          <h1 className={styles.heroTitle}>
            <span className={styles.heroTitleMain}>Menor preço</span><br />
            <span className={styles.heroTitleAccent}>do Brasil.</span>
          </h1>

          <p className={styles.heroSubtitle}>
            Busca automática em Mercado Livre, Amazon, Shopee e mais.
            Histórico de preços e alertas de queda. Score de oferta real.
          </p>

          <div className={styles.heroSearch}>
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />
          </div>

          {/* Trending pills */}
          {showLanding && trending.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className={styles.trending}>
              <span className={styles.trendingLabel}>Em alta:</span>
              <div className={styles.trendingPills}>
                {trending.map((item) => (
                  <button key={item.query} onClick={() => handleSearch(item.query)} className={styles.trendingPill} title={item.query}>
                    {item.query}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Store chips inline */}
          {showLanding && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className={styles.heroStores}>
              <span className={styles.heroStoresLabel}>Buscamos em:</span>
              <StoreChips compact />
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* ── LANDING SECTIONS (only when no search active) ── */}
      {showLanding && (
        <>
          {/* ── FEATURED OFFERS + CATEGORIES ── */}
          <section className={styles.sectionWhite}>
            <div className={styles.sectionInner}>
              <FeaturedOffers onSearch={handleSearch} />
            </div>
          </section>

          {/* ── CATEGORIES HUB ── */}
          <section className={styles.sectionWhite}>
            <div className={styles.sectionInner}>
              <h2 className={styles.sectionHeading}>
                📂 Compre por categoria
              </h2>
              <div className={styles.categoryGrid}>
                {CATEGORIES.map(cat => (
                  <a key={cat.slug} href={`/categoria/${cat.slug}`} className={styles.categoryCard}>
                    <span className={styles.categoryIcon}>{cat.icon}</span>
                    {cat.name}
                  </a>
                ))}
              </div>
            </div>
          </section>

          {/* ── WHY US (histórico de preços como diferencial) ── */}
          <section className={styles.sectionMuted}>
            <div className={styles.sectionInner}>
              <WhyUs />
            </div>
          </section>

          {/* ── HOW IT WORKS ── */}
          <section className={styles.sectionWhite}>
            <div className={styles.sectionInner}>
              <HowItWorks />
            </div>
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
        <section className={styles.sectionMuted}>
          <div className={styles.sectionInner}>
            <h2 className={styles.sectionHeading}>
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
      <section className={styles.sectionWhite}>
        <div className={styles.sectionInner}>
          <Testimonials />
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className={styles.sectionMuted}>
        <div className={styles.sectionInner}>
          <FAQ />
        </div>
      </section>

      {/* ── TRUST BADGES ── */}
      <section className={styles.sectionWhite}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionHeading}>
            Segurança e <span style={{ color: "#7c3aed" }}>confiança</span>
          </h2>
          <TrustBadges />
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className={styles.footerDark}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <a href="/" className={styles.footerLogo}>
              <img
                src="/logo-header.png"
                alt="BestPriceToday"
                width={50}
                height={50}
                className={styles.footerLogoImg}
              />
              <span className={styles.footerLogoText}>
                <span className={styles.footerLogoBest}>BestPrice</span>
                <span className={styles.footerLogoToday}>Today</span>
              </span>
            </a>
            <p className={styles.footerTagline}>Encontre o menor preço do Brasil em segundos.</p>
          </div>
          <div className={styles.footerCol}>
            <h4 className={styles.footerColTitle}>Navegue</h4>
            <a href="/" className={styles.footerLink}>Buscar ofertas</a>
            <a href="/alertas" className={styles.footerLink}>Alertas de preço</a>
            <a href="/cupons" className={styles.footerLink}>Produtos com cupom</a>
          </div>
          <div className={styles.footerCol}>
            <h4 className={styles.footerColTitle}>Legal</h4>
            <a href="/terms" className={styles.footerLink}>Termos de Uso</a>
            <a href="/privacy" className={styles.footerLink}>Política de Privacidade</a>
            <a href="/deletion-status" className={styles.footerLink}>Solicitação de Exclusão</a>
          </div>
          <div className={styles.footerCol}>
            <h4 className={styles.footerColTitle}>Contato</h4>
            <a href="mailto:aletubegames@gmail.com" className={styles.footerLink}>aletubegames@gmail.com</a>
          </div>
        </div>
        <div className={styles.footerBottom}>
          <span>© {new Date().getFullYear()} BestPriceToday. Todos os direitos reservados.</span>
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
              <button onClick={() => handleCompare(o)} className={styles.compareChipBtn} aria-label="Remover da comparação">×</button>
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
              <button onClick={() => setShowCompare(false)} className={styles.compareModalClose} aria-label="Fechar modal">✕</button>
            </div>
            <div className={styles.compareModalGrid}>
              {compareList.map((offer, i) => (
                <div key={offer.affiliate_url} className={styles.compareItem}>
                  {offer.image_url && (
                    <div className={styles.compareItemImg}>
                      <Image src={offer.image_url} alt={offer.title} fill
                        sizes="200px"
                        style={{ objectFit: "contain" }}
                      />
                    </div>
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
                    className={`${styles.compareItemLink} ${i === 0 ? styles.compareItemLinkBest : ""}`}
                  >
                    {openingCompareKey === compareOfferKey(offer, i) ? "Abrindo..." : "Ver oferta →"}
                  </a>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      )}
      </main>
    </div>
  );
}
