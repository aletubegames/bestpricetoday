"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API } from "@/lib/api"
import Link from "next/link"

interface Alert {
  id: string
  query: string
  target_price: number
  is_active: boolean
  created_at: string
  triggered_at: string | null
}

interface ShortLink {
  code: string
  url: string
  provider: string
  product: string
  clicks: number
  source: string
  created_at: string
}

interface User {
  id: string
  name: string
  email: string
  is_admin: boolean
}

const fmt = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 })
const fmtDate = (s: string) =>
  s ? new Date(s).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"

const PROVIDER_COLOR: Record<string, string> = {
  shopee: "#EE4D2D", aliexpress: "#FF4747",
  mercadolivre: "#FFE600", amazon: "#FF9900",
  lomadee: "#7C3AED", default: "#7c6aff",
}
const PROVIDER_LABEL: Record<string, string> = {
  shopee: "Shopee", aliexpress: "AliExpress",
  mercadolivre: "Mercado Livre", amazon: "Amazon",
  lomadee: "Lomadee", awin: "Awin",
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser]         = useState<User | null>(null)
  const [alerts, setAlerts]     = useState<Alert[]>([])
  const [links, setLinks]       = useState<ShortLink[]>([])
  const [totalClicks, setTotal] = useState(0)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState<"overview" | "alerts" | "links" | "account">("overview")
  const [copied, setCopied]     = useState<string | null>(null)

  useEffect(() => {
    const token  = localStorage.getItem("bpt_token")
    const stored = localStorage.getItem("bpt_user")
    if (!token || !stored) { router.push("/login"); return }

    const u = JSON.parse(stored) as User
    setUser(u)

    Promise.all([
      fetch(`${API}/api/v1/alerts?owner_id=${u.id}`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.ok ? r.json() : []),
      // Links do usuário (por source = tiktok_user ou web com user associado)
      fetch(`${API}/api/v1/admin/links/stats?limit=20`, {
        headers: { "X-Admin-Key": "" } // endpoint público de stats próprias
      }).then(r => r.ok ? r.json() : []).catch(() => []),
    ]).then(([alertData, linkData]) => {
      setAlerts(Array.isArray(alertData) ? alertData : [])
      const userLinks = Array.isArray(linkData)
        ? linkData.filter((l: ShortLink) => ["tiktok_user", "web"].includes(l.source))
        : []
      setLinks(userLinks)
      setTotal(userLinks.reduce((s: number, l: ShortLink) => s + (l.clicks || 0), 0))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [router])

  const deleteAlert = async (id: string) => {
    const token = localStorage.getItem("bpt_token")
    if (!user) return
    await fetch(`${API}/api/v1/alerts/${id}?owner_id=${user.id}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${token ?? ""}` },
    })
    setAlerts(prev => prev.filter(a => a.id !== id))
  }

  const copyLink = (url: string, code: string) => {
    navigator.clipboard.writeText(url)
    setCopied(code)
    setTimeout(() => setCopied(null), 2000)
  }

  const logout = () => {
    localStorage.removeItem("bpt_token")
    localStorage.removeItem("bpt_user")
    router.push("/login")
  }

  if (loading) return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ color: "#475569", fontSize: 14 }}>Carregando...</div>
    </div>
  )

  const activeAlerts    = alerts.filter(a => a.is_active)
  const triggeredAlerts = alerts.filter(a => !a.is_active && a.triggered_at)
  const topLinks        = [...links].sort((a, b) => b.clicks - a.clicks).slice(0, 5)

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", color: "#1a1a2e", fontFamily: "system-ui" }}>
      {/* Header */}
      <header style={{ borderBottom: "1px solid #1e293b", padding: "14px 24px", background: "rgba(255,255,255,0.97)", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ maxWidth: 960, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 20 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 15, color: "#7c6aff" }}>BestPriceToday</span>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ color: "#6b6b8a", fontSize: 12 }}>Olá, {user?.name?.split(" ")[0]} 👋</span>
            <button onClick={logout} style={{ padding: "6px 14px", borderRadius: 8, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(108,92,231,0.2)", color: "#4a4a6a", cursor: "pointer", fontSize: 12 }}>
              Sair
            </button>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "32px 20px" }}>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 28, flexWrap: "wrap" }}>
          {([
            ["overview", "📊 Visão geral"],
            ["alerts",   `🔔 Alertas (${activeAlerts.length})`],
            ["links",    `🔗 Meus links (${links.length})`],
            ["account",  "👤 Conta"],
          ] as const).map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "9px 18px", borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 600,
              background: tab === t ? "#7c6aff" : "rgba(255,255,255,0.04)",
              border: `1px solid ${tab === t ? "#7c6aff" : "rgba(108,92,231,0.2)"}`,
              color: tab === t ? "#fff" : "#475569",
            }}>
              {label}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW ── */}
        {tab === "overview" && (
          <div>
            {/* Stats cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 14, marginBottom: 28 }}>
              {[
                { label: "Alertas ativos",     value: activeAlerts.length,   icon: "🔔", color: "#a78bfa" },
                { label: "Alertas disparados", value: triggeredAlerts.length, icon: "✅", color: "#00e5a0" },
                { label: "Links gerados",      value: links.length,           icon: "🔗", color: "#7c6aff" },
                { label: "Cliques totais",     value: totalClicks,            icon: "👆", color: "#fbbf24" },
              ].map(s => (
                <div key={s.label} style={{ background: "#ffffff", border: "1px solid #1e293b", borderRadius: 14, padding: "18px 20px" }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{s.icon}</div>
                  <div style={{ fontSize: 28, fontWeight: 900, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: "#475569", marginTop: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em" }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Top links */}
            {topLinks.length > 0 && (
              <div style={{ background: "#ffffff", border: "1px solid #1e293b", borderRadius: 14, padding: "20px 24px", marginBottom: 20 }}>
                <h2 style={{ fontSize: 13, fontWeight: 700, color: "#6b6b8a", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 16 }}>
                  🏆 Links mais clicados
                </h2>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {topLinks.map((l, i) => (
                    <div key={l.code} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ width: 22, height: 22, borderRadius: 6, background: "rgba(124,106,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800, color: "#7c6aff", flexShrink: 0 }}>
                        {i + 1}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, color: "#1a1a2e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {l.product || `Link /${l.code}`}
                        </div>
                        <div style={{ fontSize: 10, color: "#334155", marginTop: 2 }}>
                          <span style={{ color: PROVIDER_COLOR[l.provider] || "#7c6aff", marginRight: 6 }}>
                            {PROVIDER_LABEL[l.provider] || l.provider}
                          </span>
                          {fmtDate(l.created_at)}
                        </div>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: "#fbbf24", flexShrink: 0 }}>
                        {l.clicks} cliques
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* CTAs */}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Link href="/" style={{ padding: "11px 22px", borderRadius: 10, background: "#7c6aff", color: "#1a1a2e", fontWeight: 700, fontSize: 13, textDecoration: "none" }}>
                🔍 Buscar produtos
              </Link>
              <button onClick={() => setTab("alerts")} style={{ padding: "11px 22px", borderRadius: 10, background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.25)", color: "#a78bfa", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
                🔔 Ver alertas
              </button>
            </div>
          </div>
        )}

        {/* ── ALERTAS ── */}
        {tab === "alerts" && (
          <div>
            {activeAlerts.length === 0 && triggeredAlerts.length === 0 ? (
              <div style={{ textAlign: "center", padding: "60px 0", color: "#475569" }}>
                <p style={{ fontSize: 40, marginBottom: 12 }}>🔔</p>
                <p style={{ fontSize: 15, marginBottom: 8, color: "#4a4a6a" }}>Nenhum alerta criado ainda.</p>
                <p style={{ fontSize: 13, marginBottom: 24 }}>Busque um produto e clique em "Criar alerta de preço".</p>
                <Link href="/" style={{ padding: "11px 24px", borderRadius: 10, background: "#7c6aff", color: "#1a1a2e", textDecoration: "none", fontWeight: 700 }}>
                  Buscar produtos →
                </Link>
              </div>
            ) : (
              <>
                {activeAlerts.length > 0 && (
                  <section style={{ marginBottom: 28 }}>
                    <h2 style={sectionLabel}>Aguardando preço cair</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {activeAlerts.map(a => <AlertCard key={a.id} alert={a} onDelete={deleteAlert} />)}
                    </div>
                  </section>
                )}
                {triggeredAlerts.length > 0 && (
                  <section>
                    <h2 style={{ ...sectionLabel, color: "#00e5a0" }}>✅ Disparados — preço atingiu o alvo</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {triggeredAlerts.map(a => <AlertCard key={a.id} alert={a} onDelete={deleteAlert} triggered />)}
                    </div>
                  </section>
                )}
              </>
            )}
          </div>
        )}

        {/* ── LINKS ── */}
        {tab === "links" && (
          <div>
            {links.length === 0 ? (
              <div style={{ textAlign: "center", padding: "60px 0", color: "#475569" }}>
                <p style={{ fontSize: 40, marginBottom: 12 }}>🔗</p>
                <p style={{ fontSize: 15, marginBottom: 8, color: "#4a4a6a" }}>Nenhum link gerado ainda.</p>
                <p style={{ fontSize: 13, marginBottom: 24 }}>Compartilhe produtos no TikTok para gerar links rastreados.</p>
                <Link href="/" style={{ padding: "11px 24px", borderRadius: 10, background: "#7c6aff", color: "#1a1a2e", textDecoration: "none", fontWeight: 700 }}>
                  Buscar produtos →
                </Link>
              </div>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                  <h2 style={sectionLabel}>Seus links rastreados</h2>
                  <span style={{ fontSize: 12, color: "#334155" }}>{totalClicks} cliques totais</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {links.map(l => (
                    <div key={l.code} style={{
                      background: "#ffffff", border: "1px solid #1e293b", borderRadius: 12,
                      padding: "14px 18px", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
                    }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, color: "#1a1a2e", fontWeight: 600, marginBottom: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {l.product || `bestpricetoday.vercel.app/r/${l.code}`}
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <span style={{ fontSize: 10, color: PROVIDER_COLOR[l.provider] || "#7c6aff", fontWeight: 700, textTransform: "uppercase" }}>
                            {PROVIDER_LABEL[l.provider] || l.provider}
                          </span>
                          <span style={{ fontSize: 10, color: "#334155" }}>{fmtDate(l.created_at)}</span>
                          <span style={{ fontSize: 10, color: "#334155", fontFamily: "monospace" }}>/r/{l.code}</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 16, fontWeight: 900, color: "#fbbf24" }}>{l.clicks}</div>
                          <div style={{ fontSize: 9, color: "#475569", textTransform: "uppercase" }}>cliques</div>
                        </div>
                        <button onClick={() => copyLink(`https://bestpricetoday.vercel.app/r/${l.code}`, l.code)}
                          style={{
                            padding: "7px 14px", borderRadius: 8, cursor: "pointer", fontSize: 11, fontWeight: 700,
                            background: copied === l.code ? "rgba(0,229,160,0.12)" : "rgba(124,106,255,0.12)",
                            border: `1px solid ${copied === l.code ? "rgba(0,229,160,0.25)" : "rgba(124,106,255,0.25)"}`,
                            color: copied === l.code ? "#00e5a0" : "#a78bfa",
                          }}>
                          {copied === l.code ? "✓ Copiado" : "Copiar"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── CONTA ── */}
        {tab === "account" && (
          <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 16, padding: 28, maxWidth: 440 }}>
            {[
              { label: "Nome",          value: user?.name },
              { label: "E-mail",        value: user?.email },
              { label: "Tipo de conta", value: user?.is_admin ? "👑 Administrador" : "👤 Usuário", highlight: true },
            ].map(f => (
              <div key={f.label} style={{ marginBottom: 20 }}>
                <label style={labelStyle}>{f.label}</label>
                <p style={{ color: f.highlight ? (user?.is_admin ? "#fbbf24" : "#7c6aff") : "#fff", fontSize: 15, fontWeight: f.highlight ? 700 : 400 }}>
                  {f.value}
                </p>
              </div>
            ))}
            <button onClick={logout} style={{ padding: "11px 24px", borderRadius: 10, background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.3)", color: "#f43f5e", cursor: "pointer", fontWeight: 600, fontSize: 13 }}>
              Sair da conta
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-componentes ──────────────────────────────────────────────────────────

function AlertCard({ alert, onDelete, triggered }: { alert: Alert; onDelete: (id: string) => void; triggered?: boolean }) {
  return (
    <div style={{
      background: "#ffffff",
      border: `1px solid ${triggered ? "rgba(0,229,160,0.2)" : "rgba(124,106,255,0.15)"}`,
      borderRadius: 12, padding: "14px 18px",
      display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
    }}>
      <div style={{ flex: 1 }}>
        <p style={{ color: "#1a1a2e", fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{alert.query}</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <p style={{ color: triggered ? "#00e5a0" : "#a78bfa", fontSize: 12 }}>
            Alvo: R$ {fmt(alert.target_price)}{triggered && " — ✅ Disparado!"}
          </p>
          <p style={{ color: "#334155", fontSize: 11 }}>
            Criado {new Date(alert.created_at).toLocaleDateString("pt-BR")}
          </p>
        </div>
      </div>
      {!triggered && (
        <button onClick={() => onDelete(alert.id)} style={{
          padding: "7px 14px", borderRadius: 8,
          background: "rgba(244,63,94,.08)", border: "1px solid rgba(244,63,94,.2)",
          color: "#f43f5e", cursor: "pointer", fontSize: 12, fontWeight: 600, flexShrink: 0,
        }}>
          Remover
        </button>
      )}
    </div>
  )
}

const sectionLabel: React.CSSProperties = {
  color: "#6b6b8a", fontSize: 11, fontWeight: 700,
  textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 12,
}

const labelStyle: React.CSSProperties = {
  color: "#475569", fontSize: 11, fontWeight: 700,
  textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 4, display: "block",
}
