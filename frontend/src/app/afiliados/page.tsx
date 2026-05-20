"use client"

import { useEffect, useState, useCallback } from "react"
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

// ─── Inline Edit Cell ─────────────────────────────────────────────────────────
function InlineEdit({
  value,
  type = "text",
  onSave,
  render,
}: {
  value: string | number | null
  type?: string
  onSave: (v: string) => void
  render?: React.ReactNode
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value ?? ""))

  function save() {
    setEditing(false)
    onSave(draft)
  }

  if (!editing)
    return (
      <span
        onClick={() => { setDraft(String(value ?? "")); setEditing(true) }}
        style={{ cursor: "pointer", textDecoration: "underline dotted" }}
        title="Clique para editar"
      >
        {render ?? (value !== null && value !== "" ? String(value) : <span style={{ color: muted, fontStyle: "italic" }}>—</span>)}
      </span>
    )

  return (
    <input
      autoFocus
      type={type}
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={save}
      onKeyDown={e => e.key === "Enter" && save()}
      style={{ width: "90%", padding: "2px 6px", borderRadius: 6, border: `1px solid ${accent}` }}
    />
  )
}

// ─── Chips ────────────────────────────────────────────────────────────────────
function Chips({ items }: { items: string[] }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {items.map((t, i) => (
        <span key={i} style={{ background: "rgba(124,106,255,0.12)", color: accent, borderRadius: 20, padding: "2px 10px", fontSize: 12 }}>
          {t}
        </span>
      ))}
    </div>
  )
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
  const [tab, setTab] = useState<"products" | "content" | "shortlinks">("products")

  // Auth
  useEffect(() => {
    const user = localStorage.getItem("bpt_user")
    const tk = localStorage.getItem("bpt_token")
    if (!user) { router.push("/login"); return }
    try {
      const u = JSON.parse(user)
      if (!u?.is_admin) { router.push("/"); return }
    } catch { router.push("/login"); return }
    setToken(tk)
  }, [router])

  if (!token) return null

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", fontFamily: "system-ui, sans-serif", padding: "0 0 60px" }}>
      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid rgba(108,92,231,0.15)", padding: "18px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 24, fontWeight: 700, color: "#1a1a2e" }}>💰 Afiliados ML</span>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => router.push("/")} style={{ padding: "7px 16px", borderRadius: 8, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}>← Home</button>
            <button onClick={() => router.push("/dashboard")} style={{ padding: "7px 16px", borderRadius: 8, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}>📊 Dashboard</button>
          </div>
        </div>
        <p style={{ margin: 0, color: muted, fontSize: 14 }}>Produtos afiliados do Mercado Livre</p>
        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          {(["products", "content", "shortlinks"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 14,
                background: tab === t ? accent : "#fff",
                color: tab === t ? "#fff" : muted,
                border: `1px solid ${tab === t ? accent : "#ddd"}`,
              }}
            >
              {t === "products" ? "📦 Produtos" : t === "content" ? "✨ Gerar Conteúdo" : "🔗 Short Links"}
            </button>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 24px" }}>
        {tab === "products" && <ProductsTab token={token} />}
        {tab === "content" && <ContentTab token={token} />}
        {tab === "shortlinks" && <ShortLinksTab token={token} />}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ABA PRODUTOS
// ═══════════════════════════════════════════════════════════════════════════════
function ProductsTab({ token }: { token: string }) {
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)

  // Form state
  const emptyForm = { ml_code: "", affiliate_url: "", title: "", price: "", commission_pct: "", category: "", image_url: "", notes: "" }
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const headers = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/v1/affiliate/products`, { headers: { "Authorization": `Bearer ${token}` } })
      const d = await r.json()
      setProducts(d.products ?? [])
      setTotal(d.total ?? 0)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  async function createProduct() {
    if (!form.affiliate_url) return alert("Link de Afiliado é obrigatório")
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        affiliate_url: form.affiliate_url,
        ml_code: form.ml_code || null,
        title: form.title || null,
        price: form.price ? parseFloat(form.price) : 0,
        commission_pct: form.commission_pct ? parseFloat(form.commission_pct) : 0,
        category: form.category || null,
        image_url: form.image_url || null,
        notes: form.notes || null,
      }
      const r = await fetch(`${API}/api/v1/affiliate/products`, { method: "POST", headers, body: JSON.stringify(body) })
      if (!r.ok) throw new Error(await r.text())
      setForm(emptyForm)
      setShowForm(false)
      await load()
    } catch (e) {
      alert("Erro ao criar: " + e)
    } finally {
      setSaving(false)
    }
  }

  async function patchProduct(id: string, data: Record<string, unknown>) {
    await fetch(`${API}/api/v1/affiliate/products/${id}`, { method: "PATCH", headers, body: JSON.stringify(data) })
    setProducts(prev => prev.map(p => p.id === id ? { ...p, ...data } : p))
  }

  async function deleteProduct(id: string) {
    if (!confirm("Remover produto?")) return
    await fetch(`${API}/api/v1/affiliate/products/${id}`, { method: "DELETE", headers })
    await load()
  }

  // Stats
  const avgComm = products.length ? (products.reduce((a, p) => a + p.commission_pct, 0) / products.length) : 0
  const totalMonth = products.reduce((a, p) => a + (p.estimate_month ?? 0), 0)

  // Pagination
  const totalPages = Math.ceil(products.length / perPage)
  const startIdx = (page - 1) * perPage
  const pageProducts = products.slice(startIdx, startIdx + perPage)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        {[
          { label: "Total de produtos", value: total },
          { label: "Comissão média", value: `${avgComm.toFixed(1)}%` },
          { label: "Estimativa mensal", value: fmt(totalMonth) },
        ].map(s => (
          <div key={s.label} style={cardStyle}>
            <div style={{ fontSize: 13, color: muted }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "#1a1a2e", marginTop: 4 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Add button */}
      <div>
        <button
          onClick={() => setShowForm(v => !v)}
          style={{ padding: "10px 22px", background: accent, color: "#fff", borderRadius: 10, border: "none", cursor: "pointer", fontWeight: 600 }}
        >
          {showForm ? "✕ Cancelar" : "+ Novo Produto"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 style={{ margin: 0, color: "#1a1a2e" }}>Novo Produto</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Código ML
              <input value={form.ml_code} onChange={e => setForm(f => ({ ...f, ml_code: e.target.value }))} placeholder="ex: S5L99N-Y7WN" style={inputStyle} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Link de Afiliado (obrigatório) *
              <input value={form.affiliate_url} onChange={e => setForm(f => ({ ...f, affiliate_url: e.target.value }))} placeholder="https://meli.la/..." style={inputStyle} />
            </label>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Título
              <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} style={inputStyle} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Preço (R$)
              <input type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} style={inputStyle} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Comissão %
              <input type="number" value={form.commission_pct} onChange={e => setForm(f => ({ ...f, commission_pct: e.target.value }))} style={inputStyle} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
              Categoria
              <input value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} style={inputStyle} />
            </label>
          </div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
            URL da Foto (imagem do produto)
            <input value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} placeholder="https://..." style={inputStyle} />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: muted }}>
            Notas
            <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} style={{ ...inputStyle, resize: "vertical" }} />
          </label>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={createProduct} disabled={saving} style={{ padding: "9px 22px", background: accent, color: "#fff", borderRadius: 9, border: "none", cursor: "pointer", fontWeight: 600 }}>
              {saving ? "Salvando…" : "Salvar"}
            </button>
            <button onClick={() => { setShowForm(false); setForm(emptyForm) }} style={{ padding: "9px 22px", background: "#fff", color: muted, borderRadius: 9, border: "1px solid #ddd", cursor: "pointer" }}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div style={cardStyle}>
        {/* Pagination controls top */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <span style={{ fontSize: 13, color: muted }}>
            Mostrando {products.length === 0 ? 0 : startIdx + 1}–{Math.min(startIdx + perPage, products.length)} de {products.length} produtos
          </span>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 13, color: muted }}>Por página:</span>
            {[20, 40, 60].map(n => (
              <button key={n} onClick={() => { setPerPage(n); setPage(1) }}
                style={{ padding: "4px 12px", borderRadius: 6, border: `1px solid ${perPage === n ? accent : "#ddd"}`, background: perPage === n ? accent : "#fff", color: perPage === n ? "#fff" : muted, cursor: "pointer", fontWeight: perPage === n ? 700 : 400 }}>
                {n}
              </button>
            ))}
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={pgBtn}>←</button>
            <span style={{ fontSize: 13, color: muted }}>{page}/{totalPages || 1}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={pgBtn}>→</button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: muted }}>Carregando…</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid rgba(108,92,231,0.1)" }}>
                  {["Foto", "Código ML", "Título", "Preço", "Comissão%", "Ganho/venda", "Est. mensal", "Ações"].map(h => (
                    <th key={h} style={{ padding: "10px 12px", textAlign: "left", color: muted, fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageProducts.map(p => (
                  <ProductRow key={p.id} product={p} onPatch={(data) => patchProduct(p.id, data)} onDelete={() => deleteProduct(p.id)} />
                ))}
                {pageProducts.length === 0 && (
                  <tr><td colSpan={8} style={{ textAlign: "center", padding: 30, color: muted }}>Nenhum produto encontrado.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function ProductRow({ product: p, onPatch, onDelete }: { product: Product; onPatch: (d: Record<string, unknown>) => void; onDelete: () => void }) {
  const [editPhoto, setEditPhoto] = useState(false)
  const [photoDraft, setPhotoDraft] = useState(p.image_url ?? "")

  function savePhoto() {
    setEditPhoto(false)
    onPatch({ image_url: photoDraft || null })
  }

  return (
    <tr style={{ borderBottom: "1px solid rgba(108,92,231,0.07)" }}>
      <td style={{ padding: "10px 12px" }}>
        {p.image_url
          ? <img src={p.image_url} alt="" width={48} height={48} style={{ borderRadius: 8, objectFit: "cover" }} />
          : <div style={{ width: 48, height: 48, borderRadius: 8, background: "#f0f0f8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>📦</div>
        }
      </td>
      <td style={{ padding: "10px 12px" }}>
        <a href={p.affiliate_url} target="_blank" rel="noreferrer" style={{ color: accent, textDecoration: "none", fontWeight: 600 }}>
          {p.ml_code ?? "—"} ↗
        </a>
      </td>
      <td style={{ padding: "10px 12px", maxWidth: 200 }}>
        <InlineEdit
          value={p.title}
          onSave={v => onPatch({ title: v || null })}
          render={p.title ? p.title : <span style={{ color: muted, fontStyle: "italic" }}>{p.ml_code ?? "sem título"}</span>}
        />
      </td>
      <td style={{ padding: "10px 12px" }}>
        <InlineEdit value={p.price} type="number" onSave={v => onPatch({ price: parseFloat(v) || 0 })} render={fmt(p.price)} />
      </td>
      <td style={{ padding: "10px 12px" }}>
        <InlineEdit value={p.commission_pct} type="number" onSave={v => onPatch({ commission_pct: parseFloat(v) || 0 })} render={`${p.commission_pct.toFixed(1)}%`} />
      </td>
      <td style={{ padding: "10px 12px", color: "#2ecc71", fontWeight: 600 }}>{fmt(p.commission_value)}</td>
      <td style={{ padding: "10px 12px", fontWeight: 700, color: accent }}>{fmt(p.estimate_month)}</td>
      <td style={{ padding: "10px 12px" }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {editPhoto ? (
            <input
              autoFocus
              value={photoDraft}
              onChange={e => setPhotoDraft(e.target.value)}
              onBlur={savePhoto}
              onKeyDown={e => e.key === "Enter" && savePhoto()}
              placeholder="https://..."
              style={{ ...inputStyle, width: 140, fontSize: 11 }}
            />
          ) : (
            <button onClick={() => { setPhotoDraft(p.image_url ?? ""); setEditPhoto(true) }}
              title="Editar URL da foto"
              style={iconBtn}>🖼️</button>
          )}
          <button onClick={onDelete} title="Remover" style={{ ...iconBtn, color: "#e74c3c" }}>🗑️</button>
        </div>
      </td>
    </tr>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ABA GERAR CONTEÚDO
// ═══════════════════════════════════════════════════════════════════════════════
type ContentType = "marketplace" | "tiktok" | "youtube"

interface MarketplaceResult {
  titulo: string
  descricao: string
  tags_busca: string[]
  sku: string
  texto_x1: string
}

interface TikTokSegment {
  gancho?: string
  problema?: string
  solucao?: string
  prova?: string
  cta?: string
  [key: string]: string | undefined
}

interface TikTokResult {
  segments: TikTokSegment
  legenda: string
  hashtags: string[]
  musica_sugerida: string
  dica_visual: string
}

interface YouTubeResult {
  titulo_video: string
  roteiro: string
  descricao: string
  tags: string[]
  timestamps: string[]
  thumbnail_texto: string
}

type GeneratedContent = MarketplaceResult | TikTokResult | YouTubeResult

function ContentTab({ token }: { token: string }) {
  const [products, setProducts] = useState<Product[]>([])
  const [selectedId, setSelectedId] = useState<string>("")
  const [type, setType] = useState<ContentType | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GeneratedContent | null>(null)

  const headers = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }

  useEffect(() => {
    fetch(`${API}/api/v1/affiliate/products`, { headers })
      .then(r => r.json())
      .then(d => setProducts(d.products ?? []))
  }, [])

  async function generate(t: ContentType) {
    if (!selectedId) return alert("Selecione um produto")
    setType(t)
    setLoading(true)
    setResult(null)
    try {
      const r = await fetch(`${API}/api/v1/affiliate/generate/${t}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ product_id: selectedId }),
      })
      if (!r.ok) throw new Error(await r.text())
      setResult(await r.json())
    } catch (e) {
      alert("Erro: " + e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 16px", color: "#1a1a2e" }}>✨ Gerar Conteúdo</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <select value={selectedId} onChange={e => { setSelectedId(e.target.value); setResult(null) }}
            style={{ ...inputStyle, minWidth: 260 }}>
            <option value="">Selecionar produto…</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>{p.title ?? p.ml_code ?? p.id}</option>
            ))}
          </select>
          {(["marketplace", "tiktok", "youtube"] as ContentType[]).map(t => (
            <button key={t} onClick={() => generate(t)} disabled={loading}
              style={{ padding: "10px 18px", borderRadius: 10, border: "none", cursor: loading ? "not-allowed" : "pointer", background: accent, color: "#fff", fontWeight: 600, opacity: loading && type === t ? 0.7 : 1 }}>
              {t === "marketplace" ? "📢 Marketplace" : t === "tiktok" ? "🎵 TikTok" : "📺 YouTube"}
            </button>
          ))}
        </div>
        {loading && <div style={{ marginTop: 20, color: muted, textAlign: "center" }}>Gerando conteúdo…</div>}
      </div>

      {result && type === "marketplace" && <MarketplaceResult data={result as MarketplaceResult} />}
      {result && type === "tiktok" && <TikTokResult data={result as TikTokResult} />}
      {result && type === "youtube" && <YouTubeResult data={result as YouTubeResult} />}
    </div>
  )
}

function MarketplaceResult({ data }: { data: MarketplaceResult }) {
  return (
    <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: 0, color: "#1a1a2e" }}>📢 Marketplace</h3>
      <Field label="Título" value={data.titulo} />
      <Field label="SKU" value={data.sku} />
      <Field label="Texto X1" value={data.texto_x1} />
      <Field label="Descrição" value={data.descricao} multiline />
      <div>
        <div style={{ fontSize: 12, color: muted, marginBottom: 6 }}>Tags de Busca</div>
        <Chips items={data.tags_busca ?? []} />
      </div>
    </div>
  )
}

const segmentColors: Record<string, string> = {
  gancho: "#7c6aff", problema: "#e74c3c", solucao: "#2ecc71", prova: "#f39c12", cta: "#3498db"
}

function TikTokResult({ data }: { data: TikTokResult }) {
  return (
    <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: 0, color: "#1a1a2e" }}>🎵 TikTok</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px,1fr))", gap: 10 }}>
        {Object.entries(data.segments ?? {}).map(([k, v]) => (
          <div key={k} style={{ background: `${segmentColors[k] ?? "#7c6aff"}18`, border: `1px solid ${segmentColors[k] ?? accent}44`, borderRadius: 10, padding: "10px 14px" }}>
            <div style={{ fontWeight: 700, color: segmentColors[k] ?? accent, fontSize: 12, textTransform: "uppercase", marginBottom: 6 }}>{k}</div>
            <div style={{ fontSize: 13 }}>{v}</div>
          </div>
        ))}
      </div>
      <Field label="Legenda" value={data.legenda} multiline />
      <div>
        <div style={{ fontSize: 12, color: muted, marginBottom: 6 }}>Hashtags</div>
        <Chips items={data.hashtags ?? []} />
      </div>
      <Field label="Música Sugerida" value={data.musica_sugerida} />
      {data.dica_visual && (
        <div style={{ background: "#fffbeb", border: "1px solid #f59e0b44", borderRadius: 10, padding: "10px 14px" }}>
          <span style={{ fontWeight: 700, color: "#d97706" }}>💡 Dica Visual: </span>
          <span style={{ fontSize: 13 }}>{data.dica_visual}</span>
        </div>
      )}
    </div>
  )
}

function YouTubeResult({ data }: { data: YouTubeResult }) {
  const [rotExpanded, setRotExpanded] = useState(false)
  return (
    <div style={{ ...cardStyle, display: "flex", flexDirection: "column", gap: 14 }}>
      <h3 style={{ margin: 0, color: "#1a1a2e" }}>📺 YouTube</h3>
      <Field label="Título do Vídeo" value={data.titulo_video} />
      {data.thumbnail_texto && (
        <div style={{ background: "#1a1a2e", color: "#fff", borderRadius: 10, padding: "14px 18px", fontSize: 18, fontWeight: 800, textAlign: "center" }}>
          {data.thumbnail_texto}
        </div>
      )}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: muted }}>Roteiro</span>
          <button onClick={() => setRotExpanded(v => !v)} style={{ fontSize: 12, color: accent, background: "none", border: "none", cursor: "pointer" }}>
            {rotExpanded ? "Recolher ▲" : "Expandir ▼"}
          </button>
        </div>
        {rotExpanded && <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, background: "#f8f8ff", borderRadius: 8, padding: 12 }}>{data.roteiro}</pre>}
      </div>
      <Field label="Descrição" value={data.descricao} multiline />
      {(data.timestamps?.length > 0) && (
        <div>
          <div style={{ fontSize: 12, color: muted, marginBottom: 6 }}>Timestamps</div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {data.timestamps.map((t, i) => <li key={i} style={{ fontSize: 13 }}>{t}</li>)}
          </ul>
        </div>
      )}
      <div>
        <div style={{ fontSize: 12, color: muted, marginBottom: 6 }}>Tags</div>
        <Chips items={data.tags ?? []} />
      </div>
    </div>
  )
}

function Field({ label, value, multiline }: { label: string; value: string; multiline?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: muted, marginBottom: 4 }}>{label}</div>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        {multiline
          ? <pre style={{ flex: 1, whiteSpace: "pre-wrap", fontSize: 13, background: "#f8f8ff", borderRadius: 8, padding: 10, margin: 0 }}>{value}</pre>
          : <span style={{ flex: 1, fontSize: 13 }}>{value}</span>
        }
        <CopyBtn text={value} />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// ABA SHORT LINKS
// ═══════════════════════════════════════════════════════════════════════════════
interface ShortLinkEntry {
  product_id: string
  productLabel: string
  campaign: string
  url: string
}

function ShortLinksTab({ token }: { token: string }) {
  const [products, setProducts] = useState<Product[]>([])
  const [selectedId, setSelectedId] = useState<string>("")
  const [campaign, setCampaign] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [history, setHistory] = useState<ShortLinkEntry[]>([])

  const headers = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }

  useEffect(() => {
    fetch(`${API}/api/v1/affiliate/products`, { headers })
      .then(r => r.json())
      .then(d => setProducts(d.products ?? []))
  }, [])

  async function generate() {
    if (!selectedId) return alert("Selecione um produto")
    setLoading(true)
    setResult(null)
    try {
      const r = await fetch(`${API}/api/v1/affiliate/shortlink`, {
        method: "POST",
        headers,
        body: JSON.stringify({ product_id: selectedId, source: "afiliados", campaign: campaign || undefined }),
      })
      if (!r.ok) throw new Error(await r.text())
      const d = await r.json()
      const url = d.short_url ?? d.url ?? JSON.stringify(d)
      setResult(url)
      const prod = products.find(p => p.id === selectedId)
      setHistory(prev => [
        { product_id: selectedId, productLabel: prod?.title ?? prod?.ml_code ?? selectedId, campaign, url },
        ...prev,
      ])
    } catch (e) {
      alert("Erro: " + e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={cardStyle}>
        <h3 style={{ margin: "0 0 16px", color: "#1a1a2e" }}>🔗 Gerar Short Link</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, color: muted }}>Produto</label>
            <select value={selectedId} onChange={e => { setSelectedId(e.target.value); setResult(null) }}
              style={{ ...inputStyle, minWidth: 260 }}>
              <option value="">Selecionar produto…</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.title ?? p.ml_code ?? p.id}</option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, color: muted }}>Campaign (opcional)</label>
            <input value={campaign} onChange={e => setCampaign(e.target.value)} placeholder="ex: instagram-bio" style={{ ...inputStyle, minWidth: 180 }} />
          </div>
          <button onClick={generate} disabled={loading}
            style={{ padding: "10px 22px", background: accent, color: "#fff", borderRadius: 10, border: "none", cursor: loading ? "not-allowed" : "pointer", fontWeight: 600, opacity: loading ? 0.7 : 1 }}>
            {loading ? "Gerando…" : "Gerar"}
          </button>
        </div>

        {result && (
          <div style={{ marginTop: 20, background: "rgba(124,106,255,0.06)", border: `1px solid ${accent}44`, borderRadius: 10, padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
            <a href={result} target="_blank" rel="noreferrer" style={{ color: accent, fontWeight: 700, fontSize: 16, flex: 1, wordBreak: "break-all" }}>{result}</a>
            <CopyBtn text={result} />
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 12px", color: "#1a1a2e" }}>Histórico da sessão</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {history.map((h, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid rgba(108,92,231,0.07)" }}>
                <span style={{ fontSize: 13, color: muted, minWidth: 160 }}>{h.productLabel}</span>
                {h.campaign && <span style={{ fontSize: 11, background: "rgba(124,106,255,0.1)", color: accent, borderRadius: 20, padding: "2px 8px" }}>{h.campaign}</span>}
                <a href={h.url} target="_blank" rel="noreferrer" style={{ color: accent, fontSize: 13, flex: 1, wordBreak: "break-all" }}>{h.url}</a>
                <CopyBtn text={h.url} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Shared styles ─────────────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid #ddd",
  fontSize: 13,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
}

const iconBtn: React.CSSProperties = {
  background: "none",
  border: "1px solid #eee",
  borderRadius: 6,
  padding: "4px 8px",
  cursor: "pointer",
  fontSize: 16,
}

const pgBtn: React.CSSProperties = {
  padding: "4px 10px",
  borderRadius: 6,
  border: "1px solid #ddd",
  background: "#fff",
  cursor: "pointer",
  fontSize: 14,
}
