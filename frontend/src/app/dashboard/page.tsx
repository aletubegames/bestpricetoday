"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import Header from "@/components/layout/Header"
import { API_BASE as API, apiFetch } from "@/lib/api"
import { isTokenExpired } from "@/lib/utils"
import styles from "./page.module.css"

interface User { id: string; name: string; email: string; is_admin: boolean }
interface Alert { id: string; query: string; target_price: number; is_active: boolean; created_at: string; triggered_at: string | null }
interface Favorite { id: string; product_id: string; owner_id: string; created_at: string }

const fmt = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 2 })
const fmtDate = (s: string) => s ? new Date(s).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) : "—"

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("bpt_token")
    const stored = localStorage.getItem("bpt_user")
    if (!token || !stored || isTokenExpired(token)) {
      localStorage.removeItem("bpt_token")
      localStorage.removeItem("bpt_user")
      router.push("/login"); return
    }
    let u: User
    try { u = JSON.parse(stored) as User } catch {
      localStorage.removeItem("bpt_token"); localStorage.removeItem("bpt_user")
      router.push("/login"); return
    }
    setUser(u)

    // Busca alertas e favoritos em paralelo
    const anonId = typeof window !== "undefined" ? localStorage.getItem("bpt_anon_id") : null
    const ownerId = u.id || anonId || ""

    Promise.all([
      apiFetch(`${API}/api/v1/alerts?owner_id=${u.id}`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.ok ? r.json() : []).then(d => Array.isArray(d) ? d : d?.items || []).catch(() => []),
      ownerId ? apiFetch(`${API}/api/v1/favorites?owner_id=${ownerId}`)
        .then(r => r.ok ? r.json() : []).then(d => Array.isArray(d) ? d : []).catch(() => []) : Promise.resolve([]),
    ]).then(([a, f]) => { setAlerts(a); setFavorites(f); setLoading(false) })
  }, [router])

  const deleteAlert = async (id: string) => {
    const token = localStorage.getItem("bpt_token")
    if (!user) return
    await apiFetch(`${API}/api/v1/alerts/${id}?owner_id=${user.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token ?? ""}` } })
    setAlerts(prev => (prev || []).filter(a => a.id !== id))
  }

  const removeFavorite = async (id: string) => {
    if (!user) return
    await apiFetch(`${API}/api/v1/favorites/${id}?owner_id=${user.id}`, { method: "DELETE" })
    setFavorites(prev => (prev || []).filter(f => f.id !== id))
  }

  const logout = () => {
    localStorage.removeItem("bpt_token")
    localStorage.removeItem("bpt_user")
    localStorage.removeItem("admin_key")
    router.push("/login")
  }

  if (loading || !user) return (
    <div className={styles.root}>
      <div className={styles.loading}>Carregando...</div>
    </div>
  )

  const activeAlerts = (alerts || []).filter(a => a.is_active)
  const triggeredAlerts = (alerts || []).filter(a => !a.is_active && a.triggered_at)

  return (
    <div className={styles.root}>
      <Header variant="dashboard" onLogout={logout} />
      <div className={styles.container}>

        {/* Welcome */}
        <div className={styles.welcome}>
          <h1 className={styles.welcomeTitle}>Olá, {user.name.split(" ")[0]}! 👋</h1>
          <p className={styles.welcomeSub}>Aqui está um resumo da sua atividade no BestPriceToday.</p>
        </div>

        {/* Stats */}
        <div className={styles.statsGrid}>
          <div className={styles.statCard} style={{ ["--c" as string]: "var(--acc)" }}>
            <div className={styles.statIcon}>🔔</div>
            <div className={styles.statValue}>{activeAlerts.length}</div>
            <div className={styles.statLabel}>Alertas ativos</div>
          </div>
          <div className={styles.statCard} style={{ ["--c" as string]: "var(--grn)" }}>
            <div className={styles.statIcon}>✅</div>
            <div className={styles.statValue}>{triggeredAlerts.length}</div>
            <div className={styles.statLabel}>Alertas disparados</div>
          </div>
          <div className={styles.statCard} style={{ ["--c" as string]: "var(--ylw)" }}>
            <div className={styles.statIcon}>⭐</div>
            <div className={styles.statValue}>{favorites.length}</div>
            <div className={styles.statLabel}>Favoritos</div>
          </div>
        </div>

        {/* Quick actions */}
        <div className={styles.actionsRow}>
          <Link href="/" className={styles.actionBtn}>🔍 Buscar produtos</Link>
          <Link href="/cupons" className={`${styles.actionBtn} ${styles.actionBtnGreen}`}>🏷️ Ver cupons</Link>
          {user.is_admin && <Link href="/admin" className={`${styles.actionBtn} ${styles.actionBtnPurple}`}>📊 Painel Admin</Link>}
          {user.is_admin && <Link href="/afiliados" className={`${styles.actionBtn} ${styles.actionBtnYellow}`}>💰 Afiliados</Link>}
          {user.is_admin && <Link href="/aletubegames" className={`${styles.actionBtn} ${styles.actionBtnRed}`}>📹 AleTube</Link>}
        </div>

        {/* Two columns: alerts + favorites */}
        <div className={styles.twoCol}>
          {/* Alertas */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>🔔 Meus Alertas</div>
              <Link href="/" className={styles.cardLink}>+ Criar</Link>
            </div>

            {activeAlerts.length === 0 && triggeredAlerts.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>🔔</div>
                <p className={styles.emptyText}>Nenhum alerta criado ainda.</p>
                <p className={styles.emptySub}>Busque um produto e clique em "Criar alerta de preço".</p>
                <Link href="/" className={styles.emptyBtn}>Buscar produtos →</Link>
              </div>
            ) : (
              <div className={styles.list}>
                {activeAlerts.length > 0 && (
                  <div className={styles.listSection}>
                    <div className={styles.listSectionLabel}>Aguardando preço cair</div>
                    {activeAlerts.map(a => (
                      <AlertRow key={a.id} alert={a} onDelete={deleteAlert} />
                    ))}
                  </div>
                )}
                {triggeredAlerts.length > 0 && (
                  <div className={styles.listSection}>
                    <div className={styles.listSectionLabel} style={{ color: "var(--grn)" }}>✅ Disparados</div>
                    {triggeredAlerts.map(a => (
                      <AlertRow key={a.id} alert={a} onDelete={deleteAlert} triggered />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Favoritos */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitle}>⭐ Meus Favoritos</div>
            </div>
            {favorites.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>⭐</div>
                <p className={styles.emptyText}>Nenhum favorito ainda.</p>
                <p className={styles.emptySub}>Clique no ❤ ao lado de um produto para salvá-lo.</p>
                <Link href="/" className={styles.emptyBtn}>Explorar produtos →</Link>
              </div>
            ) : (
              <div className={styles.list}>
                {favorites.map(f => (
                  <div key={f.id} className={styles.favRow}>
                    <Link href={`/produto/${f.product_id}`} className={styles.favLink}>
                      Ver produto
                    </Link>
                    <span className={styles.favDate}>Salvo em {fmtDate(f.created_at)}</span>
                    <button onClick={() => removeFavorite(f.id)} className={styles.favRemove}>✕</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Account info */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardTitle}>👤 Minha Conta</div>
            <Link href="/perfil" className={styles.cardLink}>Editar →</Link>
          </div>
          <div className={styles.accountGrid}>
            <div className={styles.accountField}>
              <div className={styles.accountLabel}>Nome</div>
              <div className={styles.accountValue}>{user.name}</div>
            </div>
            <div className={styles.accountField}>
              <div className={styles.accountLabel}>E-mail</div>
              <div className={styles.accountValue}>{user.email}</div>
            </div>
            <div className={styles.accountField}>
              <div className={styles.accountLabel}>Tipo de conta</div>
              <div className={styles.accountValue}>
                <span className={`${styles.tag} ${user.is_admin ? styles.tagPurple : styles.tagBlue}`}>
                  {user.is_admin ? "👑 Administrador" : "👤 Usuário"}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

function AlertRow({ alert, onDelete, triggered }: { alert: Alert; onDelete: (id: string) => void; triggered?: boolean }) {
  return (
    <div className={`${styles.alertRow} ${triggered ? styles.alertRowTriggered : ""}`}>
      <div className={styles.alertInfo}>
        <p className={styles.alertQuery}>{alert.query}</p>
        <div className={styles.alertMeta}>
          <span style={{ color: triggered ? "var(--grn)" : "var(--acc)" }}>
            Alvo: R$ {fmt(alert.target_price)}{triggered && " — ✅ Disparado!"}
          </span>
          <span className={styles.alertDate}>Criado {fmtDate(alert.created_at)}</span>
        </div>
      </div>
      {!triggered && (
        <button onClick={() => onDelete(alert.id)} className={styles.alertDelete}>Remover</button>
      )}
    </div>
  )
}
