"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API } from "@/lib/api"
import Link from "next/link"

interface User {
  id: string
  name: string
  email: string
  is_admin: boolean
}

interface Alert {
  id: string
  query: string
  target_price: number
  is_active: boolean
  created_at: string
}

const fmtDate = (s: string) =>
  s ? new Date(s).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"

export default function PerfilPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("bpt_token")
    const stored = localStorage.getItem("bpt_user")
    if (!token || !stored) { router.push("/login"); return }

    const u = JSON.parse(stored) as User
    setUser(u)

    // Carrega alertas do usuário
    fetch(`${API}/api/v1/alerts`, {
      headers: { "Authorization": `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
        if (data.items) setAlerts(data.items)
      })
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem("bpt_token")
    localStorage.removeItem("bpt_user")
    localStorage.removeItem("admin_key")
    router.push("/login")
  }

  if (!user) return <div style={{ minHeight: "100vh", background: "#f0f4ff" }} />

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", fontFamily: "system-ui, sans-serif", color: "#1a1a2e" }}>
      {/* HEADER */}
      <div style={{ background: "#ffffff", borderBottom: "1px solid rgba(108,92,231,0.2)", padding: "12px 16px" }}>
        <div style={{ maxWidth: 1000, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <span style={{ fontSize: 22 }}>🛍️</span>
            <span style={{ fontWeight: 800, fontSize: 16, color: "#1a1a2e" }}>BestPriceToday</span>
          </a>
          <button onClick={handleLogout} style={{ background: "transparent", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "6px 14px", color: "#6b6b8a", cursor: "pointer", fontSize: 13 }}>
            ← Voltar
          </button>
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 20px" }}>
        {/* CARD: Minha Conta */}
        <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 14, padding: "24px", marginBottom: 24 }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 24, color: "#1a1a2e" }}>👤 Minha Conta</h1>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 20 }}>
            {/* Nome */}
            <div>
              <label style={{ display: "block", color: "#6b6b8a", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                Nome
              </label>
              <div style={{ background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "12px 14px", color: "#1a1a2e", fontSize: 14 }}>
                {user.name}
              </div>
            </div>

            {/* Email */}
            <div>
              <label style={{ display: "block", color: "#6b6b8a", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                Email
              </label>
              <div style={{ background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "12px 14px", color: "#1a1a2e", fontSize: 14 }}>
                {user.email}
              </div>
            </div>

            {/* Status */}
            <div>
              <label style={{ display: "block", color: "#6b6b8a", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                Tipo
              </label>
              <div style={{ background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "12px 14px", color: "#1a1a2e", fontSize: 14 }}>
                {user.is_admin ? "👑 Administrador" : "👤 Usuário"}
              </div>
            </div>
          </div>
        </div>

        {/* CARD: Meus Alertas */}
        {!user.is_admin && (
          <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 14, padding: "24px", marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, color: "#1a1a2e", margin: 0 }}>🔔 Meus Alertas ({alerts.length})</h2>
              <Link href="/alertas" style={{ textDecoration: "none" }}>
                <button style={{ background: "linear-gradient(135deg,#7c6aff,#a78bfa)", border: "none", borderRadius: 8, padding: "6px 14px", color: "#ffffff", cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                  + Novo Alerta
                </button>
              </Link>
            </div>

            {loading ? (
              <div style={{ textAlign: "center", color: "#6b6b8a", padding: "40px 20px" }}>Carregando...</div>
            ) : alerts.length === 0 ? (
              <div style={{ textAlign: "center", color: "#6b6b8a", padding: "40px 20px" }}>
                <p>Nenhum alerta cadastrado</p>
                <Link href="/alertas" style={{ textDecoration: "none", color: "#7c6aff", fontWeight: 700 }}>
                  Crie o seu primeiro alerta →
                </Link>
              </div>
            ) : (
              <div style={{ display: "grid", gap: 12 }}>
                {alerts.map(a => (
                  <div key={a.id} style={{ background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "14px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#1a1a2e", marginBottom: 4 }}>{a.query}</div>
                      <div style={{ fontSize: 12, color: "#6b6b8a" }}>
                        Alerta: R$ {a.target_price.toLocaleString("pt-BR")} • {fmtDate(a.created_at)}
                        {!a.is_active && " • ⏸️ Inativo"}
                      </div>
                    </div>
                    <div style={{ fontSize: 14 }}>
                      {a.is_active ? "✅" : "⏸️"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CARD: Ações */}
        <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 14, padding: "24px" }}>
          <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 16, color: "#1a1a2e" }}>⚙️ Ações</h3>
          <div style={{ display: "grid", gap: 10 }}>
            {user.is_admin && (
              <>
                <Link href="/admin" style={{ textDecoration: "none" }}>
                  <button style={{ width: "100%", background: "linear-gradient(135deg,#7c6aff,#a78bfa)", border: "none", borderRadius: 8, padding: "12px", color: "#ffffff", cursor: "pointer", fontSize: 14, fontWeight: 700 }}>
                    👑 Painel Admin
                  </button>
                </Link>
                <Link href="/aletubegames" style={{ textDecoration: "none" }}>
                  <button style={{ width: "100%", background: "linear-gradient(135deg,#7c6aff,#a78bfa)", border: "none", borderRadius: 8, padding: "12px", color: "#ffffff", cursor: "pointer", fontSize: 14, fontWeight: 700 }}>
                    🎥 AleTubeGames
                  </button>
                </Link>
              </>
            )}
            <Link href="/alertas" style={{ textDecoration: "none" }}>
              <button style={{ width: "100%", background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, padding: "12px", color: "#7c6aff", cursor: "pointer", fontSize: 14, fontWeight: 700 }}>
                🔔 Meus Alertas
              </button>
            </Link>
            <button 
              onClick={handleLogout}
              style={{ width: "100%", background: "#fef2f2", border: "1px solid rgba(244,63,94,0.2)", borderRadius: 8, padding: "12px", color: "#f43f5e", cursor: "pointer", fontSize: 14, fontWeight: 700 }}>
              🚪 Sair da Conta
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
