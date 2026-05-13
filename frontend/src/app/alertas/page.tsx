"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Bell, Plus, Trash2, TrendingDown } from "lucide-react";

interface Alert {
  id: string;
  query: string;
  target_price: number;
  created_at: string;
}

export default function AlertasPage() {
  const [query, setQuery] = useState("");
  const [price, setPrice] = useState("");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const create = async () => {
    if (!query || !price) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, target_price: parseFloat(price) }),
      });
      if (r.ok) {
        const data = await r.json();
        setAlerts(prev => [data, ...prev]);
        setQuery(""); setPrice("");
        setMsg("✅ Alerta criado!");
        setTimeout(() => setMsg(""), 3000);
      }
    } catch { setMsg("❌ Erro ao criar alerta."); }
    setLoading(false);
  };

  const remove = async (id: string) => {
    try {
      await fetch(`${API}/api/v1/alerts/${id}`, { method: "DELETE" });
      setAlerts(prev => prev.filter(a => a.id !== id));
    } catch {}
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "40px 20px" }}>
      <div style={{ maxWidth: 640, margin: "0 auto" }}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(124,106,255,.15)" }}>
              <Bell size={22} style={{ color: "var(--acc2)" }} />
            </div>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.5px" }}>Alertas de Preço</h1>
              <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>Seja notificado quando o preço cair</p>
            </div>
          </div>
        </motion.div>

        {/* Form */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          style={{ background: "var(--s2)", border: "1px solid var(--bd)", borderRadius: 20, padding: 24, marginBottom: 32 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--muted2)", marginBottom: 16, textTransform: "uppercase", letterSpacing: ".06em" }}>Novo alerta</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              type="text" value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Ex: iPhone 16 Pro, Nike Air Force 42..."
              style={{
                background: "var(--s3)", border: "1px solid var(--bd)", borderRadius: 12,
                padding: "13px 16px", fontSize: 15, color: "var(--txt)", outline: "none",
                width: "100%",
              }}
            />
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ position: "relative", flex: 1 }}>
                <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", fontSize: 13, color: "var(--muted2)", fontWeight: 600 }}>R$</span>
                <input
                  type="number" value={price} onChange={e => setPrice(e.target.value)}
                  placeholder="Preço alvo"
                  style={{
                    background: "var(--s3)", border: "1px solid var(--bd)", borderRadius: 12,
                    padding: "13px 16px 13px 36px", fontSize: 15, color: "var(--txt)", outline: "none",
                    width: "100%",
                  }}
                />
              </div>
              <button onClick={create} disabled={loading || !query || !price}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "0 20px", borderRadius: 12, border: "none", cursor: "pointer",
                  background: query && price ? "linear-gradient(135deg,#7c6aff,#a78bfa)" : "var(--s4)",
                  color: query && price ? "#fff" : "var(--muted2)",
                  fontSize: 14, fontWeight: 700, whiteSpace: "nowrap",
                  transition: "all .2s",
                }}>
                <Plus size={16} /> Criar
              </button>
            </div>
            {msg && <p style={{ fontSize: 13, color: msg.startsWith("✅") ? "var(--grn)" : "var(--red)" }}>{msg}</p>}
          </div>
        </motion.div>

        {/* Alerts list */}
        {alerts.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            style={{ textAlign: "center", padding: "60px 20px" }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>🔔</p>
            <p style={{ color: "var(--muted)", fontSize: 15 }}>Nenhum alerta criado ainda.</p>
            <p style={{ color: "var(--muted2)", fontSize: 13, marginTop: 4 }}>Crie um alerta acima e seja notificado quando o preço cair.</p>
          </motion.div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {alerts.map((a, i) => (
              <motion.div key={a.id}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                style={{ background: "var(--s2)", border: "1px solid var(--bd)", borderRadius: 16, padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,229,160,.08)", flexShrink: 0 }}>
                    <TrendingDown size={18} style={{ color: "var(--grn)" }} />
                  </div>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600 }}>{a.query}</p>
                    <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                      Alerta quando ≤ <span style={{ color: "var(--grn)", fontWeight: 700 }}>R$ {a.target_price.toFixed(2)}</span>
                    </p>
                  </div>
                </div>
                <button onClick={() => remove(a.id)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted2)", padding: 8, borderRadius: 8, display: "flex", flexShrink: 0 }}
                  onMouseEnter={e => (e.currentTarget.style.color = "var(--red)")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--muted2)")}>
                  <Trash2 size={16} />
                </button>
              </motion.div>
            ))}
          </div>
        )}

        {/* Back */}
        <div style={{ textAlign: "center", marginTop: 40 }}>
          <a href="/" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>← Voltar para busca</a>
        </div>
      </div>
    </div>
  );
}
