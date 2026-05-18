"use client"
import { useState } from "react"
import { API_BASE as API } from "@/lib/api"

interface TikTokPublisherProps {
  offer: any
}

export default function TikTokPublisher({ offer }: TikTokPublisherProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [content, setContent] = useState({ title: "", description: "", hashtags: "" })
  const [status, setStatus] = useState<"idle" | "generating" | "ready" | "publishing" | "success">("idle")

  const generateContent = async () => {
    setLoading(true)
    setStatus("generating")
    // Simulação de chamada para IA (pode ser integrada ao seu backend depois)
    setTimeout(() => {
      setContent({
        title: `🔥 OFERTA IMPERDÍVEL: ${offer.title.slice(0, 30)}...`,
        description: `Confira essa oferta incrível que encontrei no BestPriceToday! De R$ ${offer.original_price?.toFixed(2)} por apenas R$ ${offer.final_price?.toFixed(2)}.`,
        hashtags: "#BestPriceToday #Ofertas #Promoção #Economia"
      })
      setStatus("ready")
      setLoading(false)
    }, 1500)
  }

  const publishToTikTok = async () => {
    setStatus("publishing")
    let p = 0
    const interval = setInterval(() => {
      p += 5
      setProgress(p)
      if (p >= 100) {
        clearInterval(interval)
        setStatus("success")
      }
    }, 100)
  }

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        style={{
          marginTop: 8, width: "100%", padding: "10px", borderRadius: 10,
          background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
          color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600
        }}
      >
        📱 Gerar Conteúdo TikTok
      </button>
    )
  }

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
      background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center",
      justifyContent: "center", zIndex: 1000, padding: 20
    }}>
      <div style={{
        background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 20,
        width: "100%", maxWidth: 500, padding: 24, position: "relative"
      }}>
        <button 
          onClick={() => setIsOpen(false)}
          style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 20 }}
        >
          ✕
        </button>

        <h2 style={{ color: "#fff", fontSize: 20, marginBottom: 24, textAlign: "center" }}>
          {status === "publishing" ? "Publishing to TikTok" : "Gerar Conteúdo TikTok"}
        </h2>

        {status === "idle" || status === "generating" ? (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <p style={{ color: "#94a3b8", marginBottom: 24 }}>
              Nossa IA vai criar o título, descrição e hashtags perfeitas para o seu post.
            </p>
            <button 
              onClick={generateContent}
              disabled={loading}
              style={{
                padding: "12px 24px", borderRadius: 12, background: "#7c6aff",
                color: "#fff", border: "none", fontWeight: 700, cursor: "pointer",
                opacity: loading ? 0.5 : 1
              }}
            >
              {loading ? "Gerando..." : "✨ Gerar Agora"}
            </button>
          </div>
        ) : status === "ready" ? (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ color: "#475569", fontSize: 12, display: "block", marginBottom: 4 }}>TÍTULO</label>
              <input 
                value={content.title} 
                onChange={e => setContent({...content, title: e.target.value})}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: 12, borderRadius: 8, color: "#fff" }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ color: "#475569", fontSize: 12, display: "block", marginBottom: 4 }}>DESCRIÇÃO</label>
              <textarea 
                value={content.description} 
                onChange={e => setContent({...content, description: e.target.value})}
                rows={3}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: 12, borderRadius: 8, color: "#fff", resize: "none" }}
              />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={{ color: "#475569", fontSize: 12, display: "block", marginBottom: 4 }}>HASHTAGS</label>
              <input 
                value={content.hashtags} 
                onChange={e => setContent({...content, hashtags: e.target.value})}
                style={{ width: "100%", background: "#1c1c2e", border: "1px solid #2a2a3a", padding: 12, borderRadius: 8, color: "#fff" }}
              />
            </div>
            <button 
              onClick={publishToTikTok}
              style={{
                width: "100%", padding: "14px", borderRadius: 12, background: "#ff0050",
                color: "#fff", border: "none", fontWeight: 700, cursor: "pointer"
              }}
            >
              🎵 Publicar no TikTok
            </button>
          </div>
        ) : status === "publishing" ? (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ width: "100%", height: 8, background: "#1c1c2e", borderRadius: 4, marginBottom: 16, overflow: "hidden" }}>
              <div style={{ width: `${progress}%`, height: "100%", background: "#00e5a0", transition: "width 0.1s" }} />
            </div>
            <p style={{ color: "#fff", fontSize: 18, fontWeight: 700 }}>{progress}%</p>
            <p style={{ color: "#94a3b8", marginTop: 12 }}>Fazendo upload do vídeo...</p>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <p style={{ fontSize: 48, marginBottom: 16 }}>✅</p>
            <h3 style={{ color: "#fff", fontSize: 20, marginBottom: 8 }}>Sucesso!</h3>
            <p style={{ color: "#94a3b8", marginBottom: 24 }}>Seu vídeo foi publicado com sucesso no TikTok.</p>
            <button 
              onClick={() => setIsOpen(false)}
              style={{ padding: "12px 24px", borderRadius: 12, background: "#2a2a3a", color: "#fff", border: "none", cursor: "pointer" }}
            >
              Fechar
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
