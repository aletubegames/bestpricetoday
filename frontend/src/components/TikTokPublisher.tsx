"use client"
import { useState } from "react"
import { API_BASE as API } from "@/lib/api"

interface TikTokPublisherProps {
  offer: any
}

function fmt(n: number) {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TikTokPublisher({ offer }: TikTokPublisherProps) {
  const [isOpen, setIsOpen]       = useState(false)
  const [loading, setLoading]     = useState(false)
  const [copied, setCopied]       = useState<string | null>(null)
  const [shortLink, setShortLink] = useState("")
  const [content, setContent]     = useState({
    title: "", caption: "", hashtags: "", link: "",
  })

  // ── Gera conteúdo e cria short link rastreado ─────────────────────────────
  const generate = async () => {
    setLoading(true)

    // 1. Criar short link rastreado no backend
    let trackedLink = offer.affiliate_url ?? ""
    try {
      const res = await fetch(`${API}/api/v1/links/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          affiliate_url: offer.affiliate_url,
          provider: offer.provider,
          product_title: offer.title,
          price: offer.final_price,
          source: "tiktok_user",
          campaign: "user_content",
        }),
      })
      if (res.ok) {
        const data = await res.json()
        trackedLink = `https://bestpricetoday.vercel.app/r/${data.code}`
        setShortLink(trackedLink)
      }
    } catch {
      // fallback: usa link original
    }

    // 2. Montar texto baseado na oferta
    const name     = offer.title?.slice(0, 50) ?? "produto"
    const price    = fmt(offer.final_price ?? 0)
    const original = offer.original_price > offer.final_price
      ? `~~R$ ${fmt(offer.original_price)}~~ ` : ""
    const disc     = offer.discount_percent >= 5
      ? `🔥 ${Math.round(offer.discount_percent)}% OFF — ` : ""
    const frete    = offer.shipping_free ? "\n✅ Frete grátis" : ""
    const provider = offer.provider
      ? offer.provider.charAt(0).toUpperCase() + offer.provider.slice(1) : "loja"

    const title = `${disc}${name}`

    const caption =
`${disc}${name}
${original}👉 R$ ${price}${frete}

🛒 Compra pelo link na bio ⬆️
${trackedLink}

Encontrei no BestPriceToday — compara preços em ${provider}, Amazon, Shopee e mais!`

    const hashtags =
`#oferta #desconto #promoção #bestpricetoday #${offer.provider ?? "compras"} #economize #dica #tiktokbrasil`

    setContent({ title, caption, hashtags, link: trackedLink })
    setLoading(false)
  }

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  // ── Botão fechado ─────────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={() => { setIsOpen(true); generate() }}
        style={{
          marginTop: 8, width: "100%", padding: "10px", borderRadius: 10,
          background: "rgba(255,0,80,0.08)", border: "1px solid rgba(255,0,80,0.25)",
          color: "#ff3060", cursor: "pointer", fontSize: 13, fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
        }}
      >
        ♪ Criar legenda TikTok
      </button>
    )
  }

  // ── Modal ─────────────────────────────────────────────────────────────────
  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.85)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 16,
    }}>
      <div style={{
        background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 20,
        width: "100%", maxWidth: 500, padding: 24, position: "relative",
        maxHeight: "92vh", overflowY: "auto",
      }}>
        {/* Fechar */}
        <button onClick={() => setIsOpen(false)} style={{
          position: "absolute", top: 14, right: 14,
          background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 22,
        }}>✕</button>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg,#ff0050,#ff3060)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18,
          }}>♪</div>
          <div>
            <h2 style={{ color: "#fff", fontSize: 17, margin: 0, fontWeight: 800 }}>Legenda para TikTok</h2>
            <p style={{ color: "#475569", fontSize: 11, margin: 0 }}>Cole no seu vídeo e ganhe comissão</p>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#94a3b8" }}>
            Gerando conteúdo...
          </div>
        ) : (
          <>
            {/* Como usar */}
            <div style={{
              background: "rgba(124,106,255,0.08)", border: "1px solid rgba(124,106,255,0.2)",
              borderRadius: 10, padding: "10px 14px", marginBottom: 20,
              fontSize: 12, color: "#a78bfa", lineHeight: 1.6,
            }}>
              <strong>Como usar:</strong> Filme você mostrando o produto →
              cole a legenda abaixo no TikTok → quando alguém comprar pelo link, você ganha comissão 💰
            </div>

            {/* Link rastreado */}
            <Section label="🔗 Link de afiliado rastreado">
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input readOnly value={content.link}
                  style={{
                    flex: 1, background: "#1c1c2e", border: "1px solid #2a2a3a",
                    padding: "9px 12px", borderRadius: 8, color: "#00e5a0",
                    fontSize: 12, fontFamily: "monospace",
                  }} />
                <CopyBtn text={content.link} id="link" copied={copied} onCopy={copyToClipboard} />
              </div>
            </Section>

            {/* Legenda completa */}
            <Section label="📝 Legenda completa (copie tudo)">
              <textarea readOnly value={content.caption} rows={7}
                style={{
                  width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a",
                  padding: "10px 12px", borderRadius: 8, color: "#e2e8f0",
                  fontSize: 12, resize: "none", lineHeight: 1.6, boxSizing: "border-box",
                }} />
              <CopyBtn text={content.caption} id="caption" copied={copied} onCopy={copyToClipboard} full />
            </Section>

            {/* Hashtags */}
            <Section label="# Hashtags">
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <input readOnly value={content.hashtags}
                  style={{
                    flex: 1, background: "#1c1c2e", border: "1px solid #2a2a3a",
                    padding: "9px 12px", borderRadius: 8, color: "#94a3b8", fontSize: 12,
                  }} />
                <CopyBtn text={content.hashtags} id="tags" copied={copied} onCopy={copyToClipboard} />
              </div>
            </Section>

            {/* Dica */}
            <div style={{
              marginTop: 16, padding: "10px 14px", borderRadius: 10,
              background: "rgba(0,229,160,0.06)", border: "1px solid rgba(0,229,160,0.15)",
              fontSize: 11, color: "#00e5a0", lineHeight: 1.6,
            }}>
              💡 O link rastreado registra cliques e comissões automaticamente.
              Cada venda pelo seu link conta para o seu histórico no BestPriceToday.
            </div>

            {/* Regenerar */}
            <button onClick={generate} style={{
              marginTop: 16, width: "100%", padding: "10px", borderRadius: 10,
              background: "rgba(255,255,255,0.04)", border: "1px solid #2a2a3a",
              color: "#475569", cursor: "pointer", fontSize: 12,
            }}>
              ↺ Regenerar conteúdo
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ── Sub-componentes ────────────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{
        color: "#475569", fontSize: 11, fontWeight: 700,
        display: "block", marginBottom: 6,
        textTransform: "uppercase", letterSpacing: ".05em",
      }}>{label}</label>
      {children}
    </div>
  )
}

function CopyBtn({ text, id, copied, onCopy, full }: {
  text: string; id: string; copied: string | null;
  onCopy: (t: string, k: string) => void; full?: boolean
}) {
  const done = copied === id
  return (
    <button
      onClick={() => onCopy(text, id)}
      style={{
        ...(full ? { width: "100%", marginTop: 8 } : { flexShrink: 0 }),
        padding: full ? "9px" : "9px 14px",
        borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 700,
        background: done ? "rgba(0,229,160,0.15)" : "rgba(124,106,255,0.15)",
        border: `1px solid ${done ? "rgba(0,229,160,0.3)" : "rgba(124,106,255,0.3)"}`,
        color: done ? "#00e5a0" : "#a78bfa",
        transition: "all .2s",
      }}
    >
      {done ? "✓ Copiado!" : "Copiar"}
    </button>
  )
}
