"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API } from "@/lib/api"

interface Product {
  id: string
  ml_code: string | null
  affiliate_url: string
  title: string | null
  price: number
  commission_pct: number
  commission_value: number
  estimate_10d: number
  estimate_month: number
  category: string | null
  image_url: string | null
  notes: string | null
  is_active: boolean
  created_at: string
}

const accent = "#7c6aff"
const green = "#00e5a0"
const yellow = "#fbbf24"
const muted = "#6b6b8a"
const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid rgba(108,92,231,0.2)",
  borderRadius: 14,
  padding: 20,
}
const btnPrimary: React.CSSProperties = {
  background: "linear-gradient(135deg,#7c6aff,#a78bfa)",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  cursor: "pointer",
  fontWeight: 700,
  fontSize: 13,
}
const btnSecondary: React.CSSProperties = {
  background: "rgba(108,92,231,0.08)",
  color: accent,
  border: "1px solid rgba(108,92,231,0.2)",
  borderRadius: 8,
  padding: "8px 16px",
  cursor: "pointer",
  fontWeight: 600,
  fontSize: 13,
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      style={{ ...btnSecondary, padding: "4px 10px", fontSize: 12 }}
    >
      {copied ? "✅" : "📋 Copiar"}
    </button>
  )
}

export default function AfiliadosPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [tab, setTab] = useState<"produtos" | "conteudo" | "links">("produtos")

  // Products state
  const [products, setProducts] = useState<Product[]>([])
  const [loadingProducts, setLoadingProducts] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [addForm, setAddForm] = useState({ ml_code: "", affiliate_url: "", title: "", price: "", commission_pct: "", category: "" })
  const [savingAdd, setSavingAdd] = useState(false)
  const [editingCell, setEditingCell] = useState<{ id: string; field: string; value: string } | null>(null)
  const [enrichModal, setEnrichModal] = useState<{ id: string; ml_code: string | null } | null>(null)
  const [enrichUrl, setEnrichUrl] = useState("")
  const [enriching, setEnriching] = useState(false)

  // Content gen state
  const [selectedProduct, setSelectedProduct] = useState<string>("")
  const [generatingType, setGeneratingType] = useState<string | null>(null)
  const [genResult, setGenResult] = useState<{ type: string; data: unknown } | null>(null)

  // Short links state
  const [slProduct, setSlProduct] = useState<string>("")
  const [slCampaign, setSlCampaign] = useState("")
  const [generatingLink, setGeneratingLink] = useState(false)
  const [shortLinks, setShortLinks] = useState<Array<{ product: string; campaign: string; url: string }>>([])

  useEffect(() => {
    const raw = localStorage.getItem("bpt_user")
    if (!raw) { router.push("/login"); return }
    let user: { name: string; is_admin: boolean }
    try { user = JSON.parse(raw) } catch { router.push("/login"); return }
    if (!user.is_admin) { router.push("/"); return }
    const t = localStorage.getItem("bpt_token")
    if (!t) { router.push("/login"); return }
    setToken(t)
  }, [router])

  useEffect(() => {
    if (token) fetchProducts()
  }, [token])

  async function fetchProducts() {
    setLoadingProducts(true)
    try {
      const res = await fetch(`${API}/api/v1/affiliate/products`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setProducts(data.products || [])
      }
    } finally {
      setLoadingProducts(false)
    }
  }

  async function handleAddProduct() {
    setSavingAdd(true)
    try {
      const body: Record<string, unknown> = {
        affiliate_url: addForm.affiliate_url,
      }
      if (addForm.ml_code) body.ml_code = addForm.ml_code
      if (addForm.title) body.title = addForm.title
      if (addForm.price) body.price = parseFloat(addForm.price)
      if (addForm.commission_pct) body.commission_pct = parseFloat(addForm.commission_pct)
      if (addForm.category) body.category = addForm.category

      const res = await fetch(`${API}/api/v1/affiliate/products`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        setShowAddForm(false)
        setAddForm({ ml_code: "", affiliate_url: "", title: "", price: "", commission_pct: "", category: "" })
        fetchProducts()
      }
    } finally {
      setSavingAdd(false)
    }
  }

  async function handlePatch(id: string, field: string, value: string) {
    const body: Record<string, unknown> = {}
    if (field === "price" || field === "commission_pct") body[field] = parseFloat(value)
    else body[field] = value
    await fetch(`${API}/api/v1/affiliate/products/${id}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    fetchProducts()
  }

  async function handleDelete(id: string) {
    if (!confirm("Remover produto?")) return
    await fetch(`${API}/api/v1/affiliate/products/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    fetchProducts()
  }

  async function handleEnrichUrl() {
    if (!enrichModal || !enrichUrl.trim()) return
    setEnriching(true)
    try {
      const r = await fetch(`${API}/api/v1/affiliate/products/enrich-url`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: enrichModal.id, ml_url: enrichUrl.trim() }),
      })
      const d = await r.json()
      if (r.ok) {
        setEnrichModal(null)
        setEnrichUrl("")
        fetchProducts()
      } else {
        alert(`❌ ${d.detail || "Erro ao preencher"}`)
      }
    } finally {
      setEnriching(false)
    }
  }

  async function handleGenerate(type: "marketplace" | "tiktok" | "youtube") {
    if (!selectedProduct) return
    setGeneratingType(type)
    setGenResult(null)
    try {
      const res = await fetch(`${API}/api/v1/affiliate/generate/${type}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: selectedProduct }),
      })
      if (res.ok) {
        const data = await res.json()
        setGenResult({ type, data })
      }
    } finally {
      setGeneratingType(null)
    }
  }

  async function handleShortLink() {
    if (!slProduct) return
    setGeneratingLink(true)
    try {
      const body: Record<string, unknown> = { product_id: slProduct, source: "admin" }
      if (slCampaign) body.campaign = slCampaign
      const res = await fetch(`${API}/api/v1/affiliate/shortlink`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        const prod = products.find(p => p.id === slProduct)
        setShortLinks(prev => [
          { product: prod?.title || prod?.ml_code || slProduct, campaign: slCampaign, url: data.short_url },
          ...prev,
        ])
      }
    } finally {
      setGeneratingLink(false)
    }
  }

  if (!token) return null

  const totalProducts = products.length
  const avgCommission = products.length ? (products.reduce((a, p) => a + p.commission_pct, 0) / products.length).toFixed(1) : "0"
  const totalMonthly = products.reduce((a, p) => a + (p.estimate_month || 0), 0)

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", fontFamily: "system-ui, sans-serif", padding: "24px 16px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>

        {/* Modal Enrich URL */}
        {enrichModal && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
            <div style={{ background: "#fff", borderRadius: 16, padding: 28, maxWidth: 520, width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,0.3)" }}>
              <h3 style={{ margin: "0 0 8px", color: "#1a1a2e", fontSize: 18 }}>Preencher dados do produto</h3>
              <p style={{ margin: "0 0 20px", color: "#6b6b8a", fontSize: 13 }}>
                1. Clique no link <strong>{enrichModal.ml_code}</strong> que abriu em nova aba<br/>
                2. Navegue até o produto específico<br/>
                3. Copie a URL do browser (ex: <code style={{fontSize:11}}>mercadolivre.com.br/MLB-1234567...</code>)<br/>
                4. Cole aqui:
              </p>
              <input
                type="url"
                placeholder="https://www.mercadolivre.com.br/MLB-XXXXXXX-nome-produto..."
                value={enrichUrl}
                onChange={e => setEnrichUrl(e.target.value)}
                style={{ width: "100%", boxSizing: "border-box", padding: "12px 14px", borderRadius: 8, border: "1px solid rgba(108,92,231,0.3)", fontSize: 13, marginBottom: 16, outline: "none" }}
                onKeyDown={e => e.key === "Enter" && handleEnrichUrl()}
                autoFocus
              />
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={handleEnrichUrl} disabled={enriching || !enrichUrl.trim()} style={{ ...btnPrimary, opacity: enriching || !enrichUrl.trim() ? 0.6 : 1 }}>
                  {enriching ? "Preenchendo..." : "✨ Preencher"}
                </button>
                <button onClick={() => { setEnrichModal(null); setEnrichUrl("") }} style={btnSecondary}>
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "#1a1a2e" }}>💰 Afiliados ML</h1>
            <p style={{ margin: "4px 0 0", color: muted, fontSize: 14 }}>Produtos afiliados do Mercado Livre</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <a href="/" style={{ ...btnSecondary, textDecoration: "none", display: "flex", alignItems: "center" }}>← Home</a>
            <a href="/dashboard" style={{ ...btnSecondary, textDecoration: "none", display: "flex", alignItems: "center" }}>📊 Dashboard</a>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: "2px solid rgba(108,92,231,0.1)", paddingBottom: 0 }}>
          {([["produtos", "📦 Produtos"], ["conteudo", "✨ Gerar Conteúdo"], ["links", "🔗 Short Links"]] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              style={{
                background: tab === key ? accent : "transparent",
                color: tab === key ? "#fff" : muted,
                border: "none",
                borderRadius: "8px 8px 0 0",
                padding: "10px 18px",
                cursor: "pointer",
                fontWeight: tab === key ? 700 : 500,
                fontSize: 14,
                transition: "all 0.2s",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* TAB: Produtos */}
        {tab === "produtos" && (
          <div>
            {/* Stats */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 20 }}>
              {[
                { label: "Total de Produtos", value: totalProducts, color: accent },
                { label: "Comissão Média", value: `${avgCommission}%`, color: "#a78bfa" },
                { label: "Estimativa Mensal", value: `R$ ${totalMonthly.toFixed(2)}`, color: green },
              ].map(s => (
                <div key={s.label} style={{ ...cardStyle, textAlign: "center" }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 12, color: muted, marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Add button */}
            <div style={{ marginBottom: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button onClick={() => setShowAddForm(!showAddForm)} style={btnPrimary}>
                {showAddForm ? "✕ Cancelar" : "+ Adicionar Produto"}
              </button>
              <button
                onClick={async () => {
                  const token = localStorage.getItem("bpt_token")
                  const r = await fetch(`${API}/api/v1/affiliate/products/enrich`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` },
                  })
                  const d = await r.json()
                  if (r.ok) {
                    alert(`✅ Preenchidos: ${d.enriched} | Falhas: ${d.failed}`)
                    fetchProducts()
                  } else {
                    alert(`❌ ${d.detail || "Erro"}`)
                  }
                }}
                style={{ ...btnPrimary, background: "linear-gradient(135deg,#00e5a0,#00b880)", color: "#1a1a2e" }}
                title="Busca título/preço/imagem via API oficial ML para produtos sem título"
              >
                ✨ Preencher dados via ML
              </button>
            </div>

            {/* Add form */}
            {showAddForm && (
              <div style={{ ...cardStyle, marginBottom: 20 }}>
                <h3 style={{ margin: "0 0 16px", color: "#1a1a2e", fontSize: 16 }}>Novo Produto</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 12 }}>
                  {[
                    { key: "ml_code", label: "Código ML (ex: S5L99N-Y7WN)", placeholder: "S5L99N-Y7WN" },
                    { key: "affiliate_url", label: "URL de Afiliado *", placeholder: "https://..." },
                    { key: "title", label: "Título", placeholder: "Nome do produto" },
                    { key: "price", label: "Preço (R$)", placeholder: "99.90", type: "number" },
                    { key: "commission_pct", label: "Comissão (%)", placeholder: "12.5", type: "number" },
                    { key: "category", label: "Categoria", placeholder: "Eletrônicos" },
                  ].map(f => (
                    <div key={f.key}>
                      <label style={{ fontSize: 12, color: muted, display: "block", marginBottom: 4 }}>{f.label}</label>
                      <input
                        type={f.type || "text"}
                        placeholder={f.placeholder}
                        value={addForm[f.key as keyof typeof addForm]}
                        onChange={e => setAddForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                        style={{ width: "100%", padding: "8px 10px", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, fontSize: 13, outline: "none", boxSizing: "border-box" }}
                      />
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                  <button onClick={handleAddProduct} disabled={savingAdd || !addForm.affiliate_url} style={btnPrimary}>
                    {savingAdd ? "Salvando..." : "💾 Salvar"}
                  </button>
                  <button onClick={() => setShowAddForm(false)} style={btnSecondary}>Cancelar</button>
                </div>
              </div>
            )}

            {/* Products table */}
            <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
              {loadingProducts ? (
                <div style={{ padding: 32, textAlign: "center", color: muted }}>Carregando produtos...</div>
              ) : products.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: muted }}>Nenhum produto cadastrado</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "rgba(108,92,231,0.05)" }}>
                        {["Código ML", "Título", "Preço", "Comissão %", "Ganho/venda", "Est. mensal", "Ações"].map(h => (
                          <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontWeight: 700, color: muted, fontSize: 12, whiteSpace: "nowrap" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {products.map(p => (
                        <tr key={p.id} style={{ borderBottom: "1px solid rgba(108,92,231,0.08)" }}>
                          <td style={{ padding: "12px 16px", color: muted, fontFamily: "monospace", fontSize: 12 }}>
                            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                              <a href={p.affiliate_url} target="_blank" rel="noopener noreferrer"
                                style={{ color: "#7c6aff", textDecoration: "none", fontWeight: 600 }}
                                title="Abrir produto no ML">
                                {p.ml_code || "link"} ↗
                              </a>
                              {!p.title && (
                                <button
                                  onClick={() => { setEnrichModal({ id: p.id, ml_code: p.ml_code }); setEnrichUrl("") }}
                                  style={{ background: "rgba(0,229,160,0.15)", border: "1px solid rgba(0,229,160,0.4)", borderRadius: 6, padding: "2px 8px", fontSize: 11, color: "#00b880", cursor: "pointer", fontWeight: 600 }}
                                  title="Preencher dados via URL do produto">
                                  + URL produto
                                </button>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: "12px 16px", minWidth: 160 }}>
                            {editingCell?.id === p.id && editingCell.field === "title" ? (
                              <input
                                autoFocus
                                value={editingCell.value}
                                onChange={e => setEditingCell(prev => prev ? { ...prev, value: e.target.value } : null)}
                                onBlur={() => { if (editingCell) handlePatch(p.id, "title", editingCell.value); setEditingCell(null) }}
                                onKeyDown={e => { if (e.key === "Enter" && editingCell) { handlePatch(p.id, "title", editingCell.value); setEditingCell(null) } if (e.key === "Escape") setEditingCell(null) }}
                                style={{ width: "100%", border: `1px solid ${accent}`, borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
                              />
                            ) : (
                              <span
                                onClick={() => setEditingCell({ id: p.id, field: "title", value: p.title || "" })}
                                style={{ cursor: "text", color: p.title ? "#1a1a2e" : muted, fontStyle: p.title ? "normal" : "italic" }}
                                title="Clique para editar"
                              >
                                {p.title || p.ml_code || "sem título"}
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "12px 16px" }}>
                            {editingCell?.id === p.id && editingCell.field === "price" ? (
                              <input
                                autoFocus
                                type="number"
                                value={editingCell.value}
                                onChange={e => setEditingCell(prev => prev ? { ...prev, value: e.target.value } : null)}
                                onBlur={() => { if (editingCell) handlePatch(p.id, "price", editingCell.value); setEditingCell(null) }}
                                onKeyDown={e => { if (e.key === "Enter" && editingCell) { handlePatch(p.id, "price", editingCell.value); setEditingCell(null) } if (e.key === "Escape") setEditingCell(null) }}
                                style={{ width: 90, border: `1px solid ${accent}`, borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
                              />
                            ) : (
                              <span onClick={() => setEditingCell({ id: p.id, field: "price", value: String(p.price) })} style={{ cursor: "text" }} title="Clique para editar">
                                R$ {p.price?.toFixed(2) || "0.00"}
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "12px 16px" }}>
                            {editingCell?.id === p.id && editingCell.field === "commission_pct" ? (
                              <input
                                autoFocus
                                type="number"
                                value={editingCell.value}
                                onChange={e => setEditingCell(prev => prev ? { ...prev, value: e.target.value } : null)}
                                onBlur={() => { if (editingCell) handlePatch(p.id, "commission_pct", editingCell.value); setEditingCell(null) }}
                                onKeyDown={e => { if (e.key === "Enter" && editingCell) { handlePatch(p.id, "commission_pct", editingCell.value); setEditingCell(null) } if (e.key === "Escape") setEditingCell(null) }}
                                style={{ width: 80, border: `1px solid ${accent}`, borderRadius: 6, padding: "4px 8px", fontSize: 13 }}
                              />
                            ) : (
                              <span onClick={() => setEditingCell({ id: p.id, field: "commission_pct", value: String(p.commission_pct) })} style={{ cursor: "text" }} title="Clique para editar">
                                {p.commission_pct?.toFixed(1)}%
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "12px 16px", color: green, fontWeight: 700 }}>
                            R$ {((p.price || 0) * (p.commission_pct || 0) / 100).toFixed(2)}
                          </td>
                          <td style={{ padding: "12px 16px" }}>
                            <span style={{ background: "rgba(0,229,160,0.1)", color: green, fontWeight: 700, padding: "3px 8px", borderRadius: 6, fontSize: 12 }}>
                              R$ {(p.estimate_month || 0).toFixed(2)}
                            </span>
                          </td>
                          <td style={{ padding: "12px 16px" }}>
                            <button onClick={() => handleDelete(p.id)} style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, padding: "5px 10px", cursor: "pointer", fontSize: 13 }}>
                              🗑️
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB: Gerar Conteúdo */}
        {tab === "conteudo" && (
          <div>
            <div style={{ ...cardStyle, marginBottom: 20 }}>
              <label style={{ fontSize: 13, color: muted, display: "block", marginBottom: 8 }}>Selecionar produto</label>
              <select
                value={selectedProduct}
                onChange={e => { setSelectedProduct(e.target.value); setGenResult(null) }}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, fontSize: 14, marginBottom: 16, outline: "none" }}
              >
                <option value="">— Escolha um produto —</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>{p.title || p.ml_code || p.id}</option>
                ))}
              </select>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {([["marketplace", "📢 Marketplace"], ["tiktok", "🎵 TikTok"], ["youtube", "📺 YouTube"]] as const).map(([type, label]) => (
                  <button
                    key={type}
                    onClick={() => handleGenerate(type)}
                    disabled={!selectedProduct || generatingType !== null}
                    style={{ ...btnPrimary, opacity: !selectedProduct ? 0.5 : 1 }}
                  >
                    {generatingType === type ? "Gerando..." : label}
                  </button>
                ))}
              </div>
            </div>

            {/* Results */}
            {genResult && genResult.type === "marketplace" && (
              <MarketplaceResult data={genResult.data as Record<string, unknown>} />
            )}
            {genResult && genResult.type === "tiktok" && (
              <TikTokResult data={genResult.data as Record<string, unknown>} />
            )}
            {genResult && genResult.type === "youtube" && (
              <YouTubeResult data={genResult.data as Record<string, unknown>} />
            )}
          </div>
        )}

        {/* TAB: Short Links */}
        {tab === "links" && (
          <div>
            <div style={{ ...cardStyle, marginBottom: 20 }}>
              <label style={{ fontSize: 13, color: muted, display: "block", marginBottom: 8 }}>Selecionar produto</label>
              <select
                value={slProduct}
                onChange={e => setSlProduct(e.target.value)}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, fontSize: 14, marginBottom: 12, outline: "none" }}
              >
                <option value="">— Escolha um produto —</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>{p.title || p.ml_code || p.id}</option>
                ))}
              </select>

              <label style={{ fontSize: 13, color: muted, display: "block", marginBottom: 8 }}>Campaign (opcional)</label>
              <input
                type="text"
                placeholder="ex: tiktok_jan26"
                value={slCampaign}
                onChange={e => setSlCampaign(e.target.value)}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 8, fontSize: 14, marginBottom: 16, outline: "none", boxSizing: "border-box" }}
              />

              <button onClick={handleShortLink} disabled={!slProduct || generatingLink} style={{ ...btnPrimary, opacity: !slProduct ? 0.5 : 1 }}>
                {generatingLink ? "Gerando..." : "🔗 Gerar Short Link"}
              </button>
            </div>

            {shortLinks.length > 0 && (
              <div>
                <h3 style={{ margin: "0 0 12px", color: "#1a1a2e", fontSize: 15 }}>Links gerados nesta sessão</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {shortLinks.map((sl, i) => (
                    <div key={i} style={{ ...cardStyle, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, padding: "14px 18px" }}>
                      <div>
                        <div style={{ fontWeight: 700, color: "#1a1a2e", fontSize: 14 }}>{sl.product}</div>
                        {sl.campaign && <div style={{ fontSize: 12, color: muted }}>Campaign: {sl.campaign}</div>}
                        <a href={sl.url} target="_blank" rel="noopener noreferrer" style={{ color: accent, fontSize: 14, fontWeight: 600, wordBreak: "break-all" }}>{sl.url}</a>
                      </div>
                      <CopyBtn text={sl.url} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function MarketplaceResult({ data }: { data: Record<string, unknown> }) {
  const d = data as Record<string, string>
  const tags = Array.isArray(data.tags_busca) ? data.tags_busca as string[] : []
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: "0 0 4px", color: "#1a1a2e" }}>📢 Resultado Marketplace</h3>
      {d.titulo && (
        <ResultCard label="Título">
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
            <span style={{ fontWeight: 600 }}>{d.titulo}</span>
            <CopyBtn text={d.titulo} />
          </div>
        </ResultCard>
      )}
      {d.descricao && (
        <ResultCard label="Descrição">
          <textarea readOnly value={d.descricao} rows={5} style={{ width: "100%", border: "none", resize: "vertical", fontSize: 13, color: "#1a1a2e", background: "transparent", outline: "none", boxSizing: "border-box" }} />
          <CopyBtn text={d.descricao} />
        </ResultCard>
      )}
      {tags.length > 0 && (
        <ResultCard label="Tags de Busca">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {tags.map((t, i) => (
              <span key={i} style={{ background: "rgba(108,92,231,0.1)", color: "#7c6aff", padding: "3px 10px", borderRadius: 20, fontSize: 12 }}>{t}</span>
            ))}
          </div>
          <CopyBtn text={tags.join(", ")} />
        </ResultCard>
      )}
      {d.sku && (
        <ResultCard label="SKU">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <code style={{ background: "rgba(108,92,231,0.08)", padding: "4px 10px", borderRadius: 6, fontSize: 14, fontWeight: 700, color: "#7c6aff" }}>{d.sku}</code>
            <CopyBtn text={d.sku} />
          </div>
        </ResultCard>
      )}
      {d.texto_x1 && (
        <ResultCard label="Texto para enviar no chat">
          <textarea readOnly value={d.texto_x1} rows={4} style={{ width: "100%", border: "none", resize: "vertical", fontSize: 13, color: "#1a1a2e", background: "transparent", outline: "none", boxSizing: "border-box" }} />
          <CopyBtn text={d.texto_x1} />
        </ResultCard>
      )}
    </div>
  )
}

const segmentColors: Record<string, string> = {
  gancho: "#7c6aff", problema: "#ef4444", solucao: "#00e5a0", prova: "#fbbf24", cta: "#f97316"
}

function TikTokResult({ data }: { data: Record<string, unknown> }) {
  const d = data as Record<string, string>
  const hashtags = Array.isArray(data.hashtags) ? data.hashtags as string[] : []
  const segments = Array.isArray(data.roteiro) ? data.roteiro as Array<Record<string, unknown>> : []
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: "0 0 4px", color: "#1a1a2e" }}>🎵 Resultado TikTok</h3>
      {segments.length > 0 && (
        <ResultCard label="Roteiro">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {segments.map((seg, i) => {
              const tipo = String(seg.tipo || seg.parte || "segmento").toLowerCase()
              const cor = segmentColors[tipo] || "#7c6aff"
              return (
                <div key={i} style={{ borderLeft: `4px solid ${cor}`, paddingLeft: 12, paddingTop: 4, paddingBottom: 4 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: cor, textTransform: "uppercase", marginBottom: 2 }}>
                    {String(seg.tipo || seg.parte || `Segmento ${i + 1}`)} {seg.tempo ? `· ${seg.tempo}` : ""}
                  </div>
                  <div style={{ fontSize: 13, color: "#1a1a2e" }}>{String(seg.texto || seg.conteudo || "")}</div>
                </div>
              )
            })}
          </div>
        </ResultCard>
      )}
      {d.legenda && (
        <ResultCard label="Legenda">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
            <span style={{ fontSize: 13 }}>{d.legenda}</span>
            <CopyBtn text={d.legenda} />
          </div>
        </ResultCard>
      )}
      {hashtags.length > 0 && (
        <ResultCard label="Hashtags">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {hashtags.map((h, i) => (
              <span key={i} style={{ background: "rgba(0,229,160,0.1)", color: "#00b880", padding: "3px 10px", borderRadius: 20, fontSize: 12 }}>{h}</span>
            ))}
          </div>
          <CopyBtn text={hashtags.join(" ")} />
        </ResultCard>
      )}
      {d.musica_sugerida && (
        <ResultCard label="🎵 Música Sugerida">
          <span style={{ fontWeight: 600, color: "#7c6aff" }}>{d.musica_sugerida}</span>
        </ResultCard>
      )}
      {d.dica_visual && (
        <div style={{ background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.3)", borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#d97706", marginBottom: 4 }}>💡 DICA VISUAL</div>
          <div style={{ fontSize: 13, color: "#1a1a2e" }}>{d.dica_visual}</div>
        </div>
      )}
    </div>
  )
}

function YouTubeResult({ data }: { data: Record<string, unknown> }) {
  const d = data as Record<string, string>
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggle = (k: string) => setExpanded(p => ({ ...p, [k]: !p[k] }))
  const roteiro = Array.isArray(data.roteiro) ? data.roteiro as Array<Record<string, unknown>> : []
  const timestamps = Array.isArray(data.timestamps) ? data.timestamps as string[] : []
  const tags = Array.isArray(data.tags) ? data.tags as string[] : []

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: "0 0 4px", color: "#1a1a2e" }}>📺 Resultado YouTube</h3>
      {d.titulo && (
        <ResultCard label="Título">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
            <span style={{ fontWeight: 600, fontSize: 15 }}>{d.titulo}</span>
            <CopyBtn text={d.titulo} />
          </div>
        </ResultCard>
      )}
      {roteiro.length > 0 && (
        <ResultCard label="Roteiro">
          <button onClick={() => toggle("roteiro")} style={{ ...btnSecondary, marginBottom: 10 }}>
            {expanded.roteiro ? "▲ Recolher" : "▼ Expandir roteiro"}
          </button>
          {expanded.roteiro && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {roteiro.map((parte, i) => (
                <div key={i} style={{ ...cardStyle, background: "rgba(108,92,231,0.03)", padding: 14 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#7c6aff", textTransform: "uppercase", marginBottom: 4 }}>
                    {String(parte.parte || parte.tipo || `Parte ${i + 1}`)} {parte.tempo ? `· ${parte.tempo}` : ""}
                  </div>
                  <div style={{ fontSize: 13, color: "#1a1a2e" }}>{String(parte.texto || parte.conteudo || "")}</div>
                </div>
              ))}
            </div>
          )}
        </ResultCard>
      )}
      {d.descricao && (
        <ResultCard label="Descrição do Vídeo">
          <button onClick={() => toggle("descricao")} style={{ ...btnSecondary, marginBottom: 10 }}>
            {expanded.descricao ? "▲ Recolher" : "▼ Ver descrição"}
          </button>
          {expanded.descricao && (
            <>
              <textarea readOnly value={d.descricao} rows={6} style={{ width: "100%", border: "1px solid rgba(108,92,231,0.15)", borderRadius: 8, resize: "vertical", fontSize: 13, padding: 10, outline: "none", boxSizing: "border-box", marginBottom: 8 }} />
              <CopyBtn text={d.descricao} />
            </>
          )}
        </ResultCard>
      )}
      {tags.length > 0 && (
        <ResultCard label="Tags">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {tags.map((t, i) => (
              <span key={i} style={{ background: "rgba(108,92,231,0.1)", color: "#7c6aff", padding: "3px 10px", borderRadius: 20, fontSize: 12 }}>{t}</span>
            ))}
          </div>
          <CopyBtn text={tags.join(", ")} />
        </ResultCard>
      )}
      {timestamps.length > 0 && (
        <ResultCard label="Timestamps">
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: "#1a1a2e", marginBottom: 8 }}>
            {timestamps.map((ts, i) => <li key={i}>{ts}</li>)}
          </ul>
          <CopyBtn text={timestamps.join("\n")} />
        </ResultCard>
      )}
      {d.thumbnail_texto && (
        <div style={{ background: "rgba(108,92,231,0.06)", border: "2px solid rgba(108,92,231,0.2)", borderRadius: 14, padding: 20, textAlign: "center" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: muted, marginBottom: 8 }}>🖼️ TEXTO DA THUMBNAIL</div>
          <div style={{ fontSize: 22, fontWeight: 900, color: "#1a1a2e" }}>{d.thumbnail_texto}</div>
        </div>
      )}
    </div>
  )
}

function ResultCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "#fff", border: "1px solid rgba(108,92,231,0.15)", borderRadius: 12, padding: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: muted, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 10 }}>{label}</div>
      {children}
    </div>
  )
}
