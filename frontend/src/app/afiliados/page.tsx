"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API, apiFetch } from "@/lib/api"
import { isTokenExpired } from "@/lib/utils"
import styles from "./page.module.css"

interface Offer {
  id: string
  title: string
  affiliate_url: string
  final_price: number
  original_price: number | null
  provider: string
  image_url: string | null
  store: string | null
  discount_pct: number | null
}

const accent = "#7c6aff"
const muted = "#6b6b8a"

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

function buildAdminHeaders(token?: string | null): Record<string, string> {
  const storedAdminKey = typeof window !== "undefined" ? localStorage.getItem("admin_key") : null
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = `Bearer ${token}`
  if (storedAdminKey) headers["X-Admin-Key"] = storedAdminKey
  return headers
}

// ─── Copy Button ──────────────────────────────────────────────────────────────
function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className={styles.copyBtn}
    >
      {copied ? "✅" : "📋 Copiar"}
    </button>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function AfiliadosPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [provider, setProvider] = useState<"mercadolivre" | "shopee" | "aliexpress" | "lomadee">("mercadolivre")

  // Auth
  useEffect(() => {
    const user = localStorage.getItem("bpt_user")
    const tk = localStorage.getItem("bpt_token")
    if (!user) { router.push("/login"); return }
    try {
      const u = JSON.parse(user)
      if (!u?.is_admin) { router.push("/"); return }
    } catch { router.push("/login"); return }

    if (tk && isTokenExpired(tk)) {
      localStorage.removeItem("bpt_token")
      localStorage.removeItem("bpt_user")
      router.push("/login")
      return
    }

    setToken(tk)

    const storedKey = localStorage.getItem("admin_key")
    if (!storedKey && tk) {
      apiFetch(`${API}/api/v1/admin/auth/session-key`, {
        method: "POST",
        headers: { Authorization: `Bearer ${tk}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data?.admin_key) {
            localStorage.setItem("admin_key", data.admin_key)
          }
        })
        .catch(() => {})
    }
  }, [router])

  if (!token) return null

  return (
    <div className={styles.root}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className={styles.headerTitle}>💰 Afiliados</span>
          </div>
          <div className={styles.headerActions}>
            <button onClick={() => router.push("/")} className={styles.headerBtn}>← Home</button>
            <button onClick={() => router.push("/dashboard")} className={styles.headerBtn}>📊 Dashboard</button>
          </div>
        </div>
        <p className={styles.headerSubtitle}>Produtos afiliados por plataforma</p>
        <div className={styles.providerTabs}>
          {(["mercadolivre", "shopee", "aliexpress", "lomadee"] as const).map(p => (
            <button
              key={p}
              onClick={() => setProvider(p)}
              className={`${styles.providerTab} ${provider === p ? styles.providerTabActive : ""}`}
            >
              {p === "mercadolivre" ? "🟡 Mercado Livre" : p === "shopee" ? "🟠 Shopee" : p === "aliexpress" ? "🔴 AliExpress" : "🟣 Lomadee"}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.container}>
        <ProductsTab token={token} provider={provider} />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ABA PRODUTOS
// ═══════════════════════════════════════════════════════════════════════════════
function ProductsTab({ token, provider }: { token: string; provider: "mercadolivre" | "shopee" | "aliexpress" | "lomadee" }) {
  const [products, setProducts] = useState<Offer[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [sort, setSort] = useState<"relevance" | "price_asc" | "price_desc">("relevance")
  const [searchQuery, setSearchQuery] = useState("")
  const [submittedQuery, setSubmittedQuery] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const searchParam = submittedQuery ? `&search=${encodeURIComponent(submittedQuery)}` : ""
      const r = await apiFetch(`${API}/api/v1/affiliate/products?provider=${provider}&page=${page}&per_page=${perPage}&sort=${sort}${searchParam}`, { headers: buildAdminHeaders(token) })
      const d = await r.json()
      setProducts(d.offers ?? [])
      setTotal(d.total ?? 0)
      setTotalPages(d.total_pages ?? 0)
    } finally {
      setLoading(false)
    }
  }, [token, provider, page, perPage, sort, submittedQuery])

  const handleSearch = () => {
    setSubmittedQuery(searchQuery)
    setPage(1)
  }

  const handleClear = () => {
    setSearchQuery("")
    setSubmittedQuery("")
    setPage(1)
  }

  // Busca quando provider, page, perPage, sort ou submittedQuery mudam
  useEffect(() => { load() }, [load])

  if (loading) {
    return <div className={styles.loading}>Carregando...</div>
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Search Input */}
      <div className={styles.searchRow}>
        <input
          type="text"
          placeholder="Buscar produto específico (ex: iphone x)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSearch() }}
          className={styles.searchInput}
        />
        <button onClick={handleSearch} className={styles.searchBtn}>Buscar</button>
        <button onClick={handleClear} className={styles.searchBtn}>Limpar</button>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <span className={styles.filterLabel}>Produtos por página:</span>
        {[20, 40, 60, 80, 100].map(p => (
          <button
            key={p}
            onClick={() => { setPerPage(p); setPage(1) }}
            className={`${styles.filterBtn} ${perPage === p ? styles.filterBtnActive : ""}`}
          >
            {p}
          </button>
        ))}
        <span className={styles.filterLabel} style={{ marginLeft: 20 }}>Ordenar por:</span>
        {[
          { value: "relevance", label: "Relevância" },
          { value: "price_asc", label: "Menor preço" },
          { value: "price_desc", label: "Maior preço" },
        ].map(s => (
          <button
            key={s.value}
            onClick={() => setSort(s.value as any)}
            className={`${styles.filterBtn} ${sort === s.value ? styles.filterBtnActive : ""}`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Products Grid */}
      <div className={`cq ${styles.grid}`}>
        {products.map((offer) => (
          <div key={offer.id} className={styles.card}>
            <div className={styles.cardTop}>
              {offer.image_url && (
                <img
                  src={offer.image_url}
                  alt={offer.title}
                  className={styles.cardImg}
                />
              )}
              <div className={styles.cardInfo}>
                <div className={styles.cardTitle}>{offer.title}</div>
                <div className={styles.cardStore}>{offer.store || offer.provider}</div>
                <div className={styles.cardPrice}>{fmt(offer.final_price)}</div>
                {offer.original_price && offer.original_price > offer.final_price && (
                  <div className={styles.cardOriginalPrice}>{fmt(offer.original_price)}</div>
                )}
              </div>
            </div>
            <div className={styles.cardActions}>
              <CopyBtn text={offer.affiliate_url} />
              <a
                href={offer.affiliate_url}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className={styles.cardLink}
              >
                Ver oferta
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className={`${styles.pageBtn} ${page === 1 ? styles.pageBtnDisabled : ""}`}
          >
            ← Anterior
          </button>
          <span className={styles.pageInfo}>
            Página {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className={`${styles.pageBtn} ${page === totalPages ? styles.pageBtnDisabled : ""}`}
          >
            Próxima →
          </button>
        </div>
      )}

      {/* Info */}
      <div className={styles.info}>
        Total: {total} produtos • Página {page} de {totalPages}
      </div>
    </div>
  )
}
