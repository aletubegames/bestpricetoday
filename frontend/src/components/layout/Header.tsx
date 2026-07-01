"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import styles from "./Header.module.css"

type HeaderVariant = "default" | "minimal" | "admin" | "dashboard"

type StoredUser = { name: string; is_admin: boolean }

interface HeaderProps {
  variant?: HeaderVariant
  safeBadge?: string
  onLogout?: () => void
}

function readStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null
  try {
    const stored = localStorage.getItem("bpt_user")
    if (!stored) return null
    const parsed = JSON.parse(stored) as Partial<StoredUser>
    if (
      parsed &&
      typeof parsed === "object" &&
      typeof parsed.name === "string" &&
      typeof parsed.is_admin === "boolean"
    ) {
      return parsed as StoredUser
    }
  } catch {
    // ignore
  }
  return null
}

function logout() {
  if (typeof window === "undefined") return
  localStorage.removeItem("bpt_token")
  localStorage.removeItem("bpt_user")
  window.location.href = "/login"
}

function useLogout(onLogout?: () => void) {
  return () => {
    if (onLogout) {
      onLogout()
    } else {
      logout()
    }
  }
}

function Logo() {
  return (
    <Link href="/" className={styles.logo}>
      <span className={styles.logoIcon}>🛍️</span>
      <span className={styles.logoText}>
        <span className={styles.logoBest}>BestPrice</span>
        <span className={styles.logoToday}>Today</span>
      </span>
    </Link>
  )
}

function MobileMenu({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        className={styles.mobileMenuBtn}
        onClick={() => setOpen(!open)}
        aria-label={open ? "Fechar menu" : "Abrir menu"}
        aria-expanded={open}
      >
        <span style={{ fontSize: 18 }}>{open ? "✕" : "☰"}</span>
      </button>
      <div className={`${styles.mobileMenu} ${open ? styles.mobileMenuOpen : ""}`}>
        {children}
      </div>
    </>
  )
}

function DefaultNav() {
  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        <Link href="/" className={styles.navLink}>
          🔍 <span className={styles.navText}>Buscar</span>
        </Link>
        <Link href="/alertas" className={styles.navLink}>
          🔔 <span className={styles.navText}>Alertas</span>
        </Link>
        <Link href="/cupons" className={styles.navLink}>
          🏷️ <span className={styles.navText}>Cupons</span>
        </Link>
        <AuthButton />
      </nav>
      <MobileMenu>
        <Link href="/" className={styles.mobileMenuLink} onClick={() => {}}>
          🔍 Buscar ofertas
        </Link>
        <Link href="/alertas" className={styles.mobileMenuLink}>
          🔔 Meus alertas
        </Link>
        <Link href="/cupons" className={styles.mobileMenuLink}>
          🏷️ Produtos com cupom
        </Link>
        <MobileAuthLinks />
      </MobileMenu>
    </>
  )
}

function AuthButton() {
  const [user, setUser] = useState<StoredUser | null>(null)
  useEffect(() => {
    setUser(readStoredUser())
  }, [])

  if (!user) {
    return (
      <Link href="/login" className={styles.btn}>
        Entrar
      </Link>
    )
  }

  return (
    <div className={styles.nav}>
      {user.is_admin && (
        <>
          <Link href="/afiliados" className={`${styles.btn} ${styles.btnGreen}`}>
            💰 <span className={styles.navText}>Afiliados</span>
          </Link>
          <Link href="/aletubegames" className={`${styles.btn} ${styles.btnYellow}`}>
            🎥 <span className={styles.navText}>AleTube</span>
          </Link>
        </>
      )}
      <Link href={user.is_admin ? "/admin" : "/dashboard"} className={`${styles.btn} ${styles.btnPurple}`}>
        <span>{user.is_admin ? "📊" : "👤"}</span>
        <span className={styles.navText}>{user.is_admin ? "Painel" : user.name.split(" ")[0]}</span>
      </Link>
    </div>
  )
}

function MobileAuthLinks() {
  const [user, setUser] = useState<StoredUser | null>(null)
  useEffect(() => {
    setUser(readStoredUser())
  }, [])

  if (!user) {
    return (
      <Link href="/login" className={styles.mobileMenuLink}>
        🔑 Entrar / Criar conta
      </Link>
    )
  }

  return (
    <>
      {user.is_admin && (
        <>
          <Link href="/admin" className={styles.mobileMenuLink}>
            📊 Painel Admin
          </Link>
          <Link href="/afiliados" className={styles.mobileMenuLink}>
            💰 Afiliados
          </Link>
          <Link href="/aletubegames" className={styles.mobileMenuLink}>
            🎥 AleTubeGames
          </Link>
        </>
      )}
      <Link href="/dashboard" className={styles.mobileMenuLink}>
        👤 Minha conta
      </Link>
      <button onClick={logout} className={styles.mobileMenuLink} style={{ textAlign: "left" }}>
        🚪 Sair
      </button>
    </>
  )
}

function AdminNav({ onLogout }: { onLogout?: () => void }) {
  const handleLogout = useLogout(onLogout)
  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        <Link href="/admin" className={`${styles.btn} ${styles.btnPrimary}`}>
          📊 <span className={styles.navText}>Admin</span>
        </Link>
        <Link href="/afiliados" className={styles.btn}>
          💰 <span className={styles.navText}>Afiliados</span>
        </Link>
        <Link href="/aletubegames" className={styles.btn}>
          🎥 <span className={styles.navText}>AleTube</span>
        </Link>
        <Link href="/dashboard" className={styles.btn}>
          👤 <span className={styles.navText}>Dashboard</span>
        </Link>
        <Link href="/" className={styles.btn}>
          ← <span className={styles.navText}>Home</span>
        </Link>
        <button onClick={handleLogout} className={styles.btn}>
          🚪 <span className={styles.navText}>Sair</span>
        </button>
      </nav>
      <MobileMenu>
        <Link href="/admin" className={styles.mobileMenuLink}>
          📊 Admin
        </Link>
        <Link href="/afiliados" className={styles.mobileMenuLink}>
          💰 Afiliados
        </Link>
        <Link href="/aletubegames" className={styles.mobileMenuLink}>
          🎥 AleTubeGames
        </Link>
        <Link href="/dashboard" className={styles.mobileMenuLink}>
          👤 Dashboard
        </Link>
        <Link href="/" className={styles.mobileMenuLink}>
          ← Home
        </Link>
        <button onClick={handleLogout} className={styles.mobileMenuLink} style={{ textAlign: "left" }}>
          🚪 Sair
        </button>
      </MobileMenu>
    </>
  )
}

function DashboardNav({ onLogout }: { onLogout?: () => void }) {
  const [user, setUser] = useState<StoredUser | null>(null)
  useEffect(() => {
    setUser(readStoredUser())
  }, [])
  const handleLogout = useLogout(onLogout)

  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        {user && <span className={styles.userName}>Olá, {user.name.split(" ")[0]} 👋</span>}
        <Link href="/" className={styles.btn}>
          ← <span className={styles.navText}>Home</span>
        </Link>
        <button onClick={handleLogout} className={styles.btn}>
          🚪 <span className={styles.navText}>Sair</span>
        </button>
      </nav>
      <MobileMenu>
        <Link href="/" className={styles.mobileMenuLink}>
          ← Home
        </Link>
        <button onClick={handleLogout} className={styles.mobileMenuLink} style={{ textAlign: "left" }}>
          🚪 Sair
        </button>
      </MobileMenu>
    </>
  )
}

export default function Header({ variant = "default", safeBadge, onLogout }: HeaderProps) {
  if (variant === "minimal") {
    return (
      <header className={styles.root}>
        <div className={styles.inner}>
          <Logo />
          <div className={styles.right}>
            <Link href="/" className={styles.btn}>
              ← <span className={styles.navText}>Home</span>
            </Link>
            {safeBadge && <span className={styles.badge}>{safeBadge}</span>}
          </div>
        </div>
      </header>
    )
  }

  if (variant === "admin") {
    return (
      <header className={styles.root}>
        <div className={styles.inner}>
          <div className={styles.left}>
            <Logo />
            <span className={styles.adminBadge}>Admin</span>
          </div>
          <AdminNav onLogout={onLogout} />
        </div>
      </header>
    )
  }

  if (variant === "dashboard") {
    return (
      <header className={styles.root}>
        <div className={styles.inner}>
          <Logo />
          <DashboardNav onLogout={onLogout} />
        </div>
      </header>
    )
  }

  return (
    <header className={styles.root}>
      <div className={styles.inner}>
        <Logo />
        <DefaultNav />
      </div>
    </header>
  )
}
