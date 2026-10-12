"use client";
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/layout/Header";
import { API_BASE as API, apiFetch } from "@/lib/api";
import { logger } from "@/lib/logger";
import { isTokenExpired } from "@/lib/utils";
import styles from "./page.module.css";

const PROVIDER_COLORS: Record<string, string> = {
  aliexpress: "#f43f5e", shopee: "#f87171", mercadolivre: "#facc15",
  amazon: "#fb923c", lomadee: "#c084fc", awin: "#60a5fa", tiktok: "#ff0050",
  unknown: "#6b6b8a", web: "#7c6aff", telegram: "#29b6f6", direct: "#4ade80",
};
const PROVIDER_EMOJI: Record<string, string> = {
  aliexpress: "🔴", shopee: "🟠", mercadolivre: "🟡", amazon: "📦", lomadee: "🟣", awin: "🔵"
};

type IntegrationStatusEntry = { status?: string; expires_in_minutes?: number };
type IntegrationStatus = Record<string, IntegrationStatusEntry>;

interface MlMetrics {
  days_tracked?: number; clicks_total?: number; orders_total?: number;
  estimated_earnings_total?: number; last_collected_at?: string | null;
}
interface AdminOverview {
  total_clicks_today?: number; total_clicks_week?: number; total_clicks_month?: number;
  total_conversions?: number; total_revenue?: number; total_commission?: number;
  conversion_rate?: number; revenue_per_click?: number; revenue_by_provider?: Record<string, number>;
  ml_metrics?: MlMetrics;
}
interface MarketplaceRow {
  provider: string; clicks?: number; conversions?: number; conversion_rate?: number;
  revenue?: number; commission?: number; estimated_commission?: number; avg_price?: number;
  [key: string]: string | number | undefined;
}
interface TrafficRow { source: string; clicks?: number; percentage?: number }
interface AdminProduct { product_title?: string; provider?: string; clicks?: number; price?: number; discount?: number; discount_percent?: number; badge?: string }
interface RecentClick { clicked_at?: string; provider?: string; product_title?: string; price?: number; source?: string; ip_address?: string }
interface RecentConversion { converted_at?: string; created_at?: string; provider?: string; product_title?: string; sale_value?: number; sale_price?: number; commission?: number; commission_value?: number; status?: string }
interface TikTokAdminAccount { connected?: boolean; avatar_url?: string; display_name?: string; is_verified?: boolean }
interface AdminListResponse<T> { items?: T[] }
interface AnalyticsResponse { data?: Record<string, Record<string, number>> }

function fmtBRL(v: number) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function fmtTime(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
function getSortableNumber(row: MarketplaceRow, key: string): number {
  const value = row[key];
  return typeof value === "number" ? value : Number(value || 0);
}
function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

// ─── Video formats ──────────────────────────────────────────────────────────
const VIDEO_FORMATS = [
  { id: "oferta_choque", label: "Oferta Relâmpago", emoji: "⚡", desc: "Preço + desconto + call-to-action direto" },
  { id: "vs", label: "VS Comparativo", emoji: "⚔️", desc: "Marca conhecida vs importada" },
  { id: "ultima_chance", label: "Última Chance", emoji: "⏳", desc: "Escassez + urgência para fechar venda" },
];
const PLATAFORMAS = [
  { id: "telegram", label: "Telegram", emoji: "✈️", color: "#29b6f6" },
  { id: "youtube", label: "YouTube", emoji: "📹", color: "#f43f5e" },
  { id: "tiktok", label: "TikTok", emoji: "🎙️", color: "#ff0050" },
];
const PRODUCT_SOURCES = [
  { id: "top_clicks", label: "🔥 Top Cliques (nosso)", desc: "Produtos mais clicados pelos usuários" },
  { id: "trending", label: "🔍 Mais Buscados", desc: "Termos em alta no site" },
  { id: "top_month", label: "💰 Top Vendas do Mês", desc: "Mais convertidos com comissão confirmada" },
  { id: "high_discount", label: "🏷️ Maiores Descontos Agora", desc: "Desconto ≥ 10% sem fake discount" },
  { id: "top_sales_aliexpress", label: "🔴 Mais Vendidos AliExpress", desc: "Hot products via API AliExpress" },
  { id: "top_sales_shopee", label: "🟠 Mais Vendidos Shopee", desc: "Hot sale Shopee" },
  { id: "top_sales_mercadolivre", label: "🟡 Mais Vendidos ML", desc: "Top vendas Mercado Livre" },
];

function suggestFormats(p: AdminProduct | null | undefined): { id: string; reason: string }[] {
  const title = (p?.product_title || "").toLowerCase();
  const discount = p?.discount_percent || 0;
  const price = p?.price || 0;
  const clicks = p?.clicks || 0;
  const suggestions: { id: string; score: number; reason: string }[] = [];
  if (discount >= 30) suggestions.push({ id: "oferta_choque", score: 95, reason: `${discount.toFixed(0)}% OFF — desconto alto` });
  else if (discount >= 10) suggestions.push({ id: "oferta_choque", score: 75, reason: `${discount.toFixed(0)}% OFF — bom desconto` });
  if (price >= 1500) suggestions.push({ id: "oferta_choque", score: 80, reason: `R$${price.toFixed(0)} — produto premium` });
  if (clicks >= 20) suggestions.push({ id: "oferta_choque", score: 85, reason: `${clicks} cliques — produto viral` });
  else if (clicks >= 5) suggestions.push({ id: "oferta_choque", score: 60, reason: `${clicks} cliques — boa tracção` });
  const vsTerms = ["samsung", "iphone", "apple", "xiaomi", "rtx", "amd", "intel", "dell", "lenovo"];
  const chanceTerms = ["fone", "notebook", "smartphone", "smartwatch", "tablet", "tv", "headset"];
  if (vsTerms.some(t => title.includes(t))) suggestions.push({ id: "vs", score: 72, reason: "Marca conhecida — VS gera debate" });
  if (chanceTerms.some(t => title.includes(t))) suggestions.push({ id: "ultima_chance", score: 68, reason: "Categoria popular — urgência fecha" });
  if (price < 100 && price > 0) suggestions.push({ id: "ultima_chance", score: 70, reason: `R$${price.toFixed(0)} — preço acessível` });
  ["oferta_choque", "ultima_chance", "vs"].forEach(id => {
    if (!suggestions.find(s => s.id === id)) suggestions.push({ id, score: 40, reason: "Formato genérico" });
  });
  return suggestions.sort((a, b) => b.score - a.score).slice(0, 4).map(({ id, reason }) => ({ id, reason }));
}

// ─── VideoPublisher component ───────────────────────────────────────────────
function VideoPublisher({ apiBase, adminKey, topProducts }: {
  apiBase: string; adminKey: string; topProducts: AdminProduct[];
}) {
  const [productSource, setProductSource] = useState("top_clicks");
  const [sourceProducts, setSourceProducts] = useState<AdminProduct[]>([]);
  const [loadingSource, setLoadingSource] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<AdminProduct | null>(null);
  const [selectedFormat, setSelectedFormat] = useState("oferta_choque");
  const [selectedPlats, setSelectedPlats] = useState<string[]>(["telegram"]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobLog, setJobLog] = useState<string[]>([]);
  const [jobDone, setJobDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [videoApiOnline, setVideoApiOnline] = useState<boolean | null>(null);
  const [videoApiUrl, setVideoApiUrl] = useState<string>("");
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollStartRef = useRef<number>(0);
  const POLL_TIMEOUT = 10 * 60 * 1000;

  const loadSource = useCallback(async (src: string) => {
    setLoadingSource(true); setSelectedProduct(null);
    try {
      if (src === "top_clicks") { setSourceProducts(topProducts.slice(0, 10)); }
      else {
        const r = await apiFetch(`${apiBase}/api/v1/admin/products/suggestions?source=${src}&limit=10`, { headers: { "X-Admin-Key": adminKey } });
        const data = await r.json();
        setSourceProducts(Array.isArray(data) ? data : []);
      }
    } catch { setSourceProducts([]); }
    setLoadingSource(false);
  }, [apiBase, adminKey, topProducts]);

  useEffect(() => { loadSource(productSource); }, [topProducts, productSource, loadSource]);

  const suggestions = useMemo(() => selectedProduct ? suggestFormats(selectedProduct) : [], [selectedProduct]);
  useEffect(() => { if (suggestions.length > 0) setSelectedFormat(suggestions[0].id); }, [suggestions]);

  const togglePlat = (id: string) => setSelectedPlats(p => (p || []).includes(id) ? p.filter(x => x !== id) : [...p, id]);

  useEffect(() => {
    apiFetch(`${apiBase}/api/v1/admin/video/url`, { headers: { "X-Admin-Key": adminKey } })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d?.url) return;
        setVideoApiUrl(d.url);
        return apiFetch(`${d.url}/health`).then(r => r.ok ? r.json() : null).then(h => setVideoApiOnline(!!h?.ok)).catch(() => setVideoApiOnline(false));
      })
      .catch(() => setVideoApiOnline(false));
  }, [apiBase, adminKey]);

  const stopPoll = () => { if (pollRef.current) { clearTimeout(pollRef.current); pollRef.current = null; } };

  const pollStatus = useCallback((jid: string) => {
    pollStartRef.current = Date.now();
    const doPoll = async () => {
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT) {
        setJobLog(prev => [...prev, "⏰ Timeout: job demorou mais de 10 minutos."]);
        setJobDone(true); setLoading(false); return;
      }
      let data: { ok?: boolean; log_tail?: string[]; done?: boolean; error?: string } | null = null;
      if (videoApiUrl) {
        try { const r = await apiFetch(`${videoApiUrl}/video/status/${jid}`); if (r.ok) data = await r.json(); } catch {}
      }
      if (!data?.ok) {
        try { const r = await apiFetch(`${apiBase}/api/v1/admin/video/status/${jid}`, { headers: { "X-Admin-Key": adminKey } }); if (r.ok) data = await r.json(); } catch {}
      }
      if (data?.ok) {
        setJobLog(data.log_tail || []);
        if (data.done) { setJobDone(true); setLoading(false); stopPoll(); return; }
        if (data.error) { setJobLog(prev => [...prev, `❌ ${data.error}`]); setJobDone(true); setLoading(false); stopPoll(); return; }
      }
      pollRef.current = setTimeout(doPoll, 4000);
    };
    doPoll();
  }, [videoApiUrl, apiBase, adminKey]);

  const dispatch = async () => {
    if (!selectedPlats.length) return;
    setLoading(true); setJobDone(false); setJobLog([]); setJobId(null);
    try {
      const r = await apiFetch(`${apiBase}/api/v1/admin/video/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
        body: JSON.stringify({
          product_title: selectedProduct?.product_title || null,
          product_url: selectedProduct?.provider ? `https://bestpricetoday.alaserver.com.br` : null,
          format: selectedFormat,
          platforms: selectedPlats,
          source: productSource,
        }),
      });
      const data = await r.json();
      if (data.job_id) { setJobId(data.job_id); pollStatus(data.job_id); }
      else { setJobLog([`❌ ${data.error || "Falha ao iniciar job"}`]); setJobDone(true); setLoading(false); }
    } catch (e) {
      setJobLog([`❌ ${getErrorMessage(e)}`]); setJobDone(true); setLoading(false);
    }
  };

  const fmt = VIDEO_FORMATS.find(f => f.id === selectedFormat);

  return (
    <div className={styles.videoSection}>
      <div className={styles.cardTitle} style={{ marginBottom: 16 }}>🎥 Gerar Vídeo com IA</div>

      {/* Step 1 — Produto */}
      <div className={styles.videoStep}>
        <div className={styles.videoStepLabel}>1. Produto</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
          <select value={productSource} onChange={e => { setProductSource(e.target.value); loadSource(e.target.value); }}
            className={styles.pill} style={{ minWidth: 220 }}>
            {PRODUCT_SOURCES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <button onClick={() => loadSource(productSource)} className={styles.refreshBtn} style={{ width: 32, height: 32 }}>
            {loadingSource ? "⏳" : "↻"}
          </button>
          <span style={{ fontSize: 10, color: "var(--muted)" }}>{PRODUCT_SOURCES.find(s => s.id === productSource)?.desc}</span>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button onClick={() => setSelectedProduct(null)}
            className={`${styles.sourceBtn} ${!selectedProduct ? styles.sourceBtnActive : ""}`}>🌟 Auto</button>
          {loadingSource ? <span style={{ fontSize: 11, color: "var(--muted)", padding: "6px 0" }}>⏳ Carregando...</span> :
           sourceProducts.length === 0 ? <span style={{ fontSize: 11, color: "var(--muted)", padding: "6px 0" }}>Sem dados</span> :
           sourceProducts.map((p, i) => {
            const sel = selectedProduct?.product_title === p.product_title;
            return (
              <button key={i} onClick={() => setSelectedProduct(p)} title={p.product_title}
                className={`${styles.sourceBtn} ${sel ? styles.sourceBtnActive : ""}`}
                style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", textAlign: "left" }}>
                <span style={{ fontSize: 10, opacity: 0.7 }}>#{i + 1} </span>
                {p.product_title?.slice(0, 20) || "Produto"}
                {p.price ? <span style={{ color: "var(--ylw)", marginLeft: 4 }}>{fmtBRL(p.price)}</span> : null}
              </button>
            );
          })}
        </div>
        {selectedProduct && (
          <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <span className={styles.tag + " " + styles.tagPurple}>✔ {selectedProduct.product_title?.slice(0, 60)}</span>
            {selectedProduct.badge && <span className={styles.tag + " " + styles.tagYellow}>{selectedProduct.badge}</span>}
            {(selectedProduct.discount ?? 0) >= 10 && <span className={styles.tag + " " + styles.tagGreen}>-{Math.round(selectedProduct.discount ?? 0)}% OFF</span>}
          </div>
        )}
      </div>

      {/* Step 2 — Formato */}
      <div className={styles.videoStep}>
        <div className={styles.videoStepLabel}>2. Formato do vídeo</div>
        {suggestions.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: "var(--ylw)", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>✨ Sugerido</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {suggestions.map((s, i) => {
                const f = VIDEO_FORMATS.find(x => x.id === s.id); if (!f) return null;
                const sel = selectedFormat === s.id;
                return (
                  <button key={s.id} onClick={() => setSelectedFormat(s.id)} title={s.reason}
                    className={`${styles.formatCard} ${sel ? styles.formatCardActive : ""}`}
                    style={{ position: "relative", marginBottom: 6, maxWidth: 180 }}>
                    {i === 0 && <span style={{ position: "absolute", top: -8, right: -6, fontSize: 9, background: "var(--ylw)", color: "#000", borderRadius: 4, padding: "1px 4px", fontWeight: 800 }}>TOP</span>}
                    <div className={styles.formatCardTitle}>{f.emoji} {f.label}</div>
                    <div className={styles.formatCardDesc}>{s.reason}</div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {VIDEO_FORMATS.map(f => {
            const sel = selectedFormat === f.id;
            return (
              <button key={f.id} onClick={() => setSelectedFormat(f.id)} title={f.desc}
                className={`${styles.sourceBtn} ${sel ? styles.sourceBtnActive : ""}`}>{f.emoji} {f.label}</button>
            );
          })}
        </div>
        {fmt && <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>{fmt.emoji} <em>{fmt.desc}</em></div>}
      </div>

      {/* Step 3 — Plataformas */}
      <div className={styles.videoStep}>
        <div className={styles.videoStepLabel}>3. Publicar em</div>
        <div className={styles.platformCheck}>
          {PLATAFORMAS.map(p => {
            const on = selectedPlats.includes(p.id);
            return (
              <button key={p.id} onClick={() => togglePlat(p.id)}
                className={`${styles.platformChip} ${on ? styles.platformChipActive : ""}`}
                style={on ? { borderColor: p.color, color: p.color, background: p.color + "10" } : {}}>
                {p.emoji} {p.label} {on ? "✔" : ""}
              </button>
            );
          })}
        </div>
      </div>

      {/* Status Video API */}
      <div style={{ marginBottom: 10, padding: "8px 12px", borderRadius: 8, fontSize: 11,
        background: videoApiOnline ? "rgba(0,184,148,0.06)" : "rgba(245,158,11,0.06)",
        border: `1px solid ${videoApiOnline ? "rgba(0,184,148,0.25)" : "rgba(245,158,11,0.2)"}`,
        color: videoApiOnline ? "var(--grn)" : "var(--ylw)" }}>
        {videoApiOnline === null && "🔍 Verificando Video API..."}
        {videoApiOnline === true && "✅ Video API online — GPU pronta"}
        {videoApiOnline === false && "⚠️ Video API offline — inicie localmente"}
      </div>

      <button onClick={dispatch} disabled={loading || !selectedPlats.length} className={styles.generateBtn}>
        {loading ? "⏳ Gerando..." : `🚀 Gerar e publicar em ${selectedPlats.map(id => PLATAFORMAS.find(p => p.id === id)?.emoji).join(" ")}`}
      </button>

      {(jobLog.length > 0 || jobId) && (
        <div className={styles.jobLog}>
          {jobId && !jobDone && <div style={{ color: "var(--acc)", marginBottom: 6 }}>⏳ Job {jobId} rodando...</div>}
          {jobDone && <div style={{ color: "var(--grn)", marginBottom: 6 }}>✅ Concluído!</div>}
          {jobLog.map((line, i) => (
            <div key={i} className={styles.jobLogLine}
              style={{ color: line.includes("❌") || line.toLowerCase().includes("error") ? "var(--red)" : line.includes("✅") ? "var(--grn)" : "var(--muted)" }}>
              {line}
            </div>
          ))}
          {!jobDone && jobId && <div style={{ color: "var(--muted)" }}>...</div>}
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ════════════════════════════════════════════════════════════════════════════
export default function AdminPage() {
  const router = useRouter();
  const [key, setKey] = useState<string>("");
  const [inputKey, setInputKey] = useState("");
  const [loginError, setLoginError] = useState("");
  const [activePlatform, setActivePlatform] = useState<string>("all");
  const [activePeriod, setActivePeriod] = useState<number>(7);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [analytics, setAnalytics] = useState<Record<string, Record<string, number>>>({});
  const [marketplaces, setMarketplaces] = useState<MarketplaceRow[]>([]);
  const [traffic, setTraffic] = useState<TrafficRow[]>([]);
  const [onlineVisitors, setOnlineVisitors] = useState<{ online_now: number; visitors: any[]; stats?: any } | null>(null);
  const [topProducts, setTopProducts] = useState<AdminProduct[]>([]);
  const [recentClicks, setRecentClicks] = useState<RecentClick[]>([]);
  const [recentConversions, setRecentConversions] = useState<RecentConversion[]>([]);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus>({});
  const [integrationStatusError, setIntegrationStatusError] = useState<string | null>(null);
  const [tiktokAdminAccount, setTiktokAdminAccount] = useState<TikTokAdminAccount | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [clickPage, setClickPage] = useState(1);
  const [convPage, setConvPage] = useState(1);
  const [marketSort, setMarketSort] = useState<string>("clicks");
  const [marketSortDir, setMarketSortDir] = useState<"asc" | "desc">("desc");
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("overview");

  const ADMIN_KEY_TTL = 8 * 60 * 60 * 1000;

  useEffect(() => {
    const token = localStorage.getItem("bpt_token");
    const userStr = localStorage.getItem("bpt_user");
    if (userStr) {
      try { const user = JSON.parse(userStr); if (!user.is_admin) { router.push("/"); return; } } catch {}
    }
    if (token && isTokenExpired(token)) {
      localStorage.removeItem("bpt_token"); localStorage.removeItem("bpt_user");
      router.push("/login"); return;
    }
    const stored = localStorage.getItem("admin_key");
    const storedTs = localStorage.getItem("admin_key_ts");
    if (stored && storedTs && (Date.now() - Number(storedTs)) < ADMIN_KEY_TTL) { setKey(stored); return; }
    if (stored) { localStorage.removeItem("admin_key"); localStorage.removeItem("admin_key_ts"); }
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.is_admin) {
          apiFetch(`${API}/api/v1/auth/admin-key`, { headers: { Authorization: `Bearer ${token}` } })
            .then(r => r.json())
            .then(data => { if (data?.admin_key) { localStorage.setItem("admin_key", data.admin_key); setKey(data.admin_key); } })
            .catch((err) => logger.error("[Admin Auto-Login] Error:", err.message));
        }
      } catch (e) { logger.error("[Admin Auto-Login] Parse error:", e); }
    }
  }, []);

  const adminFetch = <T,>(url: string, k: string, options: RequestInit = {}): Promise<T> =>
    apiFetch(`${API}${url}`, { cache: "no-store", ...options, headers: { "Content-Type": "application/json", "X-Admin-Key": k, ...(options.headers || {}) } })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<T>; });

  const fetchAll = useCallback(async (k: string) => {
    setLoading(true);
    const provParam = activePlatform !== "all" ? `&provider=${activePlatform}` : "";
    try {
      const [ov, an, mk, tr, tp, cl, cv, intStatus, ttAdmin] = await Promise.all([
        adminFetch<AdminOverview>(`/api/v1/admin/overview?days=${activePeriod}${provParam}`, k),
        adminFetch<AnalyticsResponse>(`/api/v1/admin/analytics?days=${activePeriod}`, k),
        adminFetch<MarketplaceRow[]>(`/api/v1/admin/marketplaces`, k),
        adminFetch<TrafficRow[]>(`/api/v1/admin/traffic`, k),
        adminFetch<AdminProduct[]>(`/api/v1/admin/products/top?limit=10`, k),
        adminFetch<AdminListResponse<RecentClick>>(`/api/v1/admin/clicks?limit=10&page=${clickPage}`, k),
        adminFetch<AdminListResponse<RecentConversion>>(`/api/v1/admin/conversions?limit=10&page=${convPage}`, k),
        apiFetch(`${API}/api/v1/admin/integrations/status`, { cache: "no-store", headers: { "X-Admin-Key": k } })
          .then(r => r.json() as Promise<IntegrationStatus>).catch((e: unknown) => { setIntegrationStatusError(getErrorMessage(e)); return null; }),
        apiFetch(`${API}/api/v1/tiktok/admin/account`, { cache: "no-store", headers: { "X-Admin-Key": k } }).then(r => r.json() as Promise<TikTokAdminAccount>).catch(() => null),
      ]);
      setOverview(ov); setAnalytics(an.data || {}); setMarketplaces(Array.isArray(mk) ? mk : []);
      setTraffic(Array.isArray(tr) ? tr : []); setTopProducts(Array.isArray(tp) ? tp : []);
      setRecentClicks(cl.items || []); setRecentConversions(cv.items || []);
      if (intStatus) { setIntegrationStatus(intStatus); setIntegrationStatusError(null); }
      setTiktokAdminAccount(ttAdmin); setLastUpdated(new Date());

      // Fetch online visitors (separate, não bloqueia)
      adminFetch<{ online_now: number; visitors: any[]; stats?: any }>(`/api/v1/admin/online/details`, k)
        .then(d => setOnlineVisitors(d))
        .catch(() => {});
    } catch (e: unknown) {
      logger.error("Admin data fetch failed:", e);
      setIntegrationStatusError(getErrorMessage(e));
    }
    setLoading(false);
  }, [activePlatform, activePeriod, clickPage, convPage]);

  useEffect(() => { if (key) fetchAll(key); }, [key, fetchAll]);

  // Auto-refresh visitantes online a cada 15s quando tab ativa
  useEffect(() => {
    if (!key || activeTab !== "online") return;
    const fetchOnline = () => adminFetch<{ online_now: number; visitors: any[]; stats?: any }>(`/api/v1/admin/online/details`, key)
      .then(d => setOnlineVisitors(d))
      .catch(() => {});
    fetchOnline(); // fetch imediato
    const interval = setInterval(fetchOnline, 15000);
    return () => clearInterval(interval);
  }, [key, activeTab]);

  const handleLogin = async () => {
    setLoginError("");
    try {
      const res = await apiFetch(`${API}/api/v1/admin/overview?days=1`, { cache: "no-store", headers: { "X-Admin-Key": inputKey } });
      if (!res.ok) { setLoginError("Chave inválida"); return; }
      localStorage.setItem("admin_key", inputKey);
      localStorage.setItem("admin_key_ts", String(Date.now()));
      setKey(inputKey);
    } catch { setLoginError("Erro ao conectar com a API"); }
  };

  const connectTikTokAdmin = async () => {
    try {
      const res = await apiFetch(`${API}/api/v1/tiktok/auth/admin`, { headers: { "X-Admin-Key": key } });
      const data = await res.json();
      if (data.auth_url) {
        const popup = window.open(data.auth_url, "TikTok Admin Auth", "width=480,height=700,scrollbars=yes");
        const interval = setInterval(() => { if (popup?.closed) { clearInterval(interval); fetchAll(key); } }, 1000);
      }
    } catch (e: unknown) { alert(`Erro: ${getErrorMessage(e)}`); }
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_key"); localStorage.removeItem("bpt_token"); localStorage.removeItem("bpt_user");
    window.location.href = "/login";
  };

  const exportCSV = () => {
    const rows = [["Hora", "Plataforma", "Produto", "Preço", "Fonte"], ...recentClicks.map(c => [c.clicked_at, c.provider, c.product_title, c.price, c.source])];
    const csv = rows.map(r => r.map(v => `"${v || ""}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `bestprice_clicks_${new Date().toISOString().slice(0, 10)}.csv`; a.click();
  };

  const sortedMarketplaces = [...marketplaces].sort((a, b) => {
    const va = getSortableNumber(a, marketSort), vb = getSortableNumber(b, marketSort);
    return marketSortDir === "desc" ? vb - va : va - vb;
  });
  const handleSortMarket = (col: string) => {
    if (marketSort === col) setMarketSortDir(d => d === "desc" ? "asc" : "desc");
    else { setMarketSort(col); setMarketSortDir("desc"); }
  };

  const analyticsKeys = Object.keys(analytics).sort();
  const analyticsTotals = analyticsKeys.map(d => Object.values(analytics[d] || {}).reduce((a, b) => a + b, 0));
  const maxBar = Math.max(...analyticsTotals, 1);
  const revByProvider = overview?.revenue_by_provider || {};
  const maxRev = Math.max(...Object.values(revByProvider).map(Number), 1);
  const hasIntegrationStatus = Object.keys(integrationStatus).length > 0;

  const platforms = [
    { id: "all", label: "Todos", emoji: "🌐" },
    { id: "aliexpress", label: "AliExpress", emoji: "🔴" },
    { id: "shopee", label: "Shopee", emoji: "🟠" },
    { id: "mercadolivre", label: "ML", emoji: "🟡" },
    { id: "amazon", label: "Amazon", emoji: "📦" },
    { id: "lomadee", label: "Lomadee", emoji: "🟣" },
  ];
  const periods = [{ days: 1, label: "Hoje" }, { days: 7, label: "7d" }, { days: 30, label: "30d" }];

  const TABS = [
    { id: "overview", label: "Visão Geral", icon: "📊" },
    { id: "online", label: "Online", icon: "🟢" },
    { id: "traffic", label: "Tráfego", icon: "🌐" },
    { id: "products", label: "Produtos", icon: "🏆" },
    { id: "conversions", label: "Conversões", icon: "✅" },
    { id: "marketing", label: "Marketing", icon: "📣" },
    { id: "integrations", label: "Integrações", icon: "🔌" },
  ];

  // ─── LOGIN ────────────────────────────────────────────────
  if (!key) {
    return (
      <div className={styles.root}>
        <div className={styles.loginWrap}>
          <div className={styles.loginCard}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔐</div>
            <h2 className={styles.loginTitle}>BestPriceToday Admin</h2>
            <p className={styles.loginSubtitle}>Digite sua chave de administrador</p>
            <input type="password" placeholder="Admin key..." value={inputKey}
              onChange={e => setInputKey(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleLogin()}
              className={styles.loginInput} />
            {loginError && <p className={styles.loginError}>{loginError}</p>}
            <button onClick={handleLogin} className={styles.loginBtn}>Entrar</button>
          </div>
        </div>
      </div>
    );
  }

  // ─── DASHBOARD ───────────────────────────────────────────────────────────
  return (
    <div className={styles.root}>
      <Header variant="admin" onLogout={handleLogout} />
      <div className={styles.container}>

        {/* Topbar */}
        <div className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <h1 className={styles.topbarTitle}>Dashboard</h1>
            {loading && <span style={{ color: "var(--acc)", fontSize: 12 }}>⟳ Atualizando...</span>}
          </div>
          <div className={styles.topbarRight}>
            {lastUpdated && !loading && <span className={styles.lastUpdated}>Atualizado às {lastUpdated.toLocaleTimeString("pt-BR")}</span>}
            <button onClick={() => fetchAll(key)} className={styles.refreshBtn} aria-label="Atualizar">↻</button>
          </div>
        </div>

        {/* Tabs */}
        <div className={styles.tabs}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`${styles.tab} ${activeTab === t.id ? styles.tabActive : ""}`}>
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
        </div>

        {/* Filter bar */}
        <div className={styles.filterBar}>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Plataforma</span>
            {platforms.map(p => (
              <button key={p.id} onClick={() => { setActivePlatform(p.id); setClickPage(1); setConvPage(1); }}
                className={`${styles.pill} ${activePlatform === p.id ? styles.pillActive : ""}`}>
                {p.emoji} {p.label}
              </button>
            ))}
          </div>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Período</span>
            {periods.map(p => (
              <button key={p.days} onClick={() => { setActivePeriod(p.days); setClickPage(1); setConvPage(1); }}
                className={`${styles.pill} ${activePeriod === p.days ? styles.pillActive : ""}`}>
                {p.label}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto" }}>
            <button onClick={exportCSV} className={`${styles.pill} ${styles.pillSuccess}`}>⬇ CSV</button>
          </div>
        </div>

        {/* ═══════ TAB: OVERVIEW ═══════ */}
        {activeTab === "overview" && (<>
          {/* KPI Grid */}
          <div className={styles.kpiGrid}>
            {[
              { label: "Cliques Hoje", value: (overview?.total_clicks_today ?? 0).toLocaleString("pt-BR"), color: "var(--acc)", icon: "👆" },
              { label: `Cliques ${activePeriod}d`, value: ((activePeriod <= 7 ? (overview?.total_clicks_week ?? 0) : (overview?.total_clicks_month ?? 0))).toLocaleString("pt-BR"), color: "#60a5fa", icon: "📊" },
              { label: "Conversões", value: (overview?.total_conversions ?? 0).toLocaleString("pt-BR"), color: "var(--grn)", icon: "✅" },
              { label: "Receita", value: fmtBRL(overview?.total_revenue ?? 0), color: "var(--ylw)", icon: "💰" },
              { label: "Comissão", value: fmtBRL(overview?.total_commission ?? 0), color: "var(--org)", icon: "🏷️" },
              { label: "CTR", value: `${(overview?.conversion_rate ?? 0).toFixed(2)}%`, color: "var(--grn)", icon: "🎯" },
              { label: "R$/Clique", value: `R$${(overview?.revenue_per_click ?? 0).toFixed(4)}`, color: "var(--ylw)", icon: "💹" },
              { label: "ML Ganho Est.", value: fmtBRL(overview?.ml_metrics?.estimated_earnings_total ?? 0), color: "#FFE600", icon: "🛒" },
            ].map(card => (
              <div key={card.label} className={styles.kpiCard} style={{ ["--kpiColor" as string]: card.color }}>
                <div className={styles.kpiIcon}>{card.icon}</div>
                <div className={styles.kpiLabel}>{card.label}</div>
                <div className={styles.kpiValue}>{card.value}</div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className={styles.chartsRow}>
            <div className={styles.card}>
              <div className={styles.cardHeader}><div className={styles.cardTitle}>📈 Cliques por Dia</div></div>
              <div className={styles.chartContainer}>
                {analyticsKeys.length === 0 && <div className={styles.emptyState}><div className={styles.emptyStateIcon}>📊</div>Sem dados</div>}
                {analyticsKeys.map((day, i) => {
                  const total = analyticsTotals[i];
                  const h = Math.max(4, (total / maxBar) * 120);
                  return (
                    <div key={day} className={styles.barCol}>
                      <div className={styles.barValue}>{total}</div>
                      <div className={styles.bar} style={{ height: h }} />
                      <div className={styles.barLabel}>{day.slice(5)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className={styles.card}>
              <div className={styles.cardHeader}><div className={styles.cardTitle}>💰 Receita por Plataforma</div></div>
              <div className={styles.barList}>
                {Object.entries(revByProvider).length === 0 && <div className={styles.emptyState}><div className={styles.emptyStateIcon}>💰</div>Sem dados</div>}
                {Object.entries(revByProvider).sort(([, a], [, b]) => Number(b) - Number(a)).map(([prov, val]) => {
                  const w = (Number(val) / maxRev) * 100;
                  const color = PROVIDER_COLORS[prov] || "var(--muted)";
                  return (
                    <div key={prov} className={styles.barRow}>
                      <div className={styles.barRowLabel}>{PROVIDER_EMOJI[prov] || "•"} {prov}</div>
                      <div className={styles.barRowTrack}>
                        <div className={styles.barRowFill} style={{ width: `${w}%`, background: color }} />
                      </div>
                      <div className={styles.barRowValue} style={{ color }}>{fmtBRL(Number(val))}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Funnel */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>🔄 Funil de Conversão</div>
              <button onClick={async () => {
                const res = await apiFetch(`${API}/api/v1/admin/conversions/poll`, { method: "POST", headers: { "X-Admin-Key": key } });
                const data = await res.json(); alert(`Poll: ${JSON.stringify(data.new_conversions)}`); fetchAll(key);
              }} className={styles.intBtn}>↻ Buscar conversões</button>
            </div>
            <div className={styles.funnel}>
              {[
                { label: "Cliques", value: (overview?.total_clicks_month ?? 0).toLocaleString("pt-BR"), color: "var(--acc)", pct: "100%" },
                { label: "Conversões", value: (overview?.total_conversions ?? 0).toLocaleString("pt-BR"), color: "var(--grn)", pct: overview?.total_clicks_month ? `${(((overview.total_conversions ?? 0) / overview.total_clicks_month) * 100).toFixed(1)}%` : "0%" },
                { label: "Receita", value: fmtBRL(overview?.total_revenue ?? 0), color: "var(--ylw)", pct: "—" },
                { label: "Comissão", value: fmtBRL(overview?.total_commission ?? 0), color: "var(--org)", pct: "—" },
              ].map((item, i, arr) => (
                <React.Fragment key={item.label}>
                  <div className={styles.funnelStep} style={{ background: `${item.color}10`, border: `1px solid ${item.color}30` }}>
                    <div className={styles.funnelStepValue} style={{ color: item.color }}>{item.value}</div>
                    <div className={styles.funnelStepLabel}>{item.label}</div>
                    <div className={styles.funnelStepPct} style={{ color: item.color }}>{item.pct}</div>
                  </div>
                  {i < arr.length - 1 && <div className={styles.funnelArrow}>→</div>}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Marketplace table */}
          <div className={styles.card}>
            <div className={styles.cardHeader}><div className={styles.cardTitle}>🏪 Comparativo de Marketplaces</div></div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {[["provider", "Marketplace"], ["clicks", "Cliques"], ["conversions", "Conv."], ["conversion_rate", "Taxa"], ["revenue", "Receita"], ["commission", "Comissão"], ["avg_price", "Preço Méd."]].map(([k, lbl]) => (
                      <th key={k} className={styles.th} onClick={() => handleSortMarket(k)}>
                        {lbl} {marketSort === k ? (marketSortDir === "desc" ? "↓" : "↑") : ""}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sortedMarketplaces.length === 0 && <tr><td colSpan={7} className={styles.td} style={{ textAlign: "center", color: "var(--muted)" }}>Sem dados</td></tr>}
                  {sortedMarketplaces.map((row, i) => (
                    <tr key={i} className={styles.tr}>
                      <td className={styles.td}><span style={{ color: PROVIDER_COLORS[row.provider] || "var(--muted)", fontWeight: 600 }}>{PROVIDER_EMOJI[row.provider] || "•"} {row.provider}</span></td>
                      <td className={styles.td}>{(row.clicks || 0).toLocaleString()}</td>
                      <td className={styles.td}>{row.conversions || 0}</td>
                      <td className={styles.td}>{(row.conversion_rate || 0).toFixed(2)}%</td>
                      <td className={styles.td} style={{ color: "var(--ylw)", fontWeight: 600 }}>{fmtBRL(row.revenue || 0)}</td>
                      <td className={styles.td} style={{ color: "var(--grn)", fontWeight: 600 }}>
                        {fmtBRL(row.commission || 0)}
                        {row.provider === "mercadolivre" && (
                          <span style={{ color: "var(--muted)", fontWeight: 400, fontSize: "0.85em" }} title="Ganho estimado do portal ML (soma dos snapshots diários)">
                            {" "}+ {fmtBRL(row.estimated_commission || 0)} est.
                          </span>
                        )}
                      </td>
                      <td className={styles.td}>{fmtBRL(row.avg_price || 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>)}

        {/* ═══════ TAB: ONLINE ═══════ */}
        {activeTab === "online" && (
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>🟢 Visitantes Online Agora</div>
              {onlineVisitors && (
                <div style={{ fontSize: 13, color: "var(--muted)" }}>
                  {onlineVisitors.online_now} online · janela de 1 min
                </div>
              )}
            </div>

            {!onlineVisitors || onlineVisitors.online_now === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyStateIcon}>🟢</div>
                Nenhum visitante online no momento
              </div>
            ) : (
              <>
                {/* Stats resumo */}
                {onlineVisitors.stats && (
                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
                    {Object.entries(onlineVisitors.stats.devices || {}).map(([k, v]: any) => (
                      <div key={`d-${k}`} style={{ padding: "6px 12px", borderRadius: 8, background: "var(--s2)", fontSize: 12 }}>
                        💻 {k}: <strong>{v}</strong>
                      </div>
                    ))}
                    {Object.entries(onlineVisitors.stats.countries || {}).map(([k, v]: any) => (
                      <div key={`c-${k}`} style={{ padding: "6px 12px", borderRadius: 8, background: "var(--s2)", fontSize: 12 }}>
                        🌍 {k}: <strong>{v}</strong>
                      </div>
                    ))}
                    {Object.entries(onlineVisitors.stats.browsers || {}).map(([k, v]: any) => (
                      <div key={`b-${k}`} style={{ padding: "6px 12px", borderRadius: 8, background: "var(--s2)", fontSize: 12 }}>
                        🌐 {k}: <strong>{v}</strong>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tabela de visitantes */}
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid var(--bd)", textAlign: "left" }}>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>IP (anonimizado)</th>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>País</th>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>Dispositivo</th>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>Página atual</th>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>Páginas vistas</th>
                        <th style={{ padding: "8px 10px", color: "var(--muted)" }}>Tempo online</th>
                      </tr>
                    </thead>
                    <tbody>
                      {onlineVisitors.visitors?.map((v: any, i: number) => (
                        <tr key={i} style={{ borderBottom: "1px solid var(--bd)" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "monospace", fontSize: 11 }}>{v.ip_anon || "—"}</td>
                          <td style={{ padding: "8px 10px" }}>{v.country || "—"}</td>
                          <td style={{ padding: "8px 10px" }}>{v.device || "—"} {v.browser !== "unknown" ? `· ${v.browser}` : ""}</td>
                          <td style={{ padding: "8px 10px", fontFamily: "monospace", fontSize: 11, color: "var(--acc)" }}>{v.current_page || "—"}</td>
                          <td style={{ padding: "8px 10px" }}>{v.page_count || 0}</td>
                          <td style={{ padding: "8px 10px" }}>{v.online_formatted || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {/* ═══════ TAB: TRAFFIC ═══════ */}
        {activeTab === "traffic" && (
          <div className={styles.card}>
            <div className={styles.cardHeader}><div className={styles.cardTitle}>🌐 Fontes de Tráfego</div></div>
            <div className={styles.barList}>
              {traffic.length === 0 && <div className={styles.emptyState}><div className={styles.emptyStateIcon}>🌐</div>Sem dados</div>}
              {traffic.map((src) => {
                const color = PROVIDER_COLORS[src.source] || "var(--acc)";
                return (
                  <div key={src.source} className={styles.barRow}>
                    <div className={styles.barRowLabel}>{src.source}</div>
                    <div className={styles.barRowTrack}>
                      <div className={styles.barRowFill} style={{ width: `${src.percentage || 0}%`, background: color }} />
                    </div>
                    <div className={styles.barRowValue}>{src.clicks} ({src.percentage}%)</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ═══════ TAB: PRODUCTS ═══════ */}
        {activeTab === "products" && (
          <div className={styles.card}>
            <div className={styles.cardHeader}><div className={styles.cardTitle}>🏆 Top 10 Produtos</div></div>
            {topProducts.length === 0 && <div className={styles.emptyState}><div className={styles.emptyStateIcon}>🏆</div>Sem dados</div>}
            <div>
              {topProducts.map((p, i) => {
                const isExpanded = expandedProduct === p.product_title;
                const provider = p.provider || "unknown";
                const color = PROVIDER_COLORS[provider] || "var(--muted)";
                return (
                  <div key={i}>
                    <div onClick={() => setExpandedProduct(isExpanded ? null : p.product_title || null)}
                      className={styles.productRow} style={{ borderColor: isExpanded ? color : "transparent" }}>
                      <span className={styles.productRank}>#{i + 1}</span>
                      <span className={styles.productTitle}>{p.product_title || "–"}</span>
                      <span className={styles.productBadge} style={{ color, background: color + "22" }}>{PROVIDER_EMOJI[provider] || ""} {provider}</span>
                      <span className={styles.productMeta}>{p.clicks} cliques</span>
                      {p.price && <span className={styles.productMeta} style={{ color: "var(--ylw)", fontWeight: 600 }}>{fmtBRL(p.price)}</span>}
                    </div>
                    {isExpanded && (
                      <div style={{ background: "var(--s2)", borderRadius: "0 0 10px 10px", padding: "8px 12px", overflowX: "auto" }}>
                        <table className={styles.table} style={{ minWidth: 320 }}>
                          <thead><tr>{["Hora", "Fonte", "Preço", "IP"].map(h => <th key={h} className={styles.th}>{h}</th>)}</tr></thead>
                          <tbody>
                            {recentClicks.filter(c => c.product_title === p.product_title).map((c, j) => (
                              <tr key={j}>
                                <td className={styles.td}>{fmtTime(c.clicked_at)}</td>
                                <td className={styles.td}>{c.source || "–"}</td>
                                <td className={styles.td}>{c.price ? fmtBRL(c.price) : "–"}</td>
                                <td className={styles.td}>{c.ip_address || "–"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ═══════ TAB: CONVERSIONS ═══════ */}
        {activeTab === "conversions" && (
          <div className={styles.twoCol}>
            {/* Cliques recentes */}
            <div className={styles.card}>
              <div className={styles.cardHeader}><div className={styles.cardTitle}>🖱️ Cliques Recentes</div></div>
              <div className={styles.tableWrap}>
                <table className={styles.table} style={{ minWidth: 360 }}>
                  <thead><tr>{["Hora", "Plataforma", "Produto", "Preço", "Fonte"].map(h => <th key={h} className={styles.th}>{h}</th>)}</tr></thead>
                  <tbody>
                    {recentClicks.length === 0 && <tr><td colSpan={5} className={styles.td} style={{ textAlign: "center", color: "var(--muted)" }}>Sem dados</td></tr>}
                    {recentClicks.map((c, i) => (
                      <tr key={i} className={styles.tr}>
                        <td className={styles.td}>{fmtTime(c.clicked_at)}</td>
                        <td className={styles.td} style={{ color: PROVIDER_COLORS[c.provider || "unknown"] || "var(--muted)" }}>{PROVIDER_EMOJI[c.provider || "unknown"] || ""} {c.provider}</td>
                        <td className={styles.td} style={{ maxWidth: 110, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.product_title}>{c.product_title || "–"}</td>
                        <td className={styles.td}>{c.price ? fmtBRL(c.price) : "–"}</td>
                        <td className={styles.td}>{c.source || "–"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className={styles.pagination}>
                <button onClick={() => setClickPage(p => Math.max(1, p - 1))} disabled={clickPage === 1}
                  className={`${styles.pageBtn} ${clickPage === 1 ? styles.pageBtnDisabled : ""}`}>← Ant.</button>
                <span className={styles.pageInfo}>Pág. {clickPage}</span>
                <button onClick={() => setClickPage(p => p + 1)} className={styles.pageBtn}>Próx. →</button>
              </div>
            </div>

            {/* Conversões recentes */}
            <div className={styles.card}>
              <div className={styles.cardHeader}><div className={styles.cardTitle}>✅ Conversões Recentes</div></div>
              <div className={styles.tableWrap}>
                <table className={styles.table} style={{ minWidth: 360 }}>
                  <thead><tr>{["Hora", "Plataforma", "Produto", "Venda", "Comissão", "Status"].map(h => <th key={h} className={styles.th}>{h}</th>)}</tr></thead>
                  <tbody>
                    {recentConversions.length === 0 && <tr><td colSpan={6} className={styles.td} style={{ textAlign: "center", color: "var(--muted)" }}>Sem dados</td></tr>}
                    {recentConversions.map((c, i) => {
                      const saleValue = c.sale_value ?? c.sale_price;
                      const commissionValue = c.commission ?? c.commission_value;
                      return (
                        <tr key={i} className={styles.tr}>
                          <td className={styles.td}>{fmtTime(c.converted_at || c.created_at)}</td>
                          <td className={styles.td} style={{ color: PROVIDER_COLORS[c.provider || "unknown"] || "var(--muted)" }}>{PROVIDER_EMOJI[c.provider || "unknown"] || ""} {c.provider}</td>
                          <td className={styles.td} style={{ maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.product_title}>{c.product_title || "–"}</td>
                          <td className={styles.td}>{saleValue ? fmtBRL(saleValue) : "–"}</td>
                          <td className={styles.td} style={{ color: "var(--grn)", fontWeight: 600 }}>{commissionValue ? fmtBRL(commissionValue) : "–"}</td>
                          <td className={styles.td}>
                            <span className={styles.tag + " " + (c.status === "confirmed" ? styles.tagGreen : c.status === "pending" ? styles.tagYellow : styles.tagRed)}>
                              {c.status || "–"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className={styles.pagination}>
                <button onClick={() => setConvPage(p => Math.max(1, p - 1))} disabled={convPage === 1}
                  className={`${styles.pageBtn} ${convPage === 1 ? styles.pageBtnDisabled : ""}`}>← Ant.</button>
                <span className={styles.pageInfo}>Pág. {convPage}</span>
                <button onClick={() => setConvPage(p => p + 1)} className={styles.pageBtn}>Próx. →</button>
              </div>
            </div>
          </div>
        )}

        {/* ═══════ TAB: MARKETING ═══════ */}
        {activeTab === "marketing" && (
          <div className={styles.card}>
            <div className={styles.cardHeader}><div className={styles.cardTitle}>📣 Marketing Automático</div></div>
            <div className={styles.mktGrid}>
              <div className={styles.mktCard}>
                <div className={styles.mktCardTitle}>📱 Canal Telegram</div>
                <div className={styles.mktCardDesc}>Posta ofertas de texto/imagem direto no canal</div>
                <button onClick={async () => {
                  const res = await apiFetch(`${API}/api/v1/admin/broadcast/telegram?n=3`, { method: "POST", headers: { "X-Admin-Key": key } });
                  const d = await res.json();
                  alert(d.ok ? `✅ ${d.posted} ofertas postadas!\n${d.titles?.join("\n") || ""}` : `❌ ${d.error || "Erro"}`);
                }} className={`${styles.mktBtn} ${styles.mktBtnTelegram}`}>📤 Postar 3 ofertas agora</button>
              </div>
              <div className={styles.mktCard}>
                <div className={styles.mktCardTitle}>🔍 SEO / Páginas</div>
                <div className={styles.mktCardDesc}>Sitemap publicado para páginas públicas em /sitemap.xml</div>
                <a href="/sitemap.xml" target="_blank" className={`${styles.mktBtn} ${styles.mktBtnPurple}`}>Ver sitemap →</a>
              </div>
            </div>
            <VideoPublisher apiBase={API} adminKey={key} topProducts={topProducts} />
          </div>
        )}

        {/* ═══════ TAB: INTEGRATIONS ═══════ */}
        {activeTab === "integrations" && (
          <div className={styles.card}>
            <div className={styles.cardHeader}><div className={styles.cardTitle}>🔌 Status das Integrações</div></div>
            {integrationStatusError && (
              <div style={{ marginBottom: 8, padding: "8px 12px", borderRadius: 8, background: "rgba(231,76,60,0.08)", border: "1px solid rgba(231,76,60,0.22)", color: "var(--red)", fontSize: 12 }}>
                Falha ao carregar: {integrationStatusError}
              </div>
            )}
            <div>
              {!hasIntegrationStatus && !integrationStatusError && (
                <div className={styles.emptyState}>Carregando status...</div>
              )}
              {/* ML */}
              {hasIntegrationStatus && (() => {
                const ml = integrationStatus?.mercadolivre || {};
                const mlColor = ml.status === "active" ? "var(--grn)" : ml.status === "expiring_soon" ? "var(--ylw)" : "var(--red)";
                const mlIcon = ml.status === "active" ? "✅" : ml.status === "expiring_soon" ? "⏰" : "❌";
                const mlLabel = ml.status === "active" ? `Ativo (${ml.expires_in_minutes}min)` : ml.status === "expiring_soon" ? "Expirando" : "Token expirado";
                return (
                  <div className={styles.intRow}>
                    <span className={styles.intName}>🟡 Mercado Livre</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className={styles.intStatus} style={{ color: mlColor }}>{mlIcon} {mlLabel}</span>
                      <button onClick={() => apiFetch(`${API}/api/v1/auth/ml/refresh`, { method: "POST", headers: { "X-Admin-Key": key } }).then(r => r.json()).then(d => { alert(d.ok ? "Token renovado!" : `Erro: ${d.error}`); fetchAll(key); })}
                        className={styles.intBtn}>Renovar</button>
                    </div>
                  </div>
                );
              })()}
              {/* Outras integrações */}
              {hasIntegrationStatus && [
                { name: "AliExpress", icon: "🔴", key: "aliexpress" },
                { name: "Shopee", icon: "🟠", key: "shopee" },
                { name: "Amazon", icon: "📦", key: "amazon" },
                { name: "Lomadee", icon: "🟣", key: "lomadee" },
              ].map(int => {
                const st = integrationStatus?.[int.key] || {};
                const color = st.status === "active" ? "var(--grn)" : "var(--ylw)";
                const icon = st.status === "active" ? "✅" : "⚠️";
                const label = st.status === "active" ? "Ativo" : "Sem credencial";
                return (
                  <div key={int.key} className={styles.intRow}>
                    <span className={styles.intName}>{int.icon} {int.name}</span>
                    <span className={styles.intStatus} style={{ color }}>{icon} {label}</span>
                  </div>
                );
              })}
              {/* TikTok */}
              <div className={styles.intRow}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {tiktokAdminAccount?.connected && tiktokAdminAccount?.avatar_url && (
                    <img src={tiktokAdminAccount.avatar_url} alt="" style={{ width: 22, height: 22, borderRadius: "50%" }} />
                  )}
                  <span className={styles.intName}>♪ TikTok Admin</span>
                </div>
                {tiktokAdminAccount?.connected ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className={styles.intStatus} style={{ color: "var(--grn)" }}>
                      ✅ @{tiktokAdminAccount.display_name}
                      {tiktokAdminAccount.is_verified && <span style={{ color: "var(--acc)", marginLeft: 4 }}>✓</span>}
                    </span>
                    <button onClick={connectTikTokAdmin} className={styles.intBtn}>Reconectar</button>
                  </div>
                ) : (
                  <button onClick={connectTikTokAdmin}
                    style={{ fontSize: 11, padding: "5px 12px", borderRadius: 8, cursor: "pointer",
                      background: "rgba(255,0,80,0.1)", border: "1px solid rgba(255,0,80,0.3)",
                      color: "#ff3060", fontWeight: 700 }}>
                    ♪ Conectar conta TikTok
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
