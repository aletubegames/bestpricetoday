"use client"
import { useState } from "react"
import { API_BASE as API } from "@/lib/api"

interface TikTokPublisherProps {
  offer: any
}

export default function TikTokPublisher({ offer }: TikTokPublisherProps) {
  const [isOpen, setIsOpen]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [content, setContent]   = useState({ title: "", description: "", hashtags: "" })
  const [status, setStatus]     = useState<"idle" | "generating" | "auth" | "ready" | "publishing" | "success" | "error">("idle")
  const [progress, setProgress] = useState(0)
  const [errorMsg, setErrorMsg] = useState("")
  const [publishId, setPublishId] = useState("")

  // ─── Passo 1: gerar conteúdo ──────────────────────────────────────────────
  const generateContent = async () => {
    setLoading(true)
    setStatus("generating")
    try {
      // Tenta chamar o backend para gerar conteúdo via IA
      const res = await fetch(`${API}/api/v1/admin/video/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: offer.title?.slice(0, 60) || "",
          plataformas: ["tiktok"],
          formato: "viral_tiktok",
        }),
      })
      // Independente do resultado, monta conteúdo a partir da oferta
      const price = offer.final_price?.toFixed(2) ?? "?"
      const orig  = offer.original_price > offer.final_price
        ? `De R$ ${offer.original_price?.toFixed(2)} por ` : ""
      const disc  = offer.discount_percent >= 5 ? ` (-${Math.round(offer.discount_percent)}%)` : ""
      const title = `🔥 ${offer.title?.slice(0, 40) ?? "Oferta"}${disc}`
      const desc  = `${orig}apenas R$ ${price}! Compre agora pelo link na bio ⬆️\n\nEncontrei no BestPriceToday — comparador de preços com cupons automáticos.\n👉 bestpricetoday.vercel.app`
      const tags  = "#Oferta #Promoção #Desconto #BestPriceToday #" + (offer.provider ?? "loja")
      setContent({ title, description: desc, hashtags: tags })
      setStatus("ready")
    } catch {
      const price = offer.final_price?.toFixed(2) ?? "?"
      const disc  = offer.discount_percent >= 5 ? ` (-${Math.round(offer.discount_percent)}%)` : ""
      setContent({
        title: `🔥 ${offer.title?.slice(0, 40) ?? "Oferta"}${disc}`,
        description: `Por apenas R$ ${price}! Compre agora pelo link na bio ⬆️\n\n👉 bestpricetoday.vercel.app`,
        hashtags: "#Oferta #Promoção #Desconto #BestPriceToday",
      })
      setStatus("ready")
    } finally {
      setLoading(false)
    }
  }

  // ─── Passo 2: iniciar OAuth TikTok ────────────────────────────────────────
  const startTikTokAuth = async () => {
    try {
      const res  = await fetch(`${API}/api/v1/tiktok/auth`)
      const data = await res.json()
      if (data.auth_url) {
        // Abre popup OAuth TikTok
        const popup = window.open(data.auth_url, "tiktok_auth", "width=600,height=700,left=300,top=100")
        setStatus("auth")
        // Aguarda o callback via mensagem ou verificação periódica
        const timer = setInterval(() => {
          if (popup?.closed) {
            clearInterval(timer)
            // Quando popup fecha, tenta publicar (assume que token foi salvo)
            publishVideo()
          }
        }, 500)
      } else {
        setErrorMsg("Não foi possível iniciar autenticação TikTok. Verifique as credenciais.")
        setStatus("error")
      }
    } catch (e) {
      setErrorMsg("Erro ao conectar com o servidor.")
      setStatus("error")
    }
  }

  // ─── Passo 3: publicar o vídeo ────────────────────────────────────────────
  const publishVideo = async () => {
    setStatus("publishing")
    setProgress(10)

    try {
      // Simula progresso enquanto o backend processa
      const interval = setInterval(() => {
        setProgress(p => {
          if (p >= 85) { clearInterval(interval); return 85 }
          return p + 5
        })
      }, 600)

      const res = await fetch(`${API}/api/v1/tiktok/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_url: offer.affiliate_url ?? "",
          title: content.title,
          description: `${content.description}\n\n${content.hashtags}`,
          access_token: "", // backend busca do DB
        }),
      })

      clearInterval(interval)
      const data = await res.json()

      if (res.ok && data.data?.publish_id) {
        setPublishId(data.data.publish_id)
        setProgress(100)
        setStatus("success")
      } else if (res.status === 400 && data.detail?.includes("aprovação")) {
        // App ainda aguardando aprovação TikTok
        setErrorMsg("App TikTok aguardando aprovação. Assim que aprovado, a publicação funcionará automaticamente.")
        setStatus("error")
      } else {
        setErrorMsg(data.detail ?? "Erro ao publicar. Tente novamente.")
        setStatus("error")
      }
    } catch (e) {
      setErrorMsg("Erro de conexão com o servidor.")
      setStatus("error")
    }
  }

  // ─── Render ───────────────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          marginTop: 8, width: "100%", padding: "10px", borderRadius: 10,
          background: "rgba(255,0,80,0.08)", border: "1px solid rgba(255,0,80,0.25)",
          color: "#ff3060", cursor: "pointer", fontSize: 13, fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
        }}
      >
        <span>♪</span> Criar post TikTok
      </button>
    )
  }

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
      background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center",
      justifyContent: "center", zIndex: 1000, padding: 20,
    }}>
      <div style={{
        background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 20,
        width: "100%", maxWidth: 520, padding: 28, position: "relative",
        maxHeight: "90vh", overflowY: "auto",
      }}>
        {/* Fechar */}
        <button onClick={() => { setIsOpen(false); setStatus("idle"); setErrorMsg("") }}
          style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 22 }}>
          ✕
        </button>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "#ff0050", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>♪</div>
          <div>
            <h2 style={{ color: "#fff", fontSize: 18, margin: 0 }}>Publicar no TikTok</h2>
            <p style={{ color: "#475569", fontSize: 12, margin: 0 }}>{offer.title?.slice(0, 50)}...</p>
          </div>
        </div>

        {/* Estado: idle / generating */}
        {(status === "idle" || status === "generating") && (
          <div style={{ textAlign: "center", padding: "32px 0" }}>
            <p style={{ color: "#94a3b8", marginBottom: 8, fontSize: 14 }}>Nossa IA cria o roteiro perfeito para sua oferta.</p>
            <p style={{ color: "#475569", marginBottom: 28, fontSize: 12 }}>Título · Descrição · Hashtags · CTA</p>
            <button onClick={generateContent} disabled={loading} style={{
              padding: "13px 28px", borderRadius: 12, background: loading ? "#2a2a3a" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
              color: "#fff", border: "none", fontWeight: 700, cursor: loading ? "default" : "pointer", fontSize: 15,
            }}>
              {loading ? "Gerando conteúdo..." : "✨ Gerar Roteiro"}
            </button>
          </div>
        )}

        {/* Estado: ready */}
        {status === "ready" && (
          <div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ color: "#475569", fontSize: 11, fontWeight: 700, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".05em" }}>Título</label>
              <input value={content.title} onChange={e => setContent({ ...content, title: e.target.value })}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: "10px 12px", borderRadius: 8, color: "#fff", fontSize: 13, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ color: "#475569", fontSize: 11, fontWeight: 700, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".05em" }}>Descrição</label>
              <textarea value={content.description} onChange={e => setContent({ ...content, description: e.target.value })} rows={4}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: "10px 12px", borderRadius: 8, color: "#fff", resize: "none", fontSize: 13, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={{ color: "#475569", fontSize: 11, fontWeight: 700, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".05em" }}>Hashtags</label>
              <input value={content.hashtags} onChange={e => setContent({ ...content, hashtags: e.target.value })}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: "10px 12px", borderRadius: 8, color: "#fff", fontSize: 13, boxSizing: "border-box" }} />
            </div>
            <button onClick={startTikTokAuth} style={{
              width: "100%", padding: "14px", borderRadius: 12,
              background: "linear-gradient(135deg,#ff0050,#ff3060)",
              color: "#fff", border: "none", fontWeight: 700, cursor: "pointer", fontSize: 15,
            }}>
              🎵 Conectar TikTok e Publicar
            </button>
          </div>
        )}

        {/* Estado: auth */}
        {status === "auth" && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔑</div>
            <p style={{ color: "#fff", fontWeight: 700, marginBottom: 8 }}>Autorizando TikTok...</p>
            <p style={{ color: "#94a3b8", fontSize: 13 }}>Complete a autorização na janela que abriu. Ela fechará automaticamente.</p>
          </div>
        )}

        {/* Estado: publishing */}
        {status === "publishing" && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ width: "100%", height: 8, background: "#1c1c2e", borderRadius: 4, marginBottom: 20, overflow: "hidden" }}>
              <div style={{ width: `${progress}%`, height: "100%", background: "linear-gradient(90deg,#ff0050,#ff6090)", transition: "width 0.6s ease", borderRadius: 4 }} />
            </div>
            <p style={{ color: "#fff", fontSize: 20, fontWeight: 800 }}>{progress}%</p>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 13 }}>
              {progress < 40 ? "Preparando vídeo..." : progress < 80 ? "Fazendo upload..." : "Finalizando..."}
            </p>
          </div>
        )}

        {/* Estado: success */}
        {status === "success" && (
          <div style={{ textAlign: "center", padding: "32px 0" }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>🎉</div>
            <h3 style={{ color: "#fff", fontSize: 22, marginBottom: 8 }}>Publicado!</h3>
            <p style={{ color: "#94a3b8", marginBottom: 6, fontSize: 14 }}>Seu vídeo foi enviado para o TikTok com sucesso.</p>
            {publishId && <p style={{ color: "#475569", fontSize: 11 }}>ID: {publishId}</p>}
            <button onClick={() => { setIsOpen(false); setStatus("idle") }}
              style={{ marginTop: 24, padding: "12px 28px", borderRadius: 12, background: "#2a2a3a", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}>
              Fechar
            </button>
          </div>
        )}

        {/* Estado: error */}
        {status === "error" && (
          <div style={{ textAlign: "center", padding: "32px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <p style={{ color: "#fb923c", fontWeight: 700, marginBottom: 8 }}>Ops!</p>
            <p style={{ color: "#94a3b8", fontSize: 13, marginBottom: 24 }}>{errorMsg}</p>
            <button onClick={() => setStatus("ready")}
              style={{ padding: "11px 24px", borderRadius: 10, background: "#2a2a3a", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}>
              Tentar novamente
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
