"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import {
  Search,
  Bell,
  Tag,
  User,
  DollarSign,
  Youtube,
  LayoutDashboard,
  LogOut,
  Home,
  Menu,
  X,
} from "lucide-react"
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
      <img
        src="/logo-header.png"
        alt="BestPriceToday"
        width={50}
        height={50}
        className={styles.logoImg}
      />
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
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>
      <div className={`${styles.mobileMenu} ${open ? styles.mobileMenuOpen : ""}`}>
        {children}
      </div>
    </>
  )
}

function DefaultNav() {
  const pathname = usePathname()
  const links = [
    { href: "/", label: "Buscar", icon: Search },
    { href: "/alertas", label: "Alertas", icon: Bell },
    { href: "/cupons", label: "Cupons", icon: Tag },
  ]
  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        <HeaderSearch />
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`${styles.navLink} ${pathname === href ? styles.navLinkActive : ""}`}
          >
            <Icon size={14} />
            <span className={styles.navText}>{label}</span>
          </Link>
        ))}
        <AuthButton />
      </nav>
      <MobileMenu>
        <HeaderSearch />
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`${styles.mobileMenuLink} ${pathname === href ? styles.mobileMenuLinkActive : ""}`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
        <MobileAuthLinks />
      </MobileMenu>
    </>
  )
}

/** Busca compacta para o header — navega para /produto/{query} */
function HeaderSearch() {
  const router = useRouter()
  const [value, setValue] = useState("")
  const [focused, setFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const submit = (v: string) => {
    const q = v.trim()
    if (q.length >= 2) {
      router.push(`/produto/${encodeURIComponent(q)}`)
      setFocused(false)
      setValue("")
    }
  }

  return (
    <form
      className={styles.headerSearch}
      onSubmit={(e) => { e.preventDefault(); submit(value) }}
    >
      <Search size={16} className={styles.headerSearchIcon} />
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 200)}
        placeholder="Buscar produto..."
        className={styles.headerSearchInput}
        aria-label="Buscar produto"
      />
    </form>
  )
}

function AuthButton() {
  const [user, setUser] = useState<StoredUser | null>(null)
  const [mounted, setMounted] = useState(false)
  const pathname = usePathname()
  useEffect(() => {
    setUser(readStoredUser())
    setMounted(true)
  }, [])

  // Evita flash de hidratação: SSR renderiza null, cliente também até mounted
  if (!mounted) return null

  if (!user) {
    return (
      <Link href="/login" className={`${styles.btn} ${styles.btnPrimary}`}>
        <User size={14} />
        <span className={styles.navText}>Entrar</span>
      </Link>
    )
  }

  return (
    <div className={styles.nav}>
      {user.is_admin && (
        <>
          <Link href="/afiliados" className={`${styles.btn} ${styles.btnGreen} ${pathname === "/afiliados" ? styles.btnActive : ""}`}>
            <DollarSign size={14} />
            <span className={styles.navText}>Afiliados</span>
          </Link>
          <Link href="/aletubegames" className={`${styles.btn} ${styles.btnYellow} ${pathname === "/aletubegames" ? styles.btnActive : ""}`}>
            <Youtube size={14} />
            <span className={styles.navText}>AleTube</span>
          </Link>
          <Link href="/admin" className={`${styles.btn} ${styles.btnPurple} ${pathname === "/admin" ? styles.btnActive : ""}`}>
            <LayoutDashboard size={14} />
            <span className={styles.navText}>Painel</span>
          </Link>
        </>
      )}
      {!user.is_admin && (
        <Link href="/perfil" className={`${styles.btn} ${styles.btnPurple} ${pathname === "/perfil" ? styles.btnActive : ""}`}>
          <User size={14} />
          <span className={styles.navText}>{user.name.split(" ")[0]}</span>
        </Link>
      )}
    </div>
  )
}

function MobileAuthLinks() {
  const [user, setUser] = useState<StoredUser | null>(null)
  const [mounted, setMounted] = useState(false)
  const pathname = usePathname()
  useEffect(() => {
    setUser(readStoredUser())
    setMounted(true)
  }, [])

  // Evita flash de hidratação
  if (!mounted) return null

  if (!user) {
    return (
      <Link href="/login" className={`${styles.mobileMenuLink} ${pathname === "/login" ? styles.mobileMenuLinkActive : ""}`}>
        <User size={18} />
        Entrar / Criar conta
      </Link>
    )
  }

  return (
    <>
      {user.is_admin && (
        <>
          <Link href="/admin" className={`${styles.mobileMenuLink} ${pathname === "/admin" ? styles.mobileMenuLinkActive : ""}`}>
            <LayoutDashboard size={18} />
            Painel Admin
          </Link>
          <Link href="/afiliados" className={`${styles.mobileMenuLink} ${pathname === "/afiliados" ? styles.mobileMenuLinkActive : ""}`}>
            <DollarSign size={18} />
            Afiliados
          </Link>
          <Link href="/aletubegames" className={`${styles.mobileMenuLink} ${pathname === "/aletubegames" ? styles.mobileMenuLinkActive : ""}`}>
            <Youtube size={18} />
            AleTubeGames
          </Link>
        </>
      )}
      {!user.is_admin && (
        <Link href="/perfil" className={`${styles.mobileMenuLink} ${pathname === "/perfil" ? styles.mobileMenuLinkActive : ""}`}>
          <User size={18} />
          Meu perfil
        </Link>
      )}
      <button onClick={logout} className={`${styles.mobileMenuLink} ${styles.mobileMenuLinkLeft}`}>
        <LogOut size={18} />
        Sair
      </button>
    </>
  )
}

function AdminNav({ onLogout }: { onLogout?: () => void }) {
  const handleLogout = useLogout(onLogout)
  const pathname = usePathname()
  const adminLinks = [
    { href: "/admin", label: "Admin", icon: LayoutDashboard },
    { href: "/afiliados", label: "Afiliados", icon: DollarSign },
    { href: "/aletubegames", label: "AleTube", icon: Youtube },
    { href: "/dashboard", label: "Dashboard", icon: User },
  ]
  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        {adminLinks.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`${styles.btn} ${pathname === href ? styles.btnActive : ""}`}
          >
            <Icon size={14} />
            <span className={styles.navText}>{label}</span>
          </Link>
        ))}
        <Link href="/" className={styles.btn}>
          <Home size={14} />
          <span className={styles.navText}>Home</span>
        </Link>
        <button onClick={handleLogout} className={styles.btn}>
          <LogOut size={14} />
          <span className={styles.navText}>Sair</span>
        </button>
      </nav>
      <MobileMenu>
        {adminLinks.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`${styles.mobileMenuLink} ${pathname === href ? styles.mobileMenuLinkActive : ""}`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
        <Link href="/" className={styles.mobileMenuLink}>
          <Home size={18} />
          Home
        </Link>
        <button onClick={handleLogout} className={`${styles.mobileMenuLink} ${styles.mobileMenuLinkLeft}`}>
          <LogOut size={18} />
          Sair
        </button>
      </MobileMenu>
    </>
  )
}

function DashboardNav({ onLogout }: { onLogout?: () => void }) {
  const [user, setUser] = useState<StoredUser | null>(null)
  const pathname = usePathname()
  useEffect(() => {
    setUser(readStoredUser())
  }, [])
  const handleLogout = useLogout(onLogout)

  return (
    <>
      <nav className={`${styles.nav} ${styles.desktopNav}`}>
        {user && <span className={styles.userName}>Olá, {user.name.split(" ")[0]} 👋</span>}
        <Link href="/" className={`${styles.btn} ${pathname === "/" ? styles.btnActive : ""}`}>
          <Home size={14} />
          <span className={styles.navText}>Home</span>
        </Link>
        <button onClick={handleLogout} className={styles.btn}>
          <LogOut size={14} />
          <span className={styles.navText}>Sair</span>
        </button>
      </nav>
      <MobileMenu>
        <Link href="/" className={`${styles.mobileMenuLink} ${pathname === "/" ? styles.mobileMenuLinkActive : ""}`}>
          <Home size={18} />
          Home
        </Link>
        <button onClick={handleLogout} className={`${styles.mobileMenuLink} ${styles.mobileMenuLinkLeft}`}>
          <LogOut size={18} />
          Sair
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
