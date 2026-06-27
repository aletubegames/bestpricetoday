"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API, apiFetch } from "@/lib/api"
import { isTokenExpired } from "@/lib/utils"

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
const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid rgba(108,92,231,0.2)",
  borderRadius: 14,
  padding: "20px 24px",
}

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
      style={{ padding: "4px 12px", borderRadius: 8, border: `1px solid ${accent}`, background: "transparent", color: accent, cursor: "pointer", fontSize: 12 }}
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
    <div style={{ minHeight: "100vh", background: "#f0f4ff", fontFamily: "system-ui, sans-serif", padding: "0 0 60px" }}>
      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid rgba(108,92,231,0.15)", padding: "18px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 24, fontWeight: 700, color: "#1a1a2e" }}>💰 Afiliados</span>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => router.push("/")} style={{ padding: "7px 16px", borderRadius: 8, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}>← Home</button>
            <button onClick={() => router.push("/dashboard")} style={{ padding: "7px 16px", borderRadius: 8, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}>📊 Dashboard</button>
          </div>
        </div>
        <p style={{ margin: 0, color: muted, fontSize: 14 }}>Produtos afiliados por plataforma</p>
        <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
          {(["mercadolivre", "shopee", "aliexpress", "lomadee"] as const).map(p => (
            <button
              key={p}
              onClick={() => setProvider(p)}
              style={{
                padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 14,
                background: provider === p ? accent : "#fff",
                color: provider === p ? "#fff" : muted,
                border: `1px solid ${provider === p ? accent : "#ddd"}`,
              }}
            >
              {p === "mercadolivre" ? "🟡 Mercado Livre" : p === "shopee" ? "🟠 Shopee" : p === "aliexpress" ? "🔴 AliExpress" : "🟣 Lomadee"}
            </button>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 24px" }}>
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
    return <div style={{ textAlign: "center", padding: 40 }}>Carregando...</div>
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Search Input */}
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <input
          type="text"
          placeholder="Buscar produto específico (ex: iphone x)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSearch() }}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #ddd",
            fontSize: 14,
            width: 300,
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: "8px 16px",
            borderRadius: 8,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          Buscar
        </button>
        <button
          onClick={handleClear}
          style={{
            padding: "8px 16px",
            borderRadius: 8,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          Limpar
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 14, color: muted }}>Produtos por página:</span>
        {[20, 40, 60, 80, 100].map(p => (
          <button
            key={p}
            onClick={() => { setPerPage(p); setPage(1) }}
            style={{
              padding: "6px 12px", borderRadius: 6, border: "1px solid #ddd", background: perPage === p ? accent : "#fff",
              color: perPage === p ? "#fff" : muted, cursor: "pointer", fontSize: 13,
            }}
          >
            {p}
          </button>
        ))}
        <span style={{ fontSize: 14, color: muted, marginLeft: 20 }}>Ordenar por:</span>
        {[
          { value: "relevance", label: "Relevância" },
          { value: "price_asc", label: "Menor preço" },
          { value: "price_desc", label: "Maior preço" },
        ].map(s => (
          <button
            key={s.value}
            onClick={() => setSort(s.value as any)}
            style={{
              padding: "6px 12px", borderRadius: 6, border: "1px solid #ddd", background: sort === s.value ? accent : "#fff",
              color: sort === s.value ? "#fff" : muted, cursor: "pointer", fontSize: 13,
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Products Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {products.map((offer) => (
          <div key={offer.id} style={cardStyle}>
            <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
              {offer.image_url && (
                <img
                  src={offer.image_url}
                  alt={offer.title}
                  style={{ width: 80, height: 80, objectFit: "cover", borderRadius: 8 }}
                />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a2e", marginBottom: 4 }}>{offer.title}</div>
                <div style={{ fontSize: 12, color: muted, marginBottom: 4 }}>{offer.store || offer.provider}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: accent }}>{fmt(offer.final_price)}</div>
                {offer.original_price && offer.original_price > offer.final_price && (
                  <div style={{ fontSize: 12, color: "#e74c3c", textDecoration: "line-through" }}>{fmt(offer.original_price)}</div>
                )}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "space-between", alignItems: "center" }}>
              <CopyBtn text={offer.affiliate_url} />
              <a
                href={offer.affiliate_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid #ddd",
                  background: "#fff",
                  color: accent,
                  cursor: "pointer",
                  fontSize: 12,
                  textDecoration: "none",
                }}
              >
                Ver oferta
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #ddd",
              background: page === 1 ? "#f5f5f5" : "#fff",
              cursor: page === 1 ? "not-allowed" : "pointer",
              fontSize: 14,
            }}
          >
            ← Anterior
          </button>
          <span style={{ padding: "8px 16px", fontSize: 14, color: muted }}>
            Página {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #ddd",
              background: page === totalPages ? "#f5f5f5" : "#fff",
              cursor: page === totalPages ? "not-allowed" : "pointer",
              fontSize: 14,
            }}
          >
            Próxima →
          </button>
        </div>
      )}

      {/* Info */}
      <div style={{ textAlign: "center", fontSize: 13, color: muted, marginTop: 20 }}>
        Total: {total} produtos • Página {page} de {totalPages}
      </div>
    </div>
  )
}
