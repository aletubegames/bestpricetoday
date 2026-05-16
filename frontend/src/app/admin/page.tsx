"use client";
import React, { useState, useEffect, useCallback } from "react";
import { API_BASE as API } from "@/lib/api";

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

function getIntegrations(integrationStatus: any) {
  const ml = integrationStatus?.mercadolivre || {};
  const ali = integrationStatus?.aliexpress || {};
  const shopee = integrationStatus?.shopee || {};
  const lomadee = integrationStatus?.lomadee || {};
  return [
    { name: "AliExpress", icon: "🔴", status: ali.status === "active" ? "✅" : "⚠️", statusText: ali.status === "active" ? "Ativo" : "Sem credencial", color: ali.status === "active" ? "#4ade80" : "#facc15" },
    { name: "Shopee", icon: "🟠", status: shopee.status === "active" ? "✅" : "⚠️", statusText: shopee.status === "active" ? "Ativo" : "Sem credencial", color: shopee.status === "active" ? "#4ade80" : "#facc15" },
    { name: "Mercado Livre", icon: "🟡", status: ml.status === "active" ? "✅" : ml.status === "expiring_soon" ? "⏰" : "❌", statusText: ml.status === "active" ? `Ativo (${ml.expires_in_minutes ?? "?"}min)` : ml.status === "expiring_soon" ? "Expirando em breve" : "Bloqueado (403)", color: ml.status === "active" ? "#4ade80" : ml.status === "expiring_soon" ? "#fbbf24" : "#f43f5e" },
    { name: "Amazon", icon: "📦", status: "⚠️", statusText: "Sem credencial", color: "#facc15" },
    { name: "Lomadee", icon: "🟣", status: lomadee.status === "active" ? "✅" : "⚠️", statusText: lomadee.status === "active" ? "Ativo" : "Sem credencial", color: lomadee.status === "active" ? "#4ade80" : "#facc15" },
    { name: "TikTok Shop", icon: "🎵", status: "🔄", statusText: "Em revisão", color: "#60a5fa" },
  ];
}

// ─── Formatos de vídeo disponíveis ───────────────────────────────────────────
const VIDEO_FORMATS = [
  { id: "oferta_choque",    label: "Oferta Choque",       emoji: "💥", desc: "Preço + desconto + urgência" },
  { id: "viral_tiktok",    label: "Viral TikTok",        emoji: "🎙️", desc: "Gancho emocional, ritmo rápido" },
  { id: "top3",            label: "Top 3",               emoji: "🏆", desc: "Compara 3 opções da mesma categoria" },
  { id: "vs",              label: "VS Comparativo",      emoji: "⚔️", desc: "Marca cara vs barata" },
  { id: "alerta",          label: "Alerta de Preço",     emoji: "🔔", desc: "\'Preço caiu! Não perca!\'" },
  { id: "ultima_chance",   label: "Última Chance",       emoji: "⏳", desc: "Urgência + escassez" },
  { id: "wan21_cinematic", label: "WAN2.1 Cinemático",  emoji: "🎥", desc: "Vídeo gerado por IA (usa GPU)" },
];

const PLATAFORMAS = [
  { id: "telegram", label: "Telegram", emoji: "✈️", color: "#29b6f6" },
  { id: "youtube",  label: "YouTube",  emoji: "📹", color: "#f43f5e" },
  { id: "tiktok",   label: "TikTok",   emoji: "🎙️", color: "#ff0050" },
];

/**
 * Sugere o melhor formato de vídeo com base nas características da oferta.
 * Retorna uma lista ordenada: [{ id, reason }]
 */
function suggestFormats(p: any): { id: string; reason: string }[] {
  const title    = (p?.product_title || "").toLowerCase();
  const discount = p?.discount_percent || 0;
  const price    = p?.price || 0;
  const clicks   = p?.clicks || 0;
  const suggestions: { id: string; score: number; reason: string }[] = [];

  // Desconto alto → oferta choque é o mais eficaz
  if (discount >= 30)
    suggestions.push({ id: "oferta_choque", score: 95,
      reason: `${discount.toFixed(0)}% OFF — desconto alto converte bem em choque` });
  else if (discount >= 10)
    suggestions.push({ id: "oferta_choque", score: 75,
      reason: `${discount.toFixed(0)}% OFF — bom desconto para destaque` });

  // Produto premium (preço alto) → WAN2.1 cinemático
  if (price >= 1500)
    suggestions.push({ id: "wan21_cinematic", score: 80,
      reason: `R$${price.toFixed(0)} — produto premium, vídeo cinemático agrega percepção de valor` });

  // Muitos cliques → já é viral, usar formato viral TikTok
  if (clicks >= 20)
    suggestions.push({ id: "viral_tiktok", score: 85,
      reason: `${clicks} cliques — produto já tem tráfego, viral TikTok amplifica` });
  else if (clicks >= 5)
    suggestions.push({ id: "viral_tiktok", score: 60,
      reason: `${clicks} cliques — boa tracção para formato viral` });

  // Categorias que pedem VS ou Top 3
  const vsTerms = ["samsung", "iphone", "apple", "xiaomi", "rtx", "amd", "intel", "dell", "lenovo"];
  const top3Terms = ["fone", "notebook", "smartphone", "smartwatch", "tablet", "tv", "headset"];
  if (vsTerms.some(t => title.includes(t)))
    suggestions.push({ id: "vs", score: 72,
      reason: "Produto de marca conhecida — VS Comparativo gera debate e engajamento" });
  if (top3Terms.some(t => title.includes(t)))
    suggestions.push({ id: "top3", score: 68,
      reason: "Categoria com várias opções — Top 3 educa e converte" });

  // Preço baixo → última chance funciona bem
  if (price < 100 && price > 0)
    suggestions.push({ id: "ultima_chance", score: 70,
      reason: `R$${price.toFixed(0)} — preço acessível, urgência fecha a venda` });

  // Alerta se desconto moderado
  if (discount >= 5 && discount < 20)
    suggestions.push({ id: "alerta", score: 65,
      reason: `${discount.toFixed(0)}% OFF — alerta de queda de preço cria senso de oportunidade` });

  // Sempre adiciona fallbacks
  ["oferta_choque", "viral_tiktok", "alerta"].forEach(id => {
    if (!suggestions.find(s => s.id === id))
      suggestions.push({ id, score: 40, reason: "Formato genérico sempre funciona" });
  });

  return suggestions
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
    .map(({ id, reason }) => ({ id, reason }));
}

const PRODUCT_SOURCES = [
  { id: "top_clicks",           label: "🔥 Top Cliques (nosso)",        desc: "Produtos mais clicados pelos usuários" },
  { id: "trending",             label: "🔍 Mais Buscados",              desc: "Termos em alta no site" },
  { id: "top_month",            label: "💰 Top Vendas do Mês",          desc: "Mais convertidos com comissão confirmada" },
  { id: "high_discount",        label: "🏷️ Maiores Descontos Agora",  desc: "Desconto ≥ 10% sem fake discount" },
  { id: "top_sales_aliexpress", label: "🔴 Mais Vendidos AliExpress",  desc: "Hot products via API AliExpress" },
  { id: "top_sales_shopee",     label: "🟠 Mais Vendidos Shopee",      desc: "Hot sale Shopee" },
  { id: "top_sales_mercadolivre", label: "🟡 Mais Vendidos ML",         desc: "Top vendas Mercado Livre" },
];

function VideoPublisher({ apiBase, adminKey, topProducts }: {
  apiBase: string;
  adminKey: string;
  topProducts: any[];
}) {
  const [productSource, setProductSource]     = React.useState("top_clicks");
  const [sourceProducts, setSourceProducts]   = React.useState<any[]>([]);
  const [loadingSource, setLoadingSource]     = React.useState(false);
  const [selectedProduct, setSelectedProduct] = React.useState<any | null>(null);
  const [selectedFormat, setSelectedFormat]   = React.useState("oferta_choque");
  const [selectedPlats, setSelectedPlats]     = React.useState<string[]>(["telegram"]);
  const [jobId, setJobId]   = React.useState<string | null>(null);
  const [jobLog, setJobLog] = React.useState<string[]>([]);

  // Carrega produtos da fonte selecionada
  const loadSource = React.useCallback(async (src: string) => {
    setLoadingSource(true);
    setSelectedProduct(null);
    try {
      // top_clicks usa os topProducts já carregados para não fazer request extra
      if (src === "top_clicks") {
        setSourceProducts(topProducts.slice(0, 10));
      } else {
        const r = await fetch(
          `${apiBase}/api/v1/admin/products/suggestions?source=${src}&limit=10`,
          { headers: { "X-Admin-Key": adminKey } }
        );
        const data = await r.json();
        setSourceProducts(Array.isArray(data) ? data : []);
      }
    } catch { setSourceProducts([]); }
    setLoadingSource(false);
  }, [apiBase, adminKey, topProducts]);

  // Carrega top_clicks ao montar e quando topProducts mudar
  React.useEffect(() => { loadSource(productSource); }, [topProducts]);
  const [jobDone, setJobDone] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const pollRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Sugestões dinâmicas ao selecionar produto
  const suggestions = React.useMemo(
    () => selectedProduct ? suggestFormats(selectedProduct) : [],
    [selectedProduct]
  );

  // Aplica sugestão top automaticamente ao selecionar produto
  React.useEffect(() => {
    if (suggestions.length > 0) setSelectedFormat(suggestions[0].id);
  }, [suggestions]);

  const togglePlat = (id: string) =>
    setSelectedPlats(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const stopPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const VIDEO_LOCAL = "http://localhost:8765";
  const [videoApiOnline, setVideoApiOnline] = React.useState<boolean | null>(null);

  // Verifica se a Video API local está online
  React.useEffect(() => {
    fetch(`${VIDEO_LOCAL}/health`, { signal: AbortSignal.timeout(2000) })
      .then(r => r.ok ? r.json() : null)
      .then(d => setVideoApiOnline(!!d?.ok))
      .catch(() => setVideoApiOnline(false));
  }, []);
  const pollStatus = React.useCallback((jid: string) => {
    stopPoll();
    pollRef.current = setInterval(async () => {
      try {
        // Tenta Video API local primeiro, fallback para HF Space
        let data: any = null;
        try {
          const r = await fetch(`${VIDEO_LOCAL}/video/status/${jid}`);
          if (r.ok) data = await r.json();
        } catch {}
        if (!data) {
          const r = await fetch(`${apiBase}/api/v1/admin/video/status/${jid}`, { headers: { "X-Admin-Key": adminKey } });
          data = await r.json();
        }
        if (data?.ok) {
          setJobLog(data.log_tail || []);
          if (data.done) { setJobDone(true); stopPoll(); setLoading(false); }
        }
      } catch {}
    }, 3000);
  }, [apiBase, adminKey]);

  const dispatch = async () => {
    if (!selectedPlats.length) return;
    setLoading(true);
    setJobId(null);
    setJobLog([]);
    setJobDone(false);
    const payload = {
      query: selectedProduct?.product_title || null,
      plataformas: selectedPlats,
      formato: selectedFormat,
    };
    try {
      // Tenta Video API local (porta 8765) primeiro
      let d: any = null;
      try {
        const r = await fetch(`${VIDEO_LOCAL}/video/publish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (r.ok) d = await r.json();
      } catch { /* local offline */ }

      // Fallback: HF Space (proxy para a local via VIDEO_API_URL no .env)
      if (!d) {
        const r = await fetch(`${apiBase}/api/v1/admin/video/publish`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
          body: JSON.stringify(payload),
        });
        d = await r.json();
      }

      if (d.ok) {
        setJobId(d.job_id);
        setJobLog([`✅ Job ${d.job_id} iniciado (pid ${d.pid || '?'})`]);
        pollStatus(d.job_id);
      } else {
        setJobLog([`❌ ${d.error}`]);
        setLoading(false);
      }
    } catch (e: any) {
      setJobLog([`❌ Erro: ${e.message}`]);
      setLoading(false);
    }
  };

  React.useEffect(() => () => stopPoll(), []);

  const fmtBRL = (v: number) => v?.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const fmt = VIDEO_FORMATS.find(f => f.id === selectedFormat);

  return (
    <div style={{ marginTop: 20, borderTop: "1px solid #1e293b", paddingTop: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#fff", marginBottom: 16 }}>
        🎥 Gerar Vídeo com IA
      </div>

      {/* STEP 1 — Produto */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
          1. Produto
        </div>

        {/* Dropdown de fonte */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
          <select
            value={productSource}
            onChange={e => { setProductSource(e.target.value); loadSource(e.target.value); }}
            style={{
              background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 8,
              padding: "8px 12px", color: "#e2e8f0", fontSize: 12, cursor: "pointer",
              minWidth: 220, outline: "none",
            }}>
            {PRODUCT_SOURCES.map(s => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
          <button
            onClick={() => loadSource(productSource)}
            title="Recarregar"
            style={{ background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 8,
              padding: "7px 12px", color: "#7c6aff", cursor: "pointer", fontSize: 13 }}>
            {loadingSource ? "⏳" : "↻"}
          </button>
          <span style={{ fontSize: 10, color: "#475569" }}>
            {PRODUCT_SOURCES.find(s => s.id === productSource)?.desc}
          </span>
        </div>

        {/* Lista de produtos da fonte */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            onClick={() => setSelectedProduct(null)}
            style={{
              padding: "6px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer",
              background: !selectedProduct ? "rgba(124,106,255,0.2)" : "#0d0d1a",
              border: `1px solid ${!selectedProduct ? "#7c6aff" : "#2a2a3a"}`,
              color: !selectedProduct ? "#a78bfa" : "#64748b",
            }}>
            🌟 Auto
          </button>

          {loadingSource ? (
            <span style={{ fontSize: 11, color: "#64748b", padding: "6px 0" }}>⏳ Carregando...</span>
          ) : sourceProducts.length === 0 ? (
            <span style={{ fontSize: 11, color: "#475569", padding: "6px 0" }}>Sem dados para esta fonte</span>
          ) : sourceProducts.map((p: any, i: number) => {
            const sel = selectedProduct?.product_title === p.product_title;
            const badge = p.badge || "";
            const discount = p.discount ? ` -${Math.round(p.discount)}%` : "";
            return (
              <button key={i} onClick={() => setSelectedProduct(p)}
                title={p.product_title}
                style={{
                  padding: "6px 10px", borderRadius: 8, fontSize: 11, fontWeight: 600,
                  cursor: "pointer", maxWidth: 180, overflow: "hidden",
                  textOverflow: "ellipsis", whiteSpace: "nowrap", textAlign: "left" as const,
                  background: sel ? "rgba(124,106,255,0.2)" : "#0d0d1a",
                  border: `1px solid ${sel ? "#7c6aff" : "#1e293b"}`,
                  color: sel ? "#a78bfa" : "#94a3b8",
                }}>
                <span style={{ fontSize: 10, opacity: 0.7 }}>#{i + 1} </span>
                {p.product_title?.slice(0, 20) || "Produto"}
                {p.price ? <span style={{ color: "#facc15", marginLeft: 4 }}>{fmtBRL(p.price)}</span> : null}
                {discount ? <span style={{ color: "#4ade80", marginLeft: 3 }}>{discount}</span> : null}
              </button>
            );
          })}
        </div>

        {/* Produto selecionado */}
        {selectedProduct && (
          <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <div style={{ fontSize: 11, color: "#7c6aff", background: "rgba(124,106,255,0.08)",
              borderRadius: 6, padding: "4px 10px" }}>
              ✔ {selectedProduct.product_title?.slice(0, 60)}
            </div>
            {selectedProduct.badge && (
              <div style={{ fontSize: 10, color: "#fbbf24", background: "rgba(251,191,36,0.1)",
                borderRadius: 6, padding: "3px 8px" }}>
                {selectedProduct.badge}
              </div>
            )}
            {selectedProduct.discount >= 10 && (
              <div style={{ fontSize: 10, color: "#4ade80", background: "rgba(74,222,128,0.1)",
                borderRadius: 6, padding: "3px 8px" }}>
                -{Math.round(selectedProduct.discount)}% OFF
              </div>
            )}
          </div>
        )}
      </div>

      {/* STEP 2 — Formato */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
          2. Formato do vídeo
        </div>

        {/* Sugestões inteligentes — aparecem só quando um produto foi selecionado */}
        {suggestions.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: "#fbbf24", fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
              ✨ Sugerido para este produto
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {suggestions.map((s, i) => {
                const fmt = VIDEO_FORMATS.find(f => f.id === s.id);
                if (!fmt) return null;
                const isSel = selectedFormat === s.id;
                return (
                  <button key={s.id} onClick={() => setSelectedFormat(s.id)}
                    title={s.reason}
                    style={{
                      padding: "8px 14px", borderRadius: 8, fontSize: 12, fontWeight: 700,
                      cursor: "pointer", transition: "all .15s",
                      background: isSel ? "rgba(251,191,36,0.18)" : "rgba(251,191,36,0.06)",
                      border: `2px solid ${isSel ? "#fbbf24" : "rgba(251,191,36,0.3)"}`,
                      color: isSel ? "#fbbf24" : "#94a3b8",
                      position: "relative" as const,
                    }}>
                    {i === 0 && <span style={{ position: "absolute", top: -8, right: -6, fontSize: 9, background: "#fbbf24", color: "#000", borderRadius: 4, padding: "1px 4px", fontWeight: 800 }}>TOP</span>}
                    {fmt.emoji} {fmt.label}
                    <div style={{ fontSize: 9, color: isSel ? "#fbbf24" : "#64748b", marginTop: 2, maxWidth: 140, lineHeight: 1.3 }}>{s.reason}</div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Todos os formatos */}
        <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
          {suggestions.length > 0 ? "Ou escolha manualmente" : "Escolha o formato"}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {VIDEO_FORMATS.map(f => {
            const isSuggested = suggestions.some(s => s.id === f.id);
            const isSel = selectedFormat === f.id;
            return (
              <button key={f.id} onClick={() => setSelectedFormat(f.id)}
                title={f.desc}
                style={{
                  padding: "6px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer",
                  background: isSel ? "rgba(124,106,255,0.2)" : "#0d0d1a",
                  border: `1px solid ${isSel ? "#7c6aff" : isSuggested ? "rgba(251,191,36,0.3)" : "#2a2a3a"}`,
                  color: isSel ? "#a78bfa" : isSuggested ? "#fbbf24" : "#94a3b8",
                  opacity: isSuggested ? 1 : 0.7,
                }}>
                {f.emoji} {f.label}
              </button>
            );
          })}
        </div>
        {fmt && (
          <div style={{ marginTop: 6, fontSize: 11, color: "#64748b" }}>
            {fmt.emoji} <em>{fmt.desc}</em>
            {fmt.id === "wan21_cinematic" && (
              <span style={{ color: "#fbbf24", marginLeft: 6 }}>⚠️ Requer GPU local — pode demorar 2-5 min</span>
            )}
          </div>
        )}
      </div>

      {/* STEP 3 — Plataformas */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
          3. Publicar em
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {PLATAFORMAS.map(p => {
            const on = selectedPlats.includes(p.id);
            return (
              <button key={p.id} onClick={() => togglePlat(p.id)}
                style={{
                  padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
                  background: on ? `${p.color}20` : "#0d0d1a",
                  border: `2px solid ${on ? p.color : "#2a2a3a"}`,
                  color: on ? p.color : "#64748b",
                  transition: "all .15s",
                }}>
                {p.emoji} {p.label} {on ? "✔" : ""}
              </button>
            );
          })}
        </div>
      </div>

      {/* DISPATCH */}
      <div style={{ marginBottom: 12, padding: "8px 12px", borderRadius: 8, fontSize: 11,
        background: videoApiOnline ? "rgba(74,222,128,0.06)" : "rgba(251,191,36,0.06)",
        border: `1px solid ${videoApiOnline ? "rgba(74,222,128,0.25)" : "rgba(251,191,36,0.2)"}`,
        color: videoApiOnline ? "#4ade80" : "#fbbf24",
        display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap"
      }}>
        {videoApiOnline === null && <span>🔍 Verificando Video API local...</span>}
        {videoApiOnline === true  && <span>✅ Video API local online (porta 8765) — GPU pronta</span>}
        {videoApiOnline === false && (
          <span>
            ⚠️ Video API offline. Inicie na máquina local:
            <code style={{ background: "rgba(0,0,0,0.4)", padding: "1px 6px", borderRadius: 3, marginLeft: 6 }}>
              cd ~/wan2 &amp;&amp; python video_api.py
            </code>
          </span>
        )}
      </div>
      <button
        onClick={dispatch}
        disabled={loading || !selectedPlats.length}
        style={{
          padding: "10px 24px", borderRadius: 10, fontSize: 13, fontWeight: 700, cursor: loading ? "wait" : "pointer",
          background: loading ? "#1a1a2e" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
          border: "none", color: loading ? "#64748b" : "#fff",
          opacity: !selectedPlats.length ? 0.5 : 1,
          marginBottom: 16, transition: "all .2s",
        }}>
        {loading ? "⏳ Gerando..." : `🚀 Gerar e publicar em ${selectedPlats.map(id => PLATAFORMAS.find(p => p.id === id)?.emoji).join(" ")}`}
      </button>

      {/* LOG */}
      {(jobLog.length > 0 || jobId) && (
        <div style={{ background: "#060610", border: "1px solid #1e293b", borderRadius: 8, padding: 12, fontFamily: "monospace", fontSize: 11 }}>
          {jobId && !jobDone && (
            <div style={{ color: "#7c6aff", marginBottom: 6 }}>⏳ Job {jobId} rodando... (atualiza a cada 3s)</div>
          )}
          {jobDone && (
            <div style={{ color: "#4ade80", marginBottom: 6 }}>✅ Concluído!</div>
          )}
          {jobLog.map((line, i) => (
            <div key={i} style={{ color: line.includes("❌") || line.toLowerCase().includes("error") ? "#f87171" : line.includes("✅") || line.includes("RESULT") ? "#4ade80" : "#94a3b8", lineHeight: 1.6 }}>
              {line}
            </div>
          ))}
          {!jobDone && jobId && <div style={{ color: "#64748b", marginTop: 4 }}>...</div>}
        </div>
      )}
    </div>
  );
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
      headers: { "Content-Type": "application/json", "X-Admin-Key": k, ...(options.headers || {}) },
    }).then(r => r.json());

  const fetchAll = useCallback(async (k: string) => {
    setLoading(true);
    const provParam = activePlatform !== "all" ? `&provider=${activePlatform}` : "";
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
      setOverview(ov); setAnalytics(an.data || {}); setMarketplaces(Array.isArray(mk) ? mk : []);
      setTraffic(Array.isArray(tr) ? tr : []); setTopProducts(Array.isArray(tp) ? tp : []);
      setRecentClicks(cl.items || []); setRecentConversions(cv.items || []);
      setIntegrationStatus(intStatus || {}); setLastUpdated(new Date());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [activePlatform, activePeriod, clickPage, convPage]);

  useEffect(() => { if (key) fetchAll(key); }, [key, fetchAll]);

  const handleLogin = async () => {
    setLoginError("");
    try {
      const res = await fetch(`${API}/api/v1/admin/overview?days=1`, { headers: { "X-Admin-Key": inputKey } });
      if (!res.ok) { setLoginError("Chave inválida"); return; }
      localStorage.setItem("admin_key", inputKey);
      setKey(inputKey);
    } catch { setLoginError("Erro ao conectar com a API"); }
  };

  const handleLogout = () => { localStorage.removeItem("admin_key"); setKey(""); setOverview(null); };

  const exportCSV = () => {
    const rows = [["Hora", "Plataforma", "Produto", "Preço", "Fonte"], ...recentClicks.map((c: any) => [c.clicked_at, c.provider, c.product_title, c.price, c.source])];
    const csv = rows.map(r => r.map(v => `"${v || ""}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `bestprice_clicks_${new Date().toISOString().slice(0, 10)}.csv`; a.click();
  };

  const sortedMarketplaces = [...marketplaces].sort((a, b) => {
    const va = a[marketSort] || 0, vb = b[marketSort] || 0;
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
    { id: "mercadolivre", label: "ML", emoji: "🟡" },
    { id: "amazon", label: "Amazon", emoji: "📦" },
    { id: "lomadee", label: "Lomadee", emoji: "🟣" },
  ];
  const periods = [{ days: 1, label: "Hoje" }, { days: 7, label: "7d" }, { days: 30, label: "30d" }];

  const pillActive: React.CSSProperties = { background: "linear-gradient(135deg,#7c6aff,#a78bfa)", color: "#fff", border: "none", borderRadius: 20, padding: "6px 14px", cursor: "pointer", fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" };
  const pillInactive: React.CSSProperties = { background: "#111120", border: "1px solid #2a2a3a", color: "#888", borderRadius: 20, padding: "6px 14px", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" };

  // ─── LOGIN ────────────────────────────────────────────────
  if (!key) {
    return (
      <div style={{ minHeight: "100vh", background: "#07070f", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif", padding: "20px" }}>
        <div style={{ ...S.card, width: "100%", maxWidth: 380, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔐</div>
          <h2 style={{ color: "#fff", margin: "0 0 8px", fontSize: 22, fontWeight: 800 }}>BestPriceToday Admin</h2>
          <p style={{ color: "#64748b", fontSize: 14, marginBottom: 24 }}>Digite sua chave de administrador</p>
          <input
            type="password" placeholder="Admin key..." value={inputKey}
            onChange={e => setInputKey(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            style={{ width: "100%", boxSizing: "border-box", background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 8, padding: "12px 16px", color: "#fff", fontSize: 14, marginBottom: 12, outline: "none" }}
          />
          {loginError && <p style={{ color: "#f43f5e", fontSize: 13, marginBottom: 12 }}>{loginError}</p>}
          <button onClick={handleLogin}
            style={{ width: "100%", background: "linear-gradient(135deg,#7c6aff,#a78bfa)", border: "none", borderRadius: 8, padding: "12px", color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer" }}>
            Entrar
          </button>
        </div>
      </div>
    );
  }

  // ─── DASHBOARD ───────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "#07070f", fontFamily: "system-ui, sans-serif", color: "#e2e8f0" }}>

      {/* HEADER — responsivo: empilha no mobile */}
      <div style={{ background: "#0d0d1a", borderBottom: "1px solid #2a2a3a", padding: "12px 16px" }}>
        <div style={{ maxWidth: 1400, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22 }}>💹</span>
            <span style={{ fontWeight: 800, fontSize: 16, color: "#fff" }}>BestPriceToday</span>
            <span style={{ color: "#64748b", fontSize: 12, display: "none" }} className="admin-subtitle">Admin</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {loading && <span style={{ color: "#7c6aff", fontSize: 12 }}>⟳ Atualizando...</span>}
            {lastUpdated && !loading && <span style={{ color: "#64748b", fontSize: 11 }}>{lastUpdated.toLocaleTimeString("pt-BR")}</span>}
            <button onClick={() => fetchAll(key)} style={{ background: "#1a1a2e", border: "1px solid #2a2a3a", borderRadius: 8, padding: "5px 12px", color: "#a78bfa", cursor: "pointer", fontSize: 12 }}>↻</button>
            <button onClick={handleLogout} style={{ background: "transparent", border: "1px solid #2a2a3a", borderRadius: 8, padding: "5px 12px", color: "#64748b", cursor: "pointer", fontSize: 12 }}>Sair</button>
          </div>
        </div>
      </div>

      <div style={{ padding: "16px", maxWidth: 1400, margin: "0 auto" }}>

        {/* FILTER BAR — flex-wrap para mobile */}
        <div style={{ ...S.card, marginBottom: 16, display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <span style={S.label}>Plataforma:</span>
            {platforms.map(p => (
              <button key={p.id} onClick={() => { setActivePlatform(p.id); setClickPage(1); setConvPage(1); }}
                style={activePlatform === p.id ? pillActive : pillInactive}>
                {p.emoji} {p.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <span style={S.label}>Período:</span>
            {periods.map(p => (
              <button key={p.days} onClick={() => { setActivePeriod(p.days); setClickPage(1); setConvPage(1); }}
                style={activePeriod === p.days ? pillActive : pillInactive}>
                {p.label}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button onClick={exportCSV} style={{ ...pillInactive, color: "#4ade80" }}>⬇ CSV</button>
          </div>
        </div>

        {/* KPI CARDS — grid responsivo: 2 cols mobile, 4 tablet, 7 desktop */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
          {[
            { label: "Cliques Hoje", value: (overview?.total_clicks_today ?? 0).toLocaleString("pt-BR"), color: "#7c6aff", icon: "👆" },
            { label: `Cliques ${activePeriod}d`, value: ((activePeriod <= 7 ? (overview?.total_clicks_week ?? 0) : (overview?.total_clicks_month ?? 0))).toLocaleString("pt-BR"), color: "#60a5fa", icon: "📊" },
            { label: "Conversões", value: (overview?.total_conversions ?? 0).toLocaleString("pt-BR"), color: "#4ade80", icon: "✅" },
            { label: "Receita", value: fmtBRL(overview?.total_revenue ?? 0), color: "#facc15", icon: "💰" },
            { label: "Comissão", value: fmtBRL(overview?.total_commission ?? 0), color: "#f87171", icon: "🏷️" },
            { label: "CTR", value: `${(overview?.conversion_rate ?? 0).toFixed(2)}%`, color: "#00e5a0", icon: "🎯" },
            { label: "R$/Clique", value: `R$${(overview?.revenue_per_click ?? 0).toFixed(4)}`, color: "#fbbf24", icon: "💹" },
          ].map(card => (
            <div key={card.label} style={{ ...S.card, padding: "14px 16px" }}>
              <div style={{ fontSize: 18, marginBottom: 6 }}>{card.icon}</div>
              <div style={{ ...S.label, marginBottom: 4 }}>{card.label}</div>
              <div style={{ color: card.color, fontSize: 20, fontWeight: 800, lineHeight: 1 }}>{card.value}</div>
            </div>
          ))}
        </div>

        {/* CHARTS ROW — 1 col mobile, 2 cols desktop */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16, marginBottom: 16 }}>
          {/* Time Series */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>📈 Cliques por Dia</div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 120, overflowX: "auto" }}>
              {analyticsKeys.length === 0 && <span style={{ color: "#64748b", fontSize: 12 }}>Sem dados</span>}
              {analyticsKeys.map((day, i) => {
                const total = analyticsTotals[i];
                const h = Math.max(4, (total / maxBar) * 110);
                return (
                  <div key={day} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1, minWidth: 24 }}>
                    <div style={{ fontSize: 9, color: "#64748b", marginBottom: 1 }}>{total}</div>
                    <div style={{ width: "100%", background: "linear-gradient(180deg,#7c6aff,#a78bfa)", borderRadius: "3px 3px 0 0", height: h }} />
                    <div style={{ fontSize: 9, color: "#64748b", marginTop: 2, writingMode: "vertical-rl", transform: "rotate(180deg)", height: 28 }}>{day.slice(5)}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Revenue by Provider */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>💰 Receita por Plataforma</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(revByProvider).length === 0 && <span style={{ color: "#64748b", fontSize: 12 }}>Sem dados</span>}
              {Object.entries(revByProvider).sort(([, a], [, b]) => Number(b) - Number(a)).map(([prov, val]) => {
                const w = (Number(val) / maxRev) * 100;
                const color = PROVIDER_COLORS[prov] || "#64748b";
                return (
                  <div key={prov} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ minWidth: 80, fontSize: 11, color: "#ccc" }}>{PROVIDER_EMOJI[prov] || "•"} {prov}</div>
                    <div style={{ flex: 1, background: "#1a1a2e", borderRadius: 3, height: 14 }}>
                      <div style={{ width: `${w}%`, background: color, borderRadius: 3, height: 14 }} />
                    </div>
                    <div style={{ minWidth: 72, fontSize: 11, color, textAlign: "right" }}>{fmtBRL(Number(val))}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* MARKETING */}
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={{ ...S.label, marginBottom: 16 }}>📣 Marketing Automático</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>

            {/* Canal Telegram */}
            <div style={{ background: "#0a0a14", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>📱 Canal Telegram</div>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 12 }}>Posta ofertas de texto/imagem direto no canal</div>
              <button onClick={async () => {
                const res = await fetch(`${API}/api/v1/admin/broadcast/telegram?n=3`, { method: "POST", headers: { "X-Admin-Key": key } });
                const d = await res.json();
                alert(d.ok ? `✅ ${d.posted} ofertas postadas!\n${d.titles?.join("\n") || ""}` : `❌ ${d.error || "Erro"}`);
              }} style={{ width: "100%", padding: "9px", borderRadius: 8, background: "rgba(41,182,246,0.1)", border: "1px solid rgba(41,182,246,0.3)", color: "#29b6f6", fontWeight: 600, fontSize: 12, cursor: "pointer" }}>
                📤 Postar 3 ofertas agora
              </button>
            </div>

            {/* SEO */}
            <div style={{ background: "#0a0a14", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>🔍 SEO / Páginas</div>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Sitemap publicado para páginas públicas</div>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 12 }}>Sitemap em /sitemap.xml</div>
              <a href="/sitemap.xml" target="_blank"
                style={{ display: "block", textAlign: "center", padding: "9px", borderRadius: 8, background: "rgba(124,106,255,0.1)", border: "1px solid rgba(124,106,255,0.3)", color: "#a78bfa", fontWeight: 600, fontSize: 12, textDecoration: "none" }}>
                Ver sitemap →
              </a>
            </div>
          </div>

          {/* ── GERADOR DE VÍDEO ── */}
          <VideoPublisher apiBase={API} adminKey={key} topProducts={topProducts} />
        </div>

        {/* CONVERSION LOOP */}
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div>
              <div style={S.label}>Loop de Conversão</div>
              <div style={{ color: "#fff", fontSize: 15, fontWeight: 700 }}>Clique → Venda → Comissão</div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={async () => {
                const res = await fetch(`${API}/api/v1/admin/conversions/poll`, { method: "POST", headers: { "X-Admin-Key": key } });
                const data = await res.json();
                alert(`Poll: ${JSON.stringify(data.new_conversions)}`); fetchAll(key);
              }} style={{ padding: "7px 14px", borderRadius: 8, border: "1px solid rgba(0,229,160,0.3)", background: "rgba(0,229,160,0.08)", color: "#00e5a0", fontWeight: 600, fontSize: 12, cursor: "pointer" }}>
                ↻ Buscar conversões
              </button>
            </div>
          </div>

          {/* Funil — scroll horizontal no mobile */}
          <div style={{ overflowX: "auto" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr auto 1fr", alignItems: "center", gap: 6, minWidth: 500 }}>
              {[
                { label: "Cliques", value: overview?.total_clicks_month ?? 0, color: "#7c6aff", pct: "100%" },
                null,
                { label: "Conversões", value: overview?.total_conversions ?? 0, color: "#00e5a0", pct: overview?.total_clicks_month ? `${((overview.total_conversions / overview.total_clicks_month) * 100).toFixed(1)}%` : "0%" },
                null,
                { label: "Receita", value: `R$${(overview?.total_revenue ?? 0).toFixed(0)}`, color: "#fbbf24", pct: "—", isStr: true },
                null,
                { label: "Comissão", value: `R$${(overview?.total_commission ?? 0).toFixed(0)}`, color: "#f43f5e", pct: "—", isStr: true },
              ].map((item, i) =>
                item === null ? (
                  <div key={i} style={{ textAlign: "center", color: "#2a2a3a", fontSize: 20 }}>→</div>
                ) : (
                  <div key={i} style={{ background: `${item.color}10`, border: `1px solid ${item.color}30`, borderRadius: 10, padding: "12px 10px", textAlign: "center" }}>
                    <div style={{ color: item.color, fontSize: 18, fontWeight: 800 }}>{(item as any).isStr ? item.value : (item.value as number).toLocaleString()}</div>
                    <div style={{ color: "#64748b", fontSize: 10, fontWeight: 600, marginTop: 3 }}>{item.label}</div>
                    <div style={{ color: item.color, fontSize: 11, marginTop: 2, opacity: 0.8 }}>{item.pct}</div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* MARKETPLACE TABLE — scroll horizontal */}
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>🏪 Comparativo de Marketplaces</div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 600 }}>
              <thead>
                <tr>
                  {[["provider", "Marketplace"], ["clicks", "Cliques"], ["conversions", "Conv."], ["conversion_rate", "Taxa%"], ["revenue", "Receita"], ["commission", "Comissão"], ["avg_price", "Preço Méd."]].map(([key, lbl]) => (
                    <th key={key} style={S.th} onClick={() => handleSortMarket(key)}>
                      {lbl} {marketSort === key ? (marketSortDir === "desc" ? "↓" : "↑") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedMarketplaces.length === 0 && <tr><td colSpan={7} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Sem dados</td></tr>}
                {sortedMarketplaces.map((row, i) => (
                  <tr key={row.provider} style={i === 0 && sortedMarketplaces.length > 1 ? { borderLeft: "3px solid #4ade80" } : {}}>
                    <td style={S.td}><span style={{ color: PROVIDER_COLORS[row.provider] || "#64748b" }}>{PROVIDER_EMOJI[row.provider] || "•"} {row.provider}</span></td>
                    <td style={S.td}>{(row.clicks || 0).toLocaleString()}</td>
                    <td style={S.td}>{row.conversions || 0}</td>
                    <td style={S.td}>{(row.conversion_rate || 0).toFixed(2)}%</td>
                    <td style={{ ...S.td, color: "#facc15" }}>{fmtBRL(row.revenue || 0)}</td>
                    <td style={{ ...S.td, color: "#4ade80" }}>{fmtBRL(row.commission || 0)}</td>
                    <td style={S.td}>{fmtBRL(row.avg_price || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TRAFFIC + INTEGRATIONS — 2 cols */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 16 }}>
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>🌐 Fontes de Tráfego</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {traffic.length === 0 && <span style={{ color: "#64748b", fontSize: 12 }}>Sem dados</span>}
              {traffic.map((src: any) => {
                const color = PROVIDER_COLORS[src.source] || "#7c6aff";
                return (
                  <div key={src.source} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ minWidth: 72, fontSize: 11, color: "#ccc" }}>{src.source}</div>
                    <div style={{ flex: 1, background: "#1a1a2e", borderRadius: 3, height: 12 }}>
                      <div style={{ width: `${src.percentage || 0}%`, background: color, borderRadius: 3, height: 12 }} />
                    </div>
                    <div style={{ minWidth: 60, fontSize: 11, color: "#888", textAlign: "right" }}>{src.clicks} ({src.percentage}%)</div>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>🔌 Status das Integrações</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(() => {
                const ml = integrationStatus?.mercadolivre || {};
                const mlColor = ml.status === "active" ? "#00e5a0" : ml.status === "expiring_soon" ? "#fbbf24" : "#ff6b6b";
                const mlIcon = ml.status === "active" ? "✅" : ml.status === "expiring_soon" ? "⏰" : "❌";
                const mlLabel = ml.status === "active" ? `Ativo (${ml.expires_in_minutes}min)` : ml.status === "expiring_soon" ? "Expirando" : "Token expirado";
                return (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "7px 10px", background: "#0d0d1a", borderRadius: 8, gap: 6, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 12 }}>🟡 Mercado Livre</span>
                    <span style={{ fontSize: 12, color: mlColor }}>{mlIcon} {mlLabel}</span>
                    <button onClick={() => fetch(`${API}/api/v1/auth/ml/refresh`, { method: "POST", headers: { "X-Admin-Key": key } }).then(r => r.json()).then(d => { alert(d.ok ? "Token renovado!" : `Erro: ${d.error}`); fetchAll(key); })}
                      style={{ fontSize: 10, padding: "2px 7px", background: "#1a1a2e", border: "1px solid #333", borderRadius: 5, color: "#a78bfa", cursor: "pointer" }}>Renovar</button>
                  </div>
                );
              })()}
              {getIntegrations(integrationStatus).filter(i => i.name !== "Mercado Livre").map(int => (
                <div key={int.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "7px 10px", background: "#0d0d1a", borderRadius: 8 }}>
                  <span style={{ fontSize: 12 }}>{int.icon} {int.name}</span>
                  <span style={{ fontSize: 12, color: int.color }}>{int.status} {int.statusText}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* TOP PRODUCTS */}
        <div style={{ ...S.card, marginBottom: 16 }}>
          <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>🏆 Top 10 Produtos</div>
          {topProducts.length === 0 && <p style={{ color: "#64748b", fontSize: 12 }}>Sem dados</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {topProducts.map((p: any, i: number) => {
              const isExpanded = expandedProduct === p.product_title;
              const color = PROVIDER_COLORS[p.provider] || "#64748b";
              return (
                <div key={i}>
                  <div onClick={() => setExpandedProduct(isExpanded ? null : p.product_title)}
                    style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", background: "#0d0d1a", borderRadius: 8, cursor: "pointer", border: `1px solid ${isExpanded ? color + "44" : "transparent"}`, flexWrap: "wrap" }}>
                    <span style={{ color: "#7c6aff", fontWeight: 800, minWidth: 22, fontSize: 12 }}>#{i + 1}</span>
                    <span style={{ flex: 1, fontSize: 12, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 100 }}>{p.product_title || "–"}</span>
                    <span style={{ color, fontSize: 11, background: color + "22", padding: "2px 7px", borderRadius: 8 }}>{PROVIDER_EMOJI[p.provider] || ""} {p.provider}</span>
                    <span style={{ color: "#64748b", fontSize: 11 }}>{p.clicks} cliques</span>
                    {p.price && <span style={{ color: "#facc15", fontSize: 11 }}>{fmtBRL(p.price)}</span>}
                  </div>
                  {isExpanded && (
                    <div style={{ background: "#0d0d1a", borderRadius: "0 0 8px 8px", padding: "8px 12px", borderTop: "1px solid #1a1a2e", overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, minWidth: 320 }}>
                        <thead><tr>{["Hora", "Fonte", "Preço", "IP"].map(h => <th key={h} style={{ ...S.th, fontSize: 10 }}>{h}</th>)}</tr></thead>
                        <tbody>
                          {recentClicks.filter(c => c.product_title === p.product_title).slice(0, 5).map((c: any, ci: number) => (
                            <tr key={ci}><td style={S.td}>{fmtTime(c.clicked_at)}</td><td style={S.td}>{c.source}</td><td style={S.td}>{c.price ? fmtBRL(c.price) : "–"}</td><td style={S.td}>{c.ip_address || "–"}</td></tr>
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

        {/* RECENT CLICKS + CONVERSIONS — 1 col mobile, 2 cols desktop */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16, marginBottom: 16 }}>
          {/* Cliques */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>🖱️ Cliques Recentes</div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, minWidth: 360 }}>
                <thead><tr>{["Hora", "Plataforma", "Produto", "Preço", "Fonte"].map(h => <th key={h} style={{ ...S.th, fontSize: 10 }}>{h}</th>)}</tr></thead>
                <tbody>
                  {recentClicks.length === 0 && <tr><td colSpan={5} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Sem dados</td></tr>}
                  {recentClicks.map((c: any, i: number) => (
                    <tr key={i}>
                      <td style={S.td}>{fmtTime(c.clicked_at)}</td>
                      <td style={{ ...S.td, color: PROVIDER_COLORS[c.provider] || "#ccc" }}>{PROVIDER_EMOJI[c.provider] || ""} {c.provider}</td>
                      <td style={{ ...S.td, maxWidth: 110, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.product_title}>{c.product_title || "–"}</td>
                      <td style={S.td}>{c.price ? fmtBRL(c.price) : "–"}</td>
                      <td style={S.td}>{c.source || "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 10 }}>
              <button onClick={() => setClickPage(p => Math.max(1, p - 1))} disabled={clickPage === 1} style={{ ...pillInactive, opacity: clickPage === 1 ? 0.5 : 1, padding: "4px 12px" }}>← Ant.</button>
              <span style={{ color: "#888", padding: "4px 10px", fontSize: 12 }}>Pág. {clickPage}</span>
              <button onClick={() => setClickPage(p => p + 1)} style={{ ...pillInactive, padding: "4px 12px" }}>Próx. →</button>
            </div>
          </div>

          {/* Conversões */}
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom: 12, fontSize: 12 }}>✅ Conversões Recentes</div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, minWidth: 360 }}>
                <thead><tr>{["Hora", "Plataforma", "Produto", "Venda", "Comissão", "Status"].map(h => <th key={h} style={{ ...S.th, fontSize: 10 }}>{h}</th>)}</tr></thead>
                <tbody>
                  {recentConversions.length === 0 && <tr><td colSpan={6} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Sem dados</td></tr>}
                  {recentConversions.map((c: any, i: number) => (
                    <tr key={i}>
                      <td style={S.td}>{fmtTime(c.converted_at || c.created_at)}</td>
                      <td style={{ ...S.td, color: PROVIDER_COLORS[c.provider] || "#ccc" }}>{PROVIDER_EMOJI[c.provider] || ""} {c.provider}</td>
                      <td style={{ ...S.td, maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.product_title}>{c.product_title || "–"}</td>
                      <td style={S.td}>{c.sale_value ? fmtBRL(c.sale_value) : "–"}</td>
                      <td style={{ ...S.td, color: "#4ade80" }}>{c.commission ? fmtBRL(c.commission) : "–"}</td>
                      <td style={{ ...S.td, color: c.status === "confirmed" ? "#4ade80" : c.status === "pending" ? "#facc15" : "#f43f5e" }}>{c.status || "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 10 }}>
              <button onClick={() => setConvPage(p => Math.max(1, p - 1))} disabled={convPage === 1} style={{ ...pillInactive, opacity: convPage === 1 ? 0.5 : 1, padding: "4px 12px" }}>← Ant.</button>
              <span style={{ color: "#888", padding: "4px 10px", fontSize: 12 }}>Pág. {convPage}</span>
              <button onClick={() => setConvPage(p => p + 1)} style={{ ...pillInactive, padding: "4px 12px" }}>Próx. →</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
