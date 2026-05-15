"use client";
import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://alessandro2090-bestpricetoday-api.hf.space";

interface Overview {
  total_clicks_today: number;
  total_clicks_week: number;
  total_clicks_month: number;
  total_conversions: number;
  total_revenue: number;
  total_commission: number;
  top_provider: string;
  avg_commission_rate: number;
  clicks_by_provider: Record<string, number>;
  clicks_by_source: Record<string, number>;
  revenue_by_provider: Record<string, number>;
  recent_clicks: any[];
  recent_conversions: any[];
}

function fmtTime(iso: string) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function fmtBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function AdminPage() {
  const [key, setKey] = useState<string>("");
  const [inputKey, setInputKey] = useState("");
  const [loginError, setLoginError] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [traffic, setTraffic] = useState<any[]>([]);
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("admin_key");
    if (stored) setKey(stored);
  }, []);

  const fetchAll = useCallback(async (k: string) => {
    setLoading(true);
    try {
      const [ov, mk, tr, tp] = await Promise.all([
        fetch(`${API}/api/v1/admin/overview?admin_key=${k}`).then(r => r.json()),
        fetch(`${API}/api/v1/admin/marketplaces?admin_key=${k}`).then(r => r.json()),
        fetch(`${API}/api/v1/admin/traffic?admin_key=${k}`).then(r => r.json()),
        fetch(`${API}/api/v1/admin/products/top?admin_key=${k}`).then(r => r.json()),
      ]);
      setOverview(ov);
      setMarketplaces(Array.isArray(mk) ? mk : []);
      setTraffic(Array.isArray(tr) ? tr : []);
      setTopProducts(Array.isArray(tp) ? tp : []);
    } catch (e) {
      // ignore
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!key) return;
    fetchAll(key);
    const interval = setInterval(() => fetchAll(key), 30000);
    return () => clearInterval(interval);
  }, [key, fetchAll]);

  const handleLogin = async () => {
    setLoginError("");
    try {
      const res = await fetch(`${API}/api/v1/admin/overview?admin_key=${inputKey}`);
      if (res.ok) {
        localStorage.setItem("admin_key", inputKey);
        setKey(inputKey);
      } else {
        setLoginError("Chave inválida. Verifique o ADMIN_MANAGER_KEY.");
      }
    } catch {
      setLoginError("Erro de conexão com a API.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_key");
    setKey("");
    setOverview(null);
  };

  if (!key) {
    return (
      <div style={{ minHeight: "100vh", background: "#07070f", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ background: "var(--s2, #111120)", border: "1px solid var(--bd, #2a2a3a)", borderRadius: 16, padding: "40px 48px", width: "100%", maxWidth: 420, textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>🛡️</div>
          <h1 style={{ color: "#fff", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>BestPriceToday Admin</h1>
          <p style={{ color: "var(--muted2, #888)", fontSize: 14, marginBottom: 28 }}>Painel de gestão e analytics</p>
          <input
            type="password"
            value={inputKey}
            onChange={e => setInputKey(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            placeholder="ADMIN_MANAGER_KEY"
            style={{
              width: "100%", padding: "12px 16px", borderRadius: 10, border: "1px solid var(--bd, #2a2a3a)",
              background: "#07070f", color: "#fff", fontSize: 15, outline: "none", marginBottom: 12,
              boxSizing: "border-box",
            }}
          />
          {loginError && <p style={{ color: "#ff6b6b", fontSize: 13, marginBottom: 12 }}>{loginError}</p>}
          <button
            onClick={handleLogin}
            style={{
              width: "100%", padding: "12px", borderRadius: 10, border: "none",
              background: "linear-gradient(135deg,#7c6aff,#a78bfa)", color: "#fff",
              fontSize: 15, fontWeight: 700, cursor: "pointer",
            }}
          >Entrar</button>
        </div>
      </div>
    );
  }

  const cardStyle: React.CSSProperties = {
    background: "var(--s2, #111120)",
    border: "1px solid var(--bd, #2a2a3a)",
    borderRadius: 14,
    padding: "20px 24px",
  };

  const labelStyle: React.CSSProperties = { color: "var(--muted2, #888)", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 };
  const valueStyle: React.CSSProperties = { color: "#fff", fontSize: 28, fontWeight: 800 };

  const maxClicks = Math.max(...Object.values(overview?.clicks_by_provider || {}), 1);

  return (
    <div style={{ minHeight: "100vh", background: "#07070f", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "0 0 60px" }}>
      {/* Header */}
      <div style={{ borderBottom: "1px solid var(--bd, #2a2a3a)", padding: "16px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <span style={{ fontSize: 20, fontWeight: 800 }}>🛡️ Admin Dashboard</span>
          <span style={{ marginLeft: 12, fontSize: 12, color: "var(--muted2, #888)" }}>Auto-refresh 30s</span>
          {loading && <span style={{ marginLeft: 8, fontSize: 12, color: "var(--acc2, #a78bfa)" }}>⟳ atualizando...</span>}
        </div>
        <button onClick={handleLogout} style={{ background: "none", border: "1px solid var(--bd, #2a2a3a)", borderRadius: 8, color: "var(--muted2, #888)", padding: "6px 16px", cursor: "pointer", fontSize: 13 }}>
          Sair
        </button>
      </div>

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 24px" }}>

        {/* Overview Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
          {[
            { label: "Cliques Hoje", value: overview?.total_clicks_today ?? 0 },
            { label: "Cliques Mês", value: overview?.total_clicks_month ?? 0 },
            { label: "Conversões", value: overview?.total_conversions ?? 0 },
            { label: "Comissão Total", value: fmtBRL(overview?.total_commission ?? 0), raw: true },
          ].map(({ label, value, raw }) => (
            <div key={label} style={cardStyle}>
              <div style={labelStyle}>{label}</div>
              <div style={valueStyle}>{raw ? value : value.toLocaleString("pt-BR")}</div>
            </div>
          ))}
        </div>

        {/* Revenue + Top Provider */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
          <div style={cardStyle}>
            <div style={labelStyle}>Receita Total</div>
            <div style={{ ...valueStyle, color: "var(--acc2, #a78bfa)" }}>{fmtBRL(overview?.total_revenue ?? 0)}</div>
            <div style={{ color: "var(--muted2, #888)", fontSize: 13, marginTop: 8 }}>
              Taxa média de comissão: <strong style={{ color: "#fff" }}>{(overview?.avg_commission_rate ?? 0).toFixed(1)}%</strong>
            </div>
          </div>
          <div style={{ ...cardStyle, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={labelStyle}>Top Marketplace</div>
            <div style={{ fontSize: 36, textTransform: "capitalize", fontWeight: 800, color: "var(--acc2, #a78bfa)" }}>
              {overview?.top_provider || "—"}
            </div>
          </div>
        </div>

        {/* Clicks by Provider (bar chart) */}
        <div style={{ ...cardStyle, marginBottom: 24 }}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>Cliques por Marketplace</div>
          {Object.entries(overview?.clicks_by_provider || {}).length === 0 && (
            <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
          )}
          {Object.entries(overview?.clicks_by_provider || {}).sort((a, b) => b[1] - a[1]).map(([provider, cnt]) => (
            <div key={provider} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 14, textTransform: "capitalize" }}>{provider}</span>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{cnt}</span>
              </div>
              <div style={{ background: "var(--s3, #1a1a2e)", borderRadius: 6, height: 8, overflow: "hidden" }}>
                <div style={{ height: "100%", borderRadius: 6, background: "linear-gradient(90deg,#7c6aff,#a78bfa)", width: `${(cnt / maxClicks) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>

        {/* Traffic Sources */}
        <div style={{ ...cardStyle, marginBottom: 24 }}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>Fontes de Tráfego</div>
          {traffic.length === 0 ? (
            <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ color: "var(--muted2, #888)", textAlign: "left" }}>
                  <th style={{ padding: "8px 0" }}>Fonte</th>
                  <th style={{ padding: "8px 0" }}>Cliques</th>
                  <th style={{ padding: "8px 0" }}>%</th>
                  <th style={{ padding: "8px 0" }}>Conversões</th>
                </tr>
              </thead>
              <tbody>
                {traffic.map((t: any) => (
                  <tr key={t.source} style={{ borderTop: "1px solid var(--bd, #2a2a3a)" }}>
                    <td style={{ padding: "10px 0", textTransform: "capitalize" }}>{t.source}</td>
                    <td style={{ padding: "10px 0" }}>{t.clicks}</td>
                    <td style={{ padding: "10px 0" }}>{t.percentage}%</td>
                    <td style={{ padding: "10px 0" }}>{t.conversions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent Clicks & Conversions */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
          <div style={cardStyle}>
            <div style={{ ...labelStyle, marginBottom: 16 }}>Cliques Recentes</div>
            {(overview?.recent_clicks || []).length === 0 ? (
              <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ color: "var(--muted2, #888)" }}>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Hora</th>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Marketplace</th>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Produto</th>
                    <th style={{ padding: "6px 0", textAlign: "right" }}>Preço</th>
                  </tr>
                </thead>
                <tbody>
                  {(overview?.recent_clicks || []).map((c: any) => (
                    <tr key={c.id} style={{ borderTop: "1px solid var(--bd, #2a2a3a)" }}>
                      <td style={{ padding: "8px 0", color: "var(--muted2, #888)" }}>{fmtTime(c.clicked_at)}</td>
                      <td style={{ padding: "8px 0", textTransform: "capitalize" }}>{c.provider}</td>
                      <td style={{ padding: "8px 0", maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.product_title || "—"}</td>
                      <td style={{ padding: "8px 0", textAlign: "right" }}>{c.price ? fmtBRL(c.price) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div style={cardStyle}>
            <div style={{ ...labelStyle, marginBottom: 16 }}>Conversões Recentes</div>
            {(overview?.recent_conversions || []).length === 0 ? (
              <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ color: "var(--muted2, #888)" }}>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Hora</th>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Marketplace</th>
                    <th style={{ padding: "6px 0", textAlign: "right" }}>Venda</th>
                    <th style={{ padding: "6px 0", textAlign: "right" }}>Comissão</th>
                    <th style={{ padding: "6px 0", textAlign: "left" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(overview?.recent_conversions || []).map((c: any) => (
                    <tr key={c.id} style={{ borderTop: "1px solid var(--bd, #2a2a3a)" }}>
                      <td style={{ padding: "8px 0", color: "var(--muted2, #888)" }}>{fmtTime(c.converted_at)}</td>
                      <td style={{ padding: "8px 0", textTransform: "capitalize" }}>{c.provider}</td>
                      <td style={{ padding: "8px 0", textAlign: "right" }}>{c.sale_price ? fmtBRL(c.sale_price) : "—"}</td>
                      <td style={{ padding: "8px 0", textAlign: "right" }}>{c.commission_value ? fmtBRL(c.commission_value) : "—"}</td>
                      <td style={{ padding: "8px 0", color: c.status === "confirmed" ? "#4ade80" : c.status === "rejected" ? "#f87171" : "var(--muted2, #888)" }}>
                        {c.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Marketplace Comparison */}
        <div style={{ ...cardStyle, marginBottom: 24 }}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>Comparativo Marketplaces</div>
          {marketplaces.length === 0 ? (
            <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ color: "var(--muted2, #888)", textAlign: "left" }}>
                  <th style={{ padding: "8px 0" }}>Marketplace</th>
                  <th style={{ padding: "8px 0" }}>Cliques</th>
                  <th style={{ padding: "8px 0" }}>Conversões</th>
                  <th style={{ padding: "8px 0" }}>Taxa</th>
                  <th style={{ padding: "8px 0" }}>Receita</th>
                  <th style={{ padding: "8px 0" }}>Comissão</th>
                </tr>
              </thead>
              <tbody>
                {marketplaces.map((m: any) => (
                  <tr key={m.provider} style={{ borderTop: "1px solid var(--bd, #2a2a3a)" }}>
                    <td style={{ padding: "10px 0", textTransform: "capitalize", fontWeight: 600 }}>{m.provider}</td>
                    <td style={{ padding: "10px 0" }}>{m.clicks}</td>
                    <td style={{ padding: "10px 0" }}>{m.conversions}</td>
                    <td style={{ padding: "10px 0" }}>{m.conversion_rate}%</td>
                    <td style={{ padding: "10px 0" }}>{fmtBRL(m.revenue)}</td>
                    <td style={{ padding: "10px 0" }}>{fmtBRL(m.commission)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Top Products */}
        <div style={{ ...cardStyle, marginBottom: 24 }}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>Top Produtos por Cliques</div>
          {topProducts.length === 0 ? (
            <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>
          ) : (
            <div>
              {topProducts.map((p: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0", borderTop: i > 0 ? "1px solid var(--bd, #2a2a3a)" : "none" }}>
                  <span style={{ color: "var(--muted2, #888)", fontSize: 13, minWidth: 24 }}>#{i + 1}</span>
                  <span style={{ flex: 1, fontSize: 14 }}>{p.product_title}</span>
                  <span style={{ fontSize: 13, textTransform: "capitalize", color: "var(--muted2, #888)" }}>{p.provider}</span>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{p.clicks} cliques</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Analytics — last 7 days simple bar */}
        <div style={cardStyle}>
          <div style={{ ...labelStyle, marginBottom: 16 }}>Últimos 7 dias — Cliques por dia</div>
          <AnalyticsChart adminKey={key} />
        </div>
      </div>
    </div>
  );
}

function AnalyticsChart({ adminKey }: { adminKey: string }) {
  const [data, setData] = useState<Record<string, Record<string, number>>>({});

  useEffect(() => {
    fetch(`${API}/api/v1/admin/analytics?days=7&admin_key=${adminKey}`)
      .then(r => r.json())
      .then(d => setData(d.data || {}))
      .catch(() => {});
  }, [adminKey]);

  const days = Object.keys(data).sort();
  const totals = days.map(d => Object.values(data[d]).reduce((a, b) => a + b, 0));
  const maxVal = Math.max(...totals, 1);

  if (days.length === 0) {
    return <div style={{ color: "var(--muted2, #888)", fontSize: 14 }}>Sem dados ainda</div>;
  }

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120 }}>
      {days.map((day, i) => (
        <div key={day} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 11, color: "var(--muted2, #888)" }}>{totals[i]}</span>
          <div style={{
            width: "100%", borderRadius: 6,
            background: "linear-gradient(180deg,#7c6aff,#a78bfa)",
            height: `${(totals[i] / maxVal) * 90}px`,
            minHeight: 4,
          }} />
          <span style={{ fontSize: 10, color: "var(--muted2, #888)" }}>{day.slice(5)}</span>
        </div>
      ))}
    </div>
  );
}
