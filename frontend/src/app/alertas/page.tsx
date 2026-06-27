"use client";
import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Bell, Plus, Trash2, TrendingDown, RefreshCw } from "lucide-react";
import { API_BASE as API, apiFetch } from "@/lib/api";

interface Alert {
  id: string;
  query: string;
  target_price: number;
  is_active: boolean;
  created_at: string;
  triggered_at?: string | null;
}

interface ApiValidationError { msg?: string }

function safeLocalStorageGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (error: unknown) {
    console.warn(`localStorage read failed for ${key}:`, error);
    return null;
  }
}

function safeLocalStorageSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch (error: unknown) {
    console.warn(`localStorage write failed for ${key}:`, error);
  }
}

/** Retorna o owner_id correto: user.id se logado, senão bpt_anon_id */
function getOwnerId(): string {
  if (typeof window === "undefined") return "";
  // Usuário logado → usa o id da conta
  const userStr = safeLocalStorageGet("bpt_user");
  if (userStr) {
    try {
      const u = JSON.parse(userStr) as { id?: unknown };
      if (typeof u.id === "string") return u.id;
    } catch (error: unknown) {
      console.warn("Stored user could not be read:", error);
    }
  }
  // Anônimo → gera/recupera bpt_anon_id
  let id = safeLocalStorageGet("bpt_anon_id");
  if (!id) {
    const uniquePart = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}`;
    id = `anon_${uniquePart}`;
    safeLocalStorageSet("bpt_anon_id", id);
  }
  return id;
}

export default function AlertasPage() {
  const [query, setQuery] = useState("");
  const [price, setPrice] = useState("");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [msg, setMsg] = useState("");
  const [anonId, setAnonId] = useState("");

  // Inicializa anonId no cliente (evita hydration mismatch)
  useEffect(() => {
    setAnonId(getOwnerId());
  }, []);

  // Carrega alertas ao montar, assim que anonId estiver disponível
  const loadAlerts = useCallback(async (id: string) => {
    if (!id) return;
    setLoadingList(true);
    try {
      const r = await apiFetch(`${API}/api/v1/alerts?owner_id=${encodeURIComponent(id)}`);
      if (r.ok) {
        const data = await r.json();
        setAlerts(Array.isArray(data) ? data : []);
      }
    } catch (error: unknown) {
      console.warn("Alert list load failed:", error);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    if (anonId) loadAlerts(anonId);
  }, [anonId, loadAlerts]);

  const create = async () => {
    if (!query.trim() || !price) return;
    setLoading(true);
    setMsg("");
    try {
      const r = await apiFetch(`${API}/api/v1/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          target_price: parseFloat(price),
          owner_id: anonId || getOwnerId(),  // garante que não envia vazio
        }),
      });
      if (r.ok) {
        const data: Alert = await r.json();
        setAlerts(prev => [data, ...prev]);
        setQuery(""); setPrice("");
        setMsg("✅ Alerta criado! Você será notificado quando o preço cair.");
        setTimeout(() => setMsg(""), 4000);
      } else {
        const err = await r.json().catch(() => ({}));
        const detail = typeof err.detail === "string" ? err.detail
          : Array.isArray(err.detail) ? err.detail.map((e: ApiValidationError) => e.msg).join(", ")
          : "Erro ao criar alerta.";
        setMsg(`❌ ${detail}`);
      }
    } catch {
      setMsg("❌ Erro de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const remove = async (id: string) => {
    // Optimistic update
    setAlerts(prev => (prev || []).filter(a => a.id !== id));
    try {
      await apiFetch(`${API}/api/v1/alerts/${id}?owner_id=${encodeURIComponent(anonId)}`, { method: "DELETE" });
    } catch {
      // Se falhar, recarrega a lista
      loadAlerts(anonId);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "0 0 40px" }}>

      {/* Header de navegação */}
      <header style={{ borderBottom: "1px solid var(--bd)", padding: "0 20px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(255,255,255,0.97)", position: "sticky", top: 0, zIndex: 50 }}>
        <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 22 }}>🛍️</span>
          <span style={{ fontWeight: 800, fontSize: 16, color: "#7c6aff" }}>BestPriceToday</span>
        </a>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <a href="/" style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", textDecoration: "none", padding: "5px 12px", borderRadius: 8, border: "1px solid var(--bd)" }}>🔍 Buscar</a>
          <AuthHeaderBtn />
        </div>
      </header>

      <div style={{ maxWidth: 640, margin: "0 auto", padding: "40px 20px 0" }}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(124,106,255,.15)", flexShrink: 0 }}>
              <Bell size={22} style={{ color: "var(--acc2)" }} />
            </div>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.5px" }}>Alertas de Preço</h1>
              <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>Seja notificado quando o preço cair</p>
            </div>
          </div>
        </motion.div>

        {/* Formulário de criação */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          style={{ background: "var(--s2)", border: "1px solid var(--bd)", borderRadius: 20, padding: 24, marginBottom: 32 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--muted2)", marginBottom: 16, textTransform: "uppercase", letterSpacing: ".06em" }}>Novo alerta</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              type="text" value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Ex: iPhone 16 Pro, Nike Air Force 42..."
              onKeyDown={e => e.key === "Enter" && !loading && create()}
              style={{
                background: "var(--s3)", border: "1px solid var(--bd)", borderRadius: 12,
                padding: "13px 16px", fontSize: 15, color: "var(--txt)", outline: "none", width: "100%",
              }}
            />
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ position: "relative", flex: 1 }}>
                <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", fontSize: 13, color: "var(--muted2)", fontWeight: 600 }}>R$</span>
                <input
                  type="number" value={price} onChange={e => setPrice(e.target.value)} min="0" step="0.01"
                  placeholder="Preço alvo"
                  onKeyDown={e => e.key === "Enter" && !loading && create()}
                  style={{
                    background: "var(--s3)", border: "1px solid var(--bd)", borderRadius: 12,
                    padding: "13px 16px 13px 36px", fontSize: 15, color: "var(--txt)", outline: "none", width: "100%",
                  }}
                />
              </div>
              <button onClick={create} disabled={loading || !query.trim() || !price}
                style={{
                  display: "flex", alignItems: "center", gap: 6, padding: "0 20px", borderRadius: 12,
                  border: "none", cursor: loading || !query.trim() || !price ? "not-allowed" : "pointer",
                  background: query.trim() && price ? "linear-gradient(135deg,#7c6aff,#a78bfa)" : "var(--s4)",
                  color: query.trim() && price ? "#fff" : "rgba(26,26,46,0.45)",
                  fontSize: 14, fontWeight: 700, whiteSpace: "nowrap", transition: "all .2s",
                  opacity: loading ? 0.7 : 1,
                }}>
                {loading ? <RefreshCw size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Plus size={16} />}
                Criar
              </button>
            </div>
            {msg && (
              <p style={{ fontSize: 13, color: msg.startsWith("✅") ? "var(--grn)" : "var(--red)", lineHeight: 1.4 }}>{msg}</p>
            )}
          </div>
        </motion.div>

        {/* Lista de alertas */}
        {loadingList ? (
          <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <RefreshCw size={24} style={{ color: "var(--acc)", animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
            <p style={{ color: "var(--muted)", fontSize: 14 }}>Carregando alertas...</p>
          </div>
        ) : alerts.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            style={{ textAlign: "center", padding: "60px 20px" }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>🔔</p>
            <p style={{ color: "var(--muted)", fontSize: 15 }}>Nenhum alerta criado ainda.</p>
            <p style={{ color: "var(--muted2)", fontSize: 13, marginTop: 4 }}>Crie um alerta acima e seja notificado quando o preço cair.</p>
          </motion.div>
        ) : (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <p style={{ fontSize: 12, color: "var(--muted2)", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".06em" }}>
                {alerts.length} alerta{alerts.length !== 1 ? "s" : ""} ativo{alerts.length !== 1 ? "s" : ""}
              </p>
              <button onClick={() => loadAlerts(anonId)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted2)", display: "flex", alignItems: "center", gap: 5, fontSize: 12, padding: 4 }}>
                <RefreshCw size={12} /> Atualizar
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {alerts.map((a, i) => (
                <motion.div key={a.id}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                  style={{ background: "var(--s2)", border: "1px solid var(--bd)", borderRadius: 16, padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,229,160,.08)", flexShrink: 0 }}>
                      <TrendingDown size={18} style={{ color: "var(--grn)" }} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.query}</p>
                      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                        Alerta quando ≤ <span style={{ color: "var(--grn)", fontWeight: 700 }}>R$ {a.target_price?.toFixed(2)}</span>
                        <span style={{ marginLeft: 8, opacity: 0.5 }}>· {a.created_at ? new Date(a.created_at).toLocaleDateString("pt-BR") : ""}</span>
                      </p>
                    </div>
                  </div>
                  <button onClick={() => remove(a.id)}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted2)", padding: 8, borderRadius: 8, display: "flex", flexShrink: 0, transition: "color .15s" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "var(--red)")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--muted2)")}>
                    <Trash2 size={16} />
                  </button>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Como receber notificações */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ background: "var(--s2)", border: "1px solid var(--bd)", borderRadius: 16, padding: "20px 24px", marginTop: 32 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--muted2)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 12 }}>
            📬 Como receber notificações?
          </p>
          <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.6, marginBottom: 12 }}>
            Seus alertas são salvos e monitorados automaticamente. Quando o preço cair, você será notificado via <strong style={{ color: "var(--txt)" }}>Telegram</strong>.
          </p>
          <a href="https://t.me/BestPriceToday_bot" target="_blank" rel="noopener noreferrer"
            style={{
              display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 18px", borderRadius: 10,
              background: "rgba(41,182,246,0.1)", border: "1px solid rgba(41,182,246,0.25)",
              color: "#29b6f6", fontSize: 13, fontWeight: 600, textDecoration: "none", transition: "all .2s",
            }}>
            ✈️ Abrir BestPriceToday Bot
          </a>
        </motion.div>

        {/* Voltar */}
        <div style={{ textAlign: "center", marginTop: 40 }}>
          <a href="/" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>← Voltar para busca</a>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function AuthHeaderBtn() {
  const [user, setUser] = useState<{name: string; is_admin: boolean} | null>(null);
  useEffect(() => {
    const s = localStorage.getItem("bpt_user");
    if (s) { try { setUser(JSON.parse(s)); } catch {} }
  }, []);
  if (!user) return (
    <a href="/login" style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", textDecoration: "none", padding: "5px 12px", borderRadius: 8, border: "1px solid var(--bd)" }}>Entrar</a>
  );
  return (
    <a href={user.is_admin ? "/admin" : "/dashboard"} style={{ fontSize: 12, fontWeight: 700, color: "#a78bfa", textDecoration: "none", padding: "5px 12px", borderRadius: 8, background: "rgba(124,106,255,0.1)", border: "1px solid rgba(124,106,255,0.25)" }}>
      {user.is_admin ? "👑" : "👤"} {user.name?.split(" ")[0]}
    </a>
  );
}
