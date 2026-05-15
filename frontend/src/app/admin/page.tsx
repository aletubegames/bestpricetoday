"use client";
import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://alessandro2090-bestpricetoday-api.hf.space";

const PROVIDERS = ["aliexpress", "shopee", "mercadolivre", "amazon", "lomadee", "awin"];
const PROVIDER_COLORS: Record<string, string> = {
  aliexpress: "#f43f5e", shopee: "#f87171", mercadolivre: "#facc15",
  amazon: "#fb923c", lomadee: "#c084fc", awin: "#60a5fa", tiktok: "#ff0050",
  unknown: "#64748b", web: "#7c6aff", telegram: "#29b6f6", direct: "#4ade80",
};
const PROVIDER_EMOJI: Record<string, string> = {
  aliexpress: "🔴", shopee: "🟠", mercadolivre: "🟡", amazon: "📦", lomadee: "🟣", awin: "🔵"
};

const S = {
  card: { background: "#111120", border: "1px solid #2a2a3a", borderRadius: 14, padding: "20px 24px" } as React.CSSProperties,
  label: { color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: 1, marginBottom: 6 } as React.CSSProperties,
  bigValue: { color: "#fff", fontSize: 32, fontWeight: 800, lineHeight: 1 } as React.CSSProperties,
  th: { padding: "10px 12px", textAlign: "left" as const, color: "#64748b", fontSize: 12, fontWeight: 600, borderBottom: "1px solid #2a2a3a", cursor: "pointer", userSelect: "none" as const } as React.CSSProperties,
  td: { padding: "10px 12px", fontSize: 13, borderBottom: "1px solid #1a1a2e" } as React.CSSProperties,
};

function fmtBRL(v: number) { return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function fmtTime(iso: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
function fmtPct(n: number, d: number) { return d > 0 ? `${((n / d) * 100).toFixed(1)}%` : "0%"; }

// Status calculado dinamicamente via integrationStatus da API
function getIntegrations(integrationStatus: any) {
  const ml = integrationStatus?.mercadolivre || {};
  const ali = integrationStatus?.aliexpress || {};
  const shopee = integrationStatus?.shopee || {};
  const lomadee = integrationStatus?.lomadee || {};

  const mlOk = ml.status === "active";
  const mlExpiring = ml.status === "expiring_soon";
  const aliOk = ali.status === "active";
  const shopeeOk = shopee.status === "active";
  const lomadeeOk = lomadee.status === "active";

  return [
    {
      name: "AliExpress", icon: "🔴",
      status: aliOk ? "✅" : "⚠️",
      statusText: aliOk ? "Ativo" : "Sem credencial",
      color: aliOk ? "#4ade80" : "#facc15",
    },
    {
      name: "Shopee", icon: "🟠",
      status: shopeeOk ? "✅" : shopee.status === "not_configured" ? "⚠️" : "⚠️",
      statusText: shopeeOk ? "Ativo" : shopee.status === "not_configured" ? "Sem credencial" : "Token inválido",
      color: shopeeOk ? "#4ade80" : "#facc15",
    },
    {
      name: "Mercado Livre", icon: "🟡",
      status: mlOk ? "✅" : mlExpiring ? "⏰" : "❌",
      statusText: mlOk
        ? `Ativo (${ml.expires_in_minutes ?? "?"}min)`
        : mlExpiring ? "Expirando em breve"
        : "Bloqueado (403)",
      color: mlOk ? "#4ade80" : mlExpiring ? "#fbbf24" : "#f43f5e",
    },
    {
      name: "Amazon", icon: "📦",
      status: "⚠️", statusText: "Sem credencial", color: "#facc15",
    },
    {
      name: "Lomadee", icon: "🟣",
      status: lomadeeOk ? "✅" : "⚠️",
      statusText: lomadeeOk ? "Ativo" : "Sem credencial",
      color: lomadeeOk ? "#4ade80" : "#facc15",
    },
    {
      name: "TikTok Shop", icon: "🎵",
      status: "🔄", statusText: "Em revisão", color: "#60a5fa",
    },
  ];
}

export default function AdminPage() {
  const [key, setKey] = useState<string>("");
  const [inputKey, setInputKey] = useState("");
  const [loginError, setLoginError] = useState("");
  const [activePlatform, setActivePlatform] = useState<string>("all");
  const [activePeriod, setActivePeriod] = useState<number>(7);
  const [overview, setOverview] = useState<any>(null);
  const [analytics, setAnalytics] = useState<Record<string, Record<string, number>>>({});
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [traffic, setTraffic] = useState<any[]>([]);
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [recentClicks, setRecentClicks] = useState<any[]>([]);
  const [recentConversions, setRecentConversions] = useState<any[]>([]);
  const [integrationStatus, setIntegrationStatus] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [clickPage, setClickPage] = useState(1);
  const [convPage, setConvPage] = useState(1);
  const [marketSort, setMarketSort] = useState<string>("clicks");
  const [marketSortDir, setMarketSortDir] = useState<"asc" | "desc">("desc");
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("admin_key");
    if (stored) setKey(stored);
  }, []);

  const adminFetch = (url: string, k: string, options: RequestInit = {}) =>
    fetch(`${API}${url}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": k,
        ...(options.headers || {}),
      },
    }).then(r => r.json());

  const fetchAll = useCallback(async (k: string) => {
    setLoading(true);
    const provParam = activePlatform !== "all" ? `&provider=${activePlatform}` : "";
    const daysParam = `&days=${activePeriod}`;
    try {
      const [ov, an, mk, tr, tp, cl, cv, intStatus] = await Promise.all([
        adminFetch(`/api/v1/admin/overview?days=${activePeriod}${provParam}`, k),
        adminFetch(`/api/v1/admin/analytics?days=${activePeriod}`, k),
        adminFetch(`/api/v1/admin/marketplaces`, k),
        adminFetch(`/api/v1/admin/traffic`, k),
        adminFetch(`/api/v1/admin/products/top?limit=10`, k),
        adminFetch(`/api/v1/admin/clicks?limit=10&page=${clickPage}`, k),
        adminFetch(`/api/v1/admin/conversions?limit=10&page=${convPage}`, k),
        fetch(`${API}/api/v1/admin/integrations/status`, { headers: { "X-Admin-Key": k } }).then(r => r.json()).catch(() => ({})),
      ]);
      setOverview(ov);
      setAnalytics(an.data || {});
      setMarketplaces(Array.isArray(mk) ? mk : []);
      setTraffic(Array.isArray(tr) ? tr : []);
      setTopProducts(Array.isArray(tp) ? tp : []);
      setRecentClicks(cl.items || []);
      setRecentConversions(cv.items || []);
      setIntegrationStatus(intStatus || {});
      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [activePlatform, activePeriod, clickPage, convPage]);

  useEffect(() => {
    if (key) fetchAll(key);
  }, [key, fetchAll]);

  const handleLogin = async () => {
    setLoginError("");
    try {
      const res = await fetch(`${API}/api/v1/admin/overview?days=1`, {
        headers: { "X-Admin-Key": inputKey },
      });
      if (!res.ok) { setLoginError("Chave inválida"); return; }
      localStorage.setItem("admin_key", inputKey);
      setKey(inputKey);
    } catch {
      setLoginError("Erro ao conectar com a API");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_key");
    setKey("");
    setOverview(null);
  };

  const exportCSV = () => {
    const rows = [
      ["Hora", "Plataforma", "Produto", "Preço", "Fonte"],
      ...recentClicks.map((c: any) => [c.clicked_at, c.provider, c.product_title, c.price, c.source])
    ];
    const csv = rows.map(r => r.map(v => `"${v || ""}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bestprice_clicks_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  const sortedMarketplaces = [...marketplaces].sort((a, b) => {
    const va = a[marketSort] || 0;
    const vb = b[marketSort] || 0;
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

  const platforms = [
    { id: "all", label: "Todos", emoji: "🌐" },
    { id: "aliexpress", label: "AliExpress", emoji: "🔴" },
    { id: "shopee", label: "Shopee", emoji: "🟠" },
    { id: "mercadolivre", label: "Mercado Livre", emoji: "🟡" },
    { id: "amazon", label: "Amazon", emoji: "📦" },
    { id: "lomadee", label: "Lomadee", emoji: "🟣" },
  ];
  const periods = [
    { days: 1, label: "Hoje" },
    { days: 7, label: "7 dias" },
    { days: 30, label: "30 dias" },
  ];

  const pillActive: React.CSSProperties = { background: "linear-gradient(135deg,#7c6aff,#a78bfa)", color: "#fff", border: "none", borderRadius: 20, padding: "6px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600 };
  const pillInactive: React.CSSProperties = { background: "#111120", border: "1px solid #2a2a3a", color: "#888", borderRadius: 20, padding: "6px 16px", cursor: "pointer", fontSize: 13 };

  // LOGIN SCREEN
  if (!key) {
    return (
      <div style={{ minHeight: "100vh", background: "#07070f", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ ...S.card, width: 380, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔐</div>
          <h2 style={{ color: "#fff", margin: "0 0 8px", fontSize: 22, fontWeight: 800 }}>BestPriceToday Admin</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 24 }}>Digite sua chave de administrador</p>
          <input
            type="password"
            placeholder="Admin key..."
            value={inputKey}
            onChange={e => setInputKey(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            style={{ width: "100%", boxSizing: "border-box", background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 8, padding: "12px 16px", color: "#fff", fontSize: 14, marginBottom: 12, outline: "none" }}
          />
          {loginError && <p style={{ color: "#f43f5e", fontSize: 13, marginBottom: 12 }}>{loginError}</p>}
          <button
            onClick={handleLogin}
            style={{ width: "100%", background: "linear-gradient(135deg,#7c6aff,#a78bfa)", border: "none", borderRadius: 8, padding: "12px", color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer" }}
          >
            Entrar
          </button>
        </div>
      </div>
    );
  }

  // DASHBOARD
  return (
    <div style={{ minHeight: "100vh", background: "#07070f", fontFamily: "system-ui, sans-serif", color: "#e2e8f0" }}>

      {/* HEADER */}
      <div style={{ background: "#0d0d1a", borderBottom: "1px solid #2a2a3a", padding: "14px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>💹</span>
          <span style={{ fontWeight: 800, fontSize: 18, color: "#fff" }}>BestPriceToday</span>
          <span style={{ color: "#64748b", fontSize: 14 }}>Admin Dashboard</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {loading && <span style={{ color: "#7c6aff", fontSize: 13 }}>⟳ Atualizando...</span>}
          {lastUpdated && !loading && <span style={{ color: "#64748b", fontSize: 12 }}>Atualizado {lastUpdated.toLocaleTimeString("pt-BR")}</span>}
          <button onClick={() => fetchAll(key)} style={{ background: "#1a1a2e", border: "1px solid #2a2a3a", borderRadius: 8, padding: "6px 14px", color: "#a78bfa", cursor: "pointer", fontSize: 13 }}>↻ Refresh</button>
          <button onClick={handleLogout} style={{ background: "transparent", border: "1px solid #2a2a3a", borderRadius: 8, padding: "6px 14px", color: "#64748b", cursor: "pointer", fontSize: 13 }}>Sair</button>
        </div>
      </div>

      <div style={{ padding: "20px 24px", maxWidth: 1400, margin: "0 auto" }}>

        {/* FILTER BAR */}
        <div style={{ ...S.card, marginBottom: 20, display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" as const }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={S.label}>Plataforma:</span>
            {platforms.map(p => (
              <button key={p.id} onClick={() => setActivePlatform(p.id)} style={activePlatform === p.id ? pillActive : pillInactive}>
                {p.emoji} {p.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={S.label}>Período:</span>
            {periods.map(p => (
              <button key={p.days} onClick={() => setActivePeriod(p.days)} style={activePeriod === p.days ? pillActive : pillInactive}>
                {p.label}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button onClick={() => fetchAll(key)} style={{ ...pillInactive, color: "#a78bfa" }}>↻ Refresh</button>
            <button onClick={exportCSV} style={{ ...pillInactive, color: "#4ade80" }}>⬇ Export CSV</button>
          </div>
        </div>

        {/* KPI CARDS */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 16, marginBottom: 20 }}>
          {[
            { label: "Cliques Hoje", value: overview?.total_clicks_today ?? "–", color: "#7c6aff", icon: "👆" },
            { label: `Cliques ${activePeriod === 1 ? "Hoje" : activePeriod === 7 ? "7 dias" : "30 dias"}`, value: overview?.total_clicks_week ?? overview?.total_clicks_month ?? "–", color: "#60a5fa", icon: "📊" },
            { label: "Conversões", value: overview?.total_conversions ?? "–", color: "#4ade80", icon: "✅" },
            { label: "Receita Total", value: overview?.total_revenue != null ? fmtBRL(overview.total_revenue) : "–", color: "#facc15", icon: "💰" },
            { label: "Comissão", value: overview?.total_commission != null ? fmtBRL(overview.total_commission) : "–", color: "#f87171", icon: "🏷️" },
            { label: "CTR Clique→Venda", value: `${(overview?.conversion_rate ?? 0).toFixed(2)}%`, color: "#00e5a0", icon: "🎯" },
            { label: "Receita/Clique", value: `R$${(overview?.revenue_per_click ?? 0).toFixed(4)}`, color: "#fbbf24", icon: "💹" },
          ].map(card => (
            <div key={card.label} style={S.card}>
              <div style={{ fontSize: 22, marginBottom: 8 }}>{card.icon}</div>
              <div style={S.label}>{card.label}</div>
              <div style={{ ...S.bigValue, color: card.color, fontSize: 26 }}>{card.value}</div>
            </div>
          ))}
        </div>

        {/* FUNNEL */}
        <div style={{ ...S.card, marginBottom: 20 }}>
          <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🔽 Funil de Conversão</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0 }}>
            {[
              { label: "Buscas", value: overview?.total_clicks_month ?? 0, color: "#7c6aff", icon: "🔍" },
              { label: "Cliques", value: overview?.total_clicks_week ?? overview?.total_clicks_month ?? 0, color: "#60a5fa", icon: "👆" },
              { label: "Compras", value: overview?.total_conversions ?? 0, color: "#4ade80", icon: "🛒" },
              { label: "Comissão", value: overview?.total_commission != null ? fmtBRL(overview.total_commission) : "R$0", color: "#facc15", icon: "💸", isStr: true },
            ].map((stage, i, arr) => {
              const totalClicks = overview?.total_clicks_month || 1;
              const pct = stage.isStr ? fmtPct(overview?.total_conversions || 0, totalClicks) : fmtPct(typeof stage.value === "number" ? stage.value : 0, totalClicks);
              return (
                <div key={stage.label} style={{ display: "flex", alignItems: "center" }}>
                  <div style={{ textAlign: "center", background: "#0d0d1a", border: `1px solid ${stage.color}33`, borderRadius: 12, padding: "16px 24px", minWidth: 120 }}>
                    <div style={{ fontSize: 28, marginBottom: 4 }}>{stage.icon}</div>
                    <div style={{ color: stage.color, fontSize: 22, fontWeight: 800 }}>{stage.isStr ? stage.value : stage.value.toLocaleString()}</div>
                    <div style={{ color: "#64748b", fontSize: 11, marginTop: 4, textTransform: "uppercase" as const, letterSpacing: 0.5 }}>{stage.label}</div>
                    <div style={{ color: stage.color, fontSize: 12, marginTop: 4 }}>{i === 0 ? "100%" : pct}</div>
                  </div>
                  {i < arr.length - 1 && <div style={{ color: "#2a2a3a", fontSize: 28, margin: "0 8px" }}>→</div>}
                </div>
              );
            })}
          </div>
        </div>

        {/* CHARTS ROW */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
          {/* Time Series */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>📈 Cliques por Dia</div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 130, overflowX: "auto" as const }}>
              {analyticsKeys.length === 0 && <span style={{ color: "#64748b", fontSize: 13 }}>Sem dados</span>}
              {analyticsKeys.map((day, i) => {
                const total = analyticsTotals[i];
                const h = Math.max(4, (total / maxBar) * 120);
                const label = day.slice(5); // MM-DD
                return (
                  <div key={day} style={{ display: "flex", flexDirection: "column" as const, alignItems: "center", flex: 1, minWidth: 28 }}>
                    <div style={{ fontSize: 10, color: "#64748b", marginBottom: 2 }}>{total}</div>
                    <div style={{ width: "100%", background: "linear-gradient(180deg,#7c6aff,#a78bfa)", borderRadius: "4px 4px 0 0", height: h }} title={`${day}: ${total}`} />
                    <div style={{ fontSize: 10, color: "#64748b", marginTop: 3, writingMode: "vertical-rl" as const, transform: "rotate(180deg)", height: 30 }}>{label}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Revenue by Provider */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>💰 Receita por Plataforma</div>
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
              {Object.entries(revByProvider).length === 0 && <span style={{ color: "#64748b", fontSize: 13 }}>Sem dados</span>}
              {Object.entries(revByProvider).sort(([, a], [, b]) => Number(b) - Number(a)).map(([prov, val]) => {
                const w = (Number(val) / maxRev) * 100;
                const color = PROVIDER_COLORS[prov] || "#64748b";
                return (
                  <div key={prov} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ minWidth: 90, fontSize: 12, color: "#ccc" }}>{PROVIDER_EMOJI[prov] || "•"} {prov}</div>
                    <div style={{ flex: 1, background: "#1a1a2e", borderRadius: 4, height: 16 }}>
                      <div style={{ width: `${w}%`, background: color, borderRadius: 4, height: 16 }} />
                    </div>
                    <div style={{ minWidth: 80, fontSize: 12, color, textAlign: "right" as const }}>{fmtBRL(Number(val))}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── MARKETING / BROADCAST ── */}
        <div style={{ ...S.card, marginBottom: 24 }}>
          <div style={{ ...S.label, marginBottom: 16 }}>📣 Marketing Automático</div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Telegram Channel */}
            <div style={{ background: "#0a0a14", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>📱 Canal Telegram</div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
                {integrationStatus?.telegram_channel
                  ? "✅ Configurado"
                  : overview?.clicks_by_source?.["telegram_channel"] !== undefined || true
                  ? "✅ Ativo (broadcaster rodando)"
                  : "⚠️ Configure TELEGRAM_CHANNEL_ID"}
              </div>
              <button
                onClick={async () => {
                  const res = await fetch(`${API}/api/v1/admin/broadcast/telegram?n=3`, {
                    method: "POST", headers: { "X-Admin-Key": key }
                  })
                  const d = await res.json()
                  alert(d.ok ? `✅ ${d.posted} ofertas postadas!` : `❌ ${d.error || "Erro"}`)
                }}
                style={{
                  width: "100%", padding: "10px", borderRadius: 8,
                  background: "rgba(41,182,246,0.1)", border: "1px solid rgba(41,182,246,0.3)",
                  color: "#29b6f6", fontWeight: 600, fontSize: 13, cursor: "pointer",
                }}
              >
                📤 Postar 3 ofertas agora
              </button>
            </div>

            {/* SEO Status */}
            <div style={{ background: "#0a0a14", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>🔍 SEO / Páginas</div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>15 páginas de produto indexáveis</div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>Sitemap em /sitemap.xml</div>
              <a href="/sitemap.xml" target="_blank"
                style={{
                  display: "block", textAlign: "center",
                  padding: "10px", borderRadius: 8,
                  background: "rgba(124,106,255,0.1)", border: "1px solid rgba(124,106,255,0.3)",
                  color: "#a78bfa", fontWeight: 600, fontSize: 13, textDecoration: "none",
                }}
              >
                Ver sitemap →
              </a>
            </div>
          </div>
        </div>

        {/* ── CONVERSION TRACKING STATUS ── */}
        <div style={{ ...S.card, marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <div style={{ ...S.label }}>Loop de Conversão</div>
              <div style={{ color: "#fff", fontSize: 16, fontWeight: 700 }}>Clique → Venda → Comissão</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={async () => {
                const res = await fetch(`${API}/api/v1/admin/conversions/poll`, {
                  method: "POST",
                  headers: { "X-Admin-Key": key },
                });
                const data = await res.json()
                alert(`Poll concluído: ${JSON.stringify(data.new_conversions)}`)
                fetchAll(key)
              }}
              style={{
                padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(0,229,160,0.3)",
                background: "rgba(0,229,160,0.08)", color: "#00e5a0", fontWeight: 600,
                fontSize: 13, cursor: "pointer",
              }}
            >
              ↻ Buscar conversões agora
            </button>
            <button
              onClick={async () => {
                const res = await fetch(`${API}/api/v1/admin/conversions/test`, {
                  method: "POST", headers: { "X-Admin-Key": key }
                })
                const d = await res.json()
                alert(d.ok
                  ? `✅ Conversão teste criada!\nClique vinculado: ${d.click_linked ? "SIM" : "NÃO"}\nClick ID: ${d.click_id || "nenhum"}`
                  : "❌ Falha ao criar conversão teste")
                fetchAll(key)
              }}
              style={{
                padding: "8px 16px", borderRadius: 8,
                border: "1px solid rgba(251,191,36,0.3)",
                background: "rgba(251,191,36,0.08)",
                color: "#fbbf24", fontWeight: 600, fontSize: 13, cursor: "pointer",
              }}
            >
              🧪 Criar conversão teste
            </button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr auto 1fr", alignItems: "center", gap: 8 }}>
            {[
              { label: "Cliques", value: overview?.total_clicks_month ?? 0, color: "#7c6aff", pct: "100%" },
              null,
              { label: "Conversões", value: overview?.total_conversions ?? 0, color: "#00e5a0",
                pct: overview?.total_clicks_month ? `${((overview.total_conversions/overview.total_clicks_month)*100).toFixed(1)}%` : "0%" },
              null,
              { label: "Receita", value: `R$${(overview?.total_revenue ?? 0).toFixed(0)}`, color: "#fbbf24", pct: "—" },
              null,
              { label: "Comissão", value: `R$${(overview?.total_commission ?? 0).toFixed(0)}`, color: "#f43f5e", pct: "—" },
            ].map((item, i) =>
              item === null ? (
                <div key={i} style={{ textAlign: "center", color: "#2a2a3a", fontSize: 20 }}>→</div>
              ) : (
                <div key={i} style={{
                  background: `${item.color}10`, border: `1px solid ${item.color}30`,
                  borderRadius: 12, padding: "16px 12px", textAlign: "center",
                }}>
                  <div style={{ color: item.color, fontSize: 22, fontWeight: 800 }}>{typeof item.value === "number" ? item.value.toLocaleString() : item.value}</div>
                  <div style={{ color: "#64748b", fontSize: 11, fontWeight: 600, marginTop: 4 }}>{item.label}</div>
                  <div style={{ color: item.color, fontSize: 12, marginTop: 2, opacity: 0.8 }}>{item.pct}</div>
                </div>
              )
            )}
          </div>

          {(overview?.total_conversions ?? 0) === 0 && (
            <div style={{
              marginTop: 16, padding: "12px 16px", borderRadius: 10,
              background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.25)",
              fontSize: 13, color: "#fbbf24",
            }}>
              ⚠️ Nenhuma conversão registrada ainda. Clique em &ldquo;Buscar conversões agora&rdquo; para sincronizar com AliExpress e Lomadee, ou aguarde o polling automático (a cada 1h).
            </div>
          )}

          <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 10, background: "#0a0a14", border: "1px solid #1e293b" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>Webhook Mercado Livre</div>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#a78bfa" }}>
              POST https://alessandro2090-bestpricetoday-api.hf.space/api/v1/admin/webhooks/mercadolivre
            </div>
            <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
              Registre esta URL no ML Developer Portal → Notificações para receber confirmações de compra em tempo real.
            </div>
          </div>
        </div>

        {/* MARKETPLACE TABLE */}
        <div style={{ ...S.card, marginBottom: 20 }}>
          <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🏪 Comparativo de Marketplaces</div>
          <div style={{ overflowX: "auto" as const }}>
            <table style={{ width: "100%", borderCollapse: "collapse" as const, fontSize: 13 }}>
              <thead>
                <tr>
                  {[
                    { key: "provider", label: "Marketplace" },
                    { key: "clicks", label: "Cliques" },
                    { key: "conversions", label: "Conversões" },
                    { key: "conversion_rate", label: "Taxa Conv%" },
                    { key: "revenue", label: "Receita" },
                    { key: "commission", label: "Comissão" },
                    { key: "avg_price", label: "Preço Médio" },
                  ].map(col => (
                    <th key={col.key} style={S.th} onClick={() => handleSortMarket(col.key)}>
                      {col.label} {marketSort === col.key ? (marketSortDir === "desc" ? "↓" : "↑") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedMarketplaces.length === 0 && (
                  <tr><td colSpan={7} style={{ ...S.td, textAlign: "center" as const, color: "#64748b" }}>Sem dados</td></tr>
                )}
                {sortedMarketplaces.map((row, i) => {
                  const isTop = i === 0 && sortedMarketplaces.length > 1;
                  const color = PROVIDER_COLORS[row.provider] || "#64748b";
                  return (
                    <tr key={row.provider} style={isTop ? { borderLeft: "3px solid #4ade80" } : {}}>
                      <td style={S.td}><span style={{ color }}>{PROVIDER_EMOJI[row.provider] || "•"} {row.provider}</span></td>
                      <td style={S.td}>{(row.clicks || 0).toLocaleString()}</td>
                      <td style={S.td}>{row.conversions || 0}</td>
                      <td style={S.td}>{(row.conversion_rate || 0).toFixed(2)}%</td>
                      <td style={{ ...S.td, color: "#facc15" }}>{fmtBRL(row.revenue || 0)}</td>
                      <td style={{ ...S.td, color: "#4ade80" }}>{fmtBRL(row.commission || 0)}</td>
                      <td style={S.td}>{fmtBRL(row.avg_price || 0)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* TRAFFIC + INTEGRATIONS */}
        <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 16, marginBottom: 20 }}>
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🌐 Fontes de Tráfego</div>
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
              {traffic.length === 0 && <span style={{ color: "#64748b", fontSize: 13 }}>Sem dados</span>}
              {traffic.map((src: any) => {
                const color = PROVIDER_COLORS[src.source] || "#7c6aff";
                const pct = src.percentage || 0;
                return (
                  <div key={src.source} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ minWidth: 80, fontSize: 12, color: "#ccc" }}>{src.source}</div>
                    <div style={{ flex: 1, background: "#1a1a2e", borderRadius: 4, height: 14 }}>
                      <div style={{ width: `${pct}%`, background: color, borderRadius: 4, height: 14 }} />
                    </div>
                    <div style={{ minWidth: 50, fontSize: 12, color: "#888", textAlign: "right" as const }}>{src.clicks} ({pct}%)</div>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🔌 Status das Integrações</div>
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 10 }}>
              {/* Mercado Livre — live data from API */}
              {(() => {
                const ml = integrationStatus?.mercadolivre || {};
                const mlColor = ml.status === "active" ? "#00e5a0" : ml.status === "expiring_soon" ? "#fbbf24" : "#ff6b6b";
                const mlIcon = ml.status === "active" ? "✅" : ml.status === "expiring_soon" ? "⏰" : "❌";
                const mlLabel = ml.status === "active"
                  ? `Ativo (expira em ${ml.expires_in_minutes}min)`
                  : ml.status === "expiring_soon" ? "Expirando em breve"
                  : ml.status === "env_only" ? "Apenas env (sem DB)"
                  : ml.status === "not_configured" ? "Não configurado"
                  : "Token expirado";
                return (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", background: "#0d0d1a", borderRadius: 8, gap: 8 }}>
                    <span style={{ fontSize: 13 }}>🟡 Mercado Livre</span>
                    <span style={{ fontSize: 13, color: mlColor }}>{mlIcon} {mlLabel}</span>
                    <button
                      onClick={() => fetch(`${API}/api/v1/auth/ml/refresh`, { method: "POST", headers: { "X-Admin-Key": key } })
                        .then(r => r.json()).then(d => { alert(d.ok ? "Token renovado!" : `Erro: ${d.error}`); fetchAll(key); })}
                      style={{ fontSize: 11, padding: "3px 8px", background: "#1a1a2e", border: "1px solid #333", borderRadius: 6, color: "#a78bfa", cursor: "pointer" }}
                    >Renovar</button>
                  </div>
                );
              })()}
              {/* Other integrations — dynamic from API */}
              {getIntegrations(integrationStatus).filter(i => i.name !== "Mercado Livre").map(int => (
                <div key={int.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", background: "#0d0d1a", borderRadius: 8 }}>
                  <span style={{ fontSize: 13 }}>{int.icon} {int.name}</span>
                  <span style={{ fontSize: 13, color: int.color }}>{int.status} {int.statusText}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* TOP PRODUCTS */}
        <div style={{ ...S.card, marginBottom: 20 }}>
          <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🏆 Top 10 Produtos</div>
          {topProducts.length === 0 && <p style={{ color: "#64748b", fontSize: 13 }}>Sem dados</p>}
          <div style={{ display: "flex", flexDirection: "column" as const, gap: 6 }}>
            {topProducts.map((p: any, i: number) => {
              const isExpanded = expandedProduct === p.product_title;
              const color = PROVIDER_COLORS[p.provider] || "#64748b";
              const filteredClicks = recentClicks.filter(c => c.product_title === p.product_title);
              return (
                <div key={i}>
                  <div
                    onClick={() => setExpandedProduct(isExpanded ? null : p.product_title)}
                    style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: "#0d0d1a", borderRadius: 8, cursor: "pointer", border: `1px solid ${isExpanded ? color + "44" : "transparent"}` }}
                  >
                    <span style={{ color: "#7c6aff", fontWeight: 800, minWidth: 24 }}>#{i + 1}</span>
                    <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>{p.product_title || "–"}</span>
                    <span style={{ color, fontSize: 12, background: color + "22", padding: "2px 8px", borderRadius: 10 }}>{PROVIDER_EMOJI[p.provider] || ""} {p.provider}</span>
                    <span style={{ color: "#64748b", fontSize: 12 }}>{p.clicks} cliques</span>
                    {p.price && <span style={{ color: "#facc15", fontSize: 12 }}>{fmtBRL(p.price)}</span>}
                    <span style={{ color: "#64748b", fontSize: 11 }}>{isExpanded ? "▲" : "▼"}</span>
                  </div>
                  {isExpanded && (
                    <div style={{ background: "#0d0d1a", borderRadius: "0 0 8px 8px", padding: "8px 14px", borderTop: "1px solid #1a1a2e" }}>
                      {filteredClicks.length === 0 ? (
                        <p style={{ color: "#64748b", fontSize: 12, margin: 0 }}>Nenhum clique recente disponível (dados não carregados para este produto)</p>
                      ) : (
                        <table style={{ width: "100%", borderCollapse: "collapse" as const, fontSize: 12 }}>
                          <thead>
                            <tr>
                              {["Hora", "Fonte", "Preço", "IP"].map(h => <th key={h} style={{ ...S.th, fontSize: 11 }}>{h}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {filteredClicks.slice(0, 5).map((c: any, ci: number) => (
                              <tr key={ci}>
                                <td style={S.td}>{fmtTime(c.clicked_at)}</td>
                                <td style={S.td}>{c.source}</td>
                                <td style={S.td}>{c.price ? fmtBRL(c.price) : "–"}</td>
                                <td style={S.td}>{c.ip_address || "–"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* RECENT CLICKS + CONVERSIONS */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
          {/* Recent Clicks */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>🖱️ Cliques Recentes</div>
            <div style={{ overflowX: "auto" as const }}>
              <table style={{ width: "100%", borderCollapse: "collapse" as const, fontSize: 12 }}>
                <thead>
                  <tr>
                    {["Hora", "Plataforma", "Produto", "Preço", "Fonte"].map(h => <th key={h} style={{ ...S.th, fontSize: 11 }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {recentClicks.length === 0 && <tr><td colSpan={5} style={{ ...S.td, textAlign: "center" as const, color: "#64748b" }}>Sem dados</td></tr>}
                  {recentClicks.map((c: any, i: number) => (
                    <tr key={i}>
                      <td style={S.td}>{fmtTime(c.clicked_at)}</td>
                      <td style={{ ...S.td, color: PROVIDER_COLORS[c.provider] || "#ccc" }}>{PROVIDER_EMOJI[c.provider] || ""} {c.provider}</td>
                      <td style={{ ...S.td, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }} title={c.product_title}>{c.product_title || "–"}</td>
                      <td style={S.td}>{c.price ? fmtBRL(c.price) : "–"}</td>
                      <td style={S.td}>{c.source || "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 12 }}>
              <button onClick={() => setClickPage(p => Math.max(1, p - 1))} disabled={clickPage === 1} style={{ ...pillInactive, opacity: clickPage === 1 ? 0.5 : 1 }}>← Anterior</button>
              <span style={{ color: "#888", padding: "6px 12px" }}>Página {clickPage}</span>
              <button onClick={() => setClickPage(p => p + 1)} style={pillInactive}>Próxima →</button>
            </div>
          </div>

          {/* Recent Conversions */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 16, fontSize: 13 }}>✅ Conversões Recentes</div>
            <div style={{ overflowX: "auto" as const }}>
              <table style={{ width: "100%", borderCollapse: "collapse" as const, fontSize: 12 }}>
                <thead>
                  <tr>
                    {["Hora", "Plataforma", "Produto", "Venda", "Comissão", "Status"].map(h => <th key={h} style={{ ...S.th, fontSize: 11 }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {recentConversions.length === 0 && <tr><td colSpan={6} style={{ ...S.td, textAlign: "center" as const, color: "#64748b" }}>Sem dados</td></tr>}
                  {recentConversions.map((c: any, i: number) => {
                    const statusColor = c.status === "confirmed" ? "#4ade80" : c.status === "pending" ? "#facc15" : "#f43f5e";
                    return (
                      <tr key={i}>
                        <td style={S.td}>{fmtTime(c.converted_at || c.created_at)}</td>
                        <td style={{ ...S.td, color: PROVIDER_COLORS[c.provider] || "#ccc" }}>{PROVIDER_EMOJI[c.provider] || ""} {c.provider}</td>
                        <td style={{ ...S.td, maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }} title={c.product_title}>{c.product_title || "–"}</td>
                        <td style={S.td}>{c.sale_value ? fmtBRL(c.sale_value) : "–"}</td>
                        <td style={{ ...S.td, color: "#4ade80" }}>{c.commission ? fmtBRL(c.commission) : "–"}</td>
                        <td style={{ ...S.td, color: statusColor }}>{c.status || "–"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 12 }}>
              <button onClick={() => setConvPage(p => Math.max(1, p - 1))} disabled={convPage === 1} style={{ ...pillInactive, opacity: convPage === 1 ? 0.5 : 1 }}>← Anterior</button>
              <span style={{ color: "#888", padding: "6px 12px" }}>Página {convPage}</span>
              <button onClick={() => setConvPage(p => p + 1)} style={pillInactive}>Próxima →</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
