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

interface User {
  id: string
  name: string
  email: string
  is_admin: boolean
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser]       = useState<User | null>(null)
  const [alerts, setAlerts]   = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState<"alerts" | "account">("alerts")

  useEffect(() => {
    const token = localStorage.getItem("bpt_token")
    const stored = localStorage.getItem("bpt_user")
    if (!token || !stored) { router.push("/login"); return }

    const u = JSON.parse(stored) as User
    setUser(u)

    // Buscar alertas do usuário logado
    fetch(`${API}/api/v1/alerts?owner_id=${u.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => { setAlerts(Array.isArray(data) ? data : []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [router])

  const deleteAlert = async (id: string) => {
    const token = localStorage.getItem("bpt_token")
    const u = user
    if (!u) return
    await fetch(`${API}/api/v1/alerts/${id}?owner_id=${u.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token ?? ""}` },
    })
    setAlerts(prev => prev.filter(a => a.id !== id))
  }

  const logout = () => {
    const isAdmin = user?.is_admin
    localStorage.removeItem("bpt_token")
    localStorage.removeItem("bpt_user")
    router.push(isAdmin ? "/admin" : "/login")
  }

  if (loading) return (
    <div style={{ minHeight: "100vh", background: "#07070f", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "#475569" }}>Carregando...</p>
    </div>
  )

  const activeAlerts   = alerts.filter(a => a.is_active)
  const triggeredAlerts = alerts.filter(a => !a.is_active && a.triggered_at)

  return (
    <div style={{ minHeight: "100vh", background: "#07070f", color: "#fff", fontFamily: "system-ui" }}>
      {/* Header */}
      <header style={{ borderBottom: "1px solid #1e293b", padding: "16px 24px", background: "rgba(7,7,15,0.95)" }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 22 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 16, color: "#7c6aff" }}>BestPriceToday</span>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ color: "#94a3b8", fontSize: 13 }}>Olá, {user?.name?.split(" ")[0]}</span>
            <button onClick={logout} style={{ padding: "7px 14px", borderRadius: 8, background: "rgba(255,255,255,0.05)", border: "1px solid #2a2a3a", color: "#94a3b8", cursor: "pointer", fontSize: 12 }}>
              Sair
            </button>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
        <h1 style={{ fontSize: 26, fontWeight: 900, marginBottom: 32 }}>Minha conta</h1>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 28 }}>
          {(["alerts", "account"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "9px 20px", borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 600,
              background: tab === t ? "#7c6aff" : "rgba(255,255,255,0.04)",
              border: `1px solid ${tab === t ? "#7c6aff" : "#2a2a3a"}`,
              color: tab === t ? "#fff" : "#475569",
            }}>
              {t === "alerts" ? `🔔 Alertas (${activeAlerts.length})` : "👤 Conta"}
            </button>
          ))}
        </div>

        {/* Tab: Alertas */}
        {tab === "alerts" && (
          <div>
            {activeAlerts.length === 0 && triggeredAlerts.length === 0 ? (
              <div style={{ textAlign: "center", padding: "60px 0", color: "#475569" }}>
                <p style={{ fontSize: 40, marginBottom: 12 }}>🔔</p>
                <p style={{ fontSize: 16, marginBottom: 8 }}>Nenhum alerta criado ainda.</p>
                <p style={{ fontSize: 13 }}>
                  Busque um produto e clique em "Criar alerta de preço" para ser notificado quando o preço cair.
                </p>
                <Link href="/" style={{ display: "inline-block", marginTop: 20, padding: "11px 24px", borderRadius: 10, background: "#7c6aff", color: "#fff", textDecoration: "none", fontWeight: 700 }}>
                  Buscar produtos →
                </Link>
              </div>
            ) : (
              <>
                {activeAlerts.length > 0 && (
                  <>
                    <h2 style={{ color: "#94a3b8", fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 12 }}>
                      Ativos — aguardando preço cair
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 32 }}>
                      {activeAlerts.map(a => (
                        <AlertCard key={a.id} alert={a} onDelete={deleteAlert} />
                      ))}
                    </div>
                  </>
                )}
                {triggeredAlerts.length > 0 && (
                  <>
                    <h2 style={{ color: "#00e5a0", fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 12 }}>
                      ✅ Disparados — preço atingiu o alvo
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {triggeredAlerts.map(a => (
                        <AlertCard key={a.id} alert={a} onDelete={deleteAlert} triggered />
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* Tab: Conta */}
        {tab === "account" && (
          <div style={{ background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 16, padding: 28, maxWidth: 440 }}>
            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>Nome</label>
              <p style={{ color: "#fff", fontSize: 15 }}>{user?.name}</p>
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={labelStyle}>E-mail</label>
              <p style={{ color: "#fff", fontSize: 15 }}>{user?.email}</p>
            </div>
            <div style={{ marginBottom: 28 }}>
              <label style={labelStyle}>Tipo de conta</label>
              <p style={{ color: user?.is_admin ? "#fbbf24" : "#7c6aff", fontSize: 14, fontWeight: 700 }}>
                {user?.is_admin ? "👑 Administrador" : "👤 Usuário"}
              </p>
            </div>
            <button onClick={logout} style={{ padding: "11px 24px", borderRadius: 10, background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.3)", color: "#f43f5e", cursor: "pointer", fontWeight: 600, fontSize: 13 }}>
              Sair da conta
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function AlertCard({ alert, onDelete, triggered }: { alert: Alert; onDelete: (id: string) => void; triggered?: boolean }) {
  const fmt = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 })
  return (
    <div style={{
      background: "#0d0d1a", border: `1px solid ${triggered ? "rgba(0,229,160,0.2)" : "rgba(124,106,255,0.15)"}`,
      borderRadius: 12, padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
    }}>
      <div style={{ flex: 1 }}>
        <p style={{ color: "#fff", fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{alert.query}</p>
        <p style={{ color: triggered ? "#00e5a0" : "#a78bfa", fontSize: 13 }}>
          Alvo: R$ {fmt(alert.target_price)}
          {triggered && " ✓ Disparado!"}
        </p>
      </div>
      {!triggered && (
        <button onClick={() => onDelete(alert.id)} style={{
          padding: "7px 14px", borderRadius: 8, background: "rgba(244,63,94,.08)", border: "1px solid rgba(244,63,94,.2)",
          color: "#f43f5e", cursor: "pointer", fontSize: 12, fontWeight: 600, flexShrink: 0,
        }}>
          Remover
        </button>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  color: "#475569", fontSize: 11, fontWeight: 700,
  textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 4, display: "block",
}
