"use client"
/**
 * TikTokPublisher — Fluxo correto BestPriceToday
 * ================================================
 * 1. Usuário conecta conta TikTok via Login Kit
 * 2. Escolhe produto
 * 3. Plataforma gera short link rastreado (comissão BestPriceToday)
 * 4. Usuário compartilha no próprio TikTok via Share Kit
 *
 * A plataforma NÃO publica em nome do usuário.
 * A comissão é rastreada pelo short link independente de quem postou.
 */

import { useState, useEffect } from "react"
import { API_BASE as API } from "@/lib/api"
import type { Offer } from "@/types"

type TikTokOffer = Partial<Offer> & {
  affiliate_url?: string
  image?: string
  image_url?: string
  provider: string
  title?: string
}

interface TikTokPublisherProps {
  offer: TikTokOffer
}

type Step = "idle" | "connect" | "connected" | "generating" | "ready" | "error"

interface TikTokAccount {
  display_name: string
  avatar_url: string
  is_verified: boolean
  profile_link: string
  scopes: string
}

interface ShareResult {
  short_link: string
  share_kit_url: string
  caption: string
  hashtags: string
}

interface TikTokAuthResponse { state?: string; auth_url?: string }

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function fmt(n: number) {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TikTokPublisher({ offer }: TikTokPublisherProps) {
  const [isOpen, setIsOpen]       = useState(false)
  const [step, setStep]           = useState<Step>("idle")
  const [account, setAccount]     = useState<TikTokAccount | null>(null)
  const [shareResult, setShare]   = useState<ShareResult | null>(null)
  const [copied, setCopied]       = useState<string | null>(null)
  const [error, setError]         = useState<string | null>(null)

  // Verificar se há conta TikTok salva localmente (open_id no localStorage)
  useEffect(() => {
    const openId = localStorage.getItem("tiktok_open_id")
    if (openId && isOpen) {
      fetchAccountInfo(openId)
    }
  }, [isOpen])

  // ── Buscar conta conectada ─────────────────────────────────────────────────
  const fetchAccountInfo = async (openId: string) => {
    try {
      const res = await fetch(`${API}/api/v1/tiktok/account/me?open_id=${openId}`)
      if (res.ok) {
        const data = await res.json() as TikTokAccount
        setAccount(data)
        setStep("connected")
      } else {
        localStorage.removeItem("tiktok_open_id")
        setStep("connect")
      }
    } catch (error: unknown) {
      console.warn("TikTok account lookup failed:", error)
      setStep("connect")
    }
  }

  // ── Iniciar Login Kit ─────────────────────────────────────────────────────
  const connectTikTok = async () => {
    setStep("connect")
    setError(null)
    try {
      const res  = await fetch(`${API}/api/v1/tiktok/auth/user`)
      const data = await res.json() as TikTokAuthResponse
      if (!data.state || !data.auth_url) throw new Error("Resposta inválida do TikTok auth")

      // Salvar state para validar no callback
      localStorage.setItem("tiktok_oauth_state", data.state)

      // Abrir popup do TikTok
      const popup = window.open(
        data.auth_url,
        "TikTok Login",
        "width=480,height=700,scrollbars=yes"
      )

      // Escutar mensagem de retorno do callback (via postMessage ou polling)
      const interval = setInterval(async () => {
        if (popup?.closed) {
          clearInterval(interval)
          const openId = localStorage.getItem("tiktok_open_id")
          if (openId) {
            await fetchAccountInfo(openId)
          } else {
            setStep("idle")
          }
        }
      }, 1000)
    } catch (e: unknown) {
      console.warn("TikTok login failed:", getErrorMessage(e))
      setError("Erro ao iniciar login TikTok. Tente novamente.")
      setStep("error")
    }
  }

  // ── Desconectar ───────────────────────────────────────────────────────────
  const disconnect = () => {
    localStorage.removeItem("tiktok_open_id")
    setAccount(null)
    setShare(null)
    setStep("connect")
  }

  // ── Gerar link rastreado + Share Kit URL ──────────────────────────────────
  const generateShareLink = async () => {
    setStep("generating")
    setError(null)
    try {
      const openId = localStorage.getItem("tiktok_open_id")
      const res = await fetch(`${API}/api/v1/tiktok/share/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          affiliate_url:  offer.affiliate_url,
          provider:       offer.provider,
          product_title:  offer.title,
          price:          offer.final_price,
          tiktok_open_id: openId,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json() as ShareResult
      setShare(data)
      setStep("ready")
    } catch (e: unknown) {
      console.warn("TikTok share link failed:", getErrorMessage(e))
      setError("Erro ao gerar link. Tente novamente.")
      setStep("connected")
    }
  }

  // ── Copiar para clipboard ─────────────────────────────────────────────────
  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2500)
  }

  // ── Abrir Share Kit ───────────────────────────────────────────────────────
  const openShareKit = () => {
    if (shareResult?.share_kit_url) {
      window.open(shareResult.share_kit_url, "_blank")
    }
  }

  // ── Botão fechado ─────────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={() => {
          setIsOpen(true)
          const openId = localStorage.getItem("tiktok_open_id")
          setStep(openId ? "idle" : "connect")
        }}
        style={{
          marginTop: 8, width: "100%", padding: "10px", borderRadius: 10,
          background: "rgba(255,0,80,0.08)", border: "1px solid rgba(255,0,80,0.25)",
          color: "#ff3060", cursor: "pointer", fontSize: 13, fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
        }}
      >
        ♪ Compartilhar no TikTok
      </button>
    )
  }

  // ── Modal ─────────────────────────────────────────────────────────────────
  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,0.88)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 16,
    }}>
      <div style={{
        background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 20,
        width: "100%", maxWidth: 480, padding: 24, position: "relative",
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
            width: 38, height: 38, borderRadius: 10,
            background: "linear-gradient(135deg,#ff0050,#010101,#69c9d0)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
          }}>♪</div>
          <div>
            <h2 style={{ color: "#1a1a2e", fontSize: 17, margin: 0, fontWeight: 800 }}>Compartilhar no TikTok</h2>
            <p style={{ color: "#475569", fontSize: 11, margin: 0 }}>
              Compartilhe e ganhe comissão pelo link rastreado
            </p>
          </div>
        </div>

        {/* ── Produto selecionado ── */}
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid #1e293b",
          borderRadius: 10, padding: "10px 14px", marginBottom: 20,
          display: "flex", alignItems: "center", gap: 12,
        }}>
          {offer.image_url && (
            <img src={offer.image_url} alt="" loading="lazy" fetchPriority="low" style={{ width: 44, height: 44, objectFit: "cover", borderRadius: 8 }} />
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: "#1a1a2e", fontSize: 12, fontWeight: 600,
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {offer.title?.slice(0, 55)}
            </div>
            <div style={{ color: "#00e5a0", fontSize: 13, fontWeight: 800, marginTop: 2 }}>
              R$ {fmt(offer.final_price ?? 0)}
              {(offer.original_price ?? 0) > (offer.final_price ?? 0) && (
                <span style={{ color: "#475569", fontSize: 11, fontWeight: 400,
                  textDecoration: "line-through", marginLeft: 6 }}>
                  R$ {fmt(offer.original_price ?? 0)}
                </span>
              )}
            </div>
          </div>
          <div style={{
            background: "rgba(255,0,80,0.1)", border: "1px solid rgba(255,0,80,0.2)",
            borderRadius: 6, padding: "3px 8px", fontSize: 10, color: "#ff3060", fontWeight: 700,
          }}>
            {(offer.provider || "loja").toUpperCase()}
          </div>
        </div>

        {/* ── Steps ── */}
        <Steps current={step} />

        {/* ── Erro ── */}
        {error && (
          <div style={{
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 8, padding: "10px 14px", marginBottom: 16,
            fontSize: 12, color: "#f87171",
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* ── PASSO 1: Conectar conta TikTok ── */}
        {(step === "connect" || step === "idle") && (
          <div>
            <div style={{
              background: "rgba(124,106,255,0.06)", border: "1px solid rgba(124,106,255,0.15)",
              borderRadius: 10, padding: "12px 16px", marginBottom: 16,
              fontSize: 12, color: "#a78bfa", lineHeight: 1.7,
            }}>
              <strong>Por que conectar?</strong><br />
              Ao conectar sua conta TikTok, você pode compartilhar produtos com um link rastreado.
              Cada compra feita pelo seu link gera comissão para você via BestPriceToday. 💰
            </div>
            <button onClick={connectTikTok} style={{
              width: "100%", padding: "13px", borderRadius: 12,
              background: "linear-gradient(135deg,#ff0050,#ff3060)",
              border: "none", color: "#1a1a2e", cursor: "pointer",
              fontSize: 14, fontWeight: 800, letterSpacing: 0.3,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}>
              ♪ Conectar conta TikTok
            </button>
            <p style={{ textAlign: "center", fontSize: 10, color: "#334155", marginTop: 10 }}>
              Usamos apenas Login Kit — não publicamos nada em seu nome
            </p>
          </div>
        )}

        {/* ── PASSO 2: Conta conectada → gerar link ── */}
        {step === "connected" && account && (
          <div>
            <div style={{
              display: "flex", alignItems: "center", gap: 10, marginBottom: 16,
              background: "rgba(0,229,160,0.06)", border: "1px solid rgba(0,229,160,0.15)",
              borderRadius: 10, padding: "10px 14px",
            }}>
              {account.avatar_url && (
                <img src={account.avatar_url} alt="" style={{ width: 36, height: 36, borderRadius: "50%" }} />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ color: "#00e5a0", fontSize: 13, fontWeight: 700 }}>
                  ✓ Conectado como @{account.display_name}
                  {account.is_verified && <span style={{ color: "#60a5fa", marginLeft: 4 }}>✓</span>}
                </div>
                <div style={{ color: "#334155", fontSize: 10 }}>Conta TikTok pessoal</div>
              </div>
              <button onClick={disconnect} style={{
                background: "none", border: "1px solid #1e293b", borderRadius: 6,
                color: "#475569", cursor: "pointer", fontSize: 10, padding: "4px 8px",
              }}>
                Trocar
              </button>
            </div>

            <button onClick={generateShareLink} style={{
              width: "100%", padding: "13px", borderRadius: 12,
              background: "linear-gradient(135deg,#7c3aed,#a855f7)",
              border: "none", color: "#1a1a2e", cursor: "pointer",
              fontSize: 14, fontWeight: 800,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}>
              🔗 Gerar link rastreado + legenda
            </button>
          </div>
        )}

        {/* ── Gerando... ── */}
        {step === "generating" && (
          <div style={{ textAlign: "center", padding: "32px 0", color: "#4a4a6a", fontSize: 13 }}>
            <div style={{ marginBottom: 10, fontSize: 24 }}>⚙️</div>
            Gerando seu link rastreado...
          </div>
        )}

        {/* ── PASSO 3: Link gerado → compartilhar ── */}
        {step === "ready" && shareResult && (
          <div>
            {/* Link rastreado */}
            <Section label="🔗 Seu link de afiliado rastreado">
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input readOnly value={shareResult.short_link}
                  style={{
                    flex: 1, background: "#eef0ff", border: "1px solid rgba(108,92,231,0.2)",
                    padding: "9px 12px", borderRadius: 8, color: "#00e5a0",
                    fontSize: 12, fontFamily: "monospace",
                  }} />
                <CopyBtn text={shareResult.short_link} id="link" copied={copied} onCopy={copyToClipboard} />
              </div>
              <p style={{ fontSize: 10, color: "#334155", margin: "6px 0 0" }}>
                💡 Cada clique neste link é registrado. Quando alguém comprar, você recebe comissão.
              </p>
            </Section>

            {/* Legenda */}
            <Section label="📝 Legenda pronta para o TikTok">
              <textarea readOnly value={shareResult.caption} rows={6}
                style={{
                  width: "100%", background: "#eef0ff", border: "1px solid rgba(108,92,231,0.2)",
                  padding: "10px 12px", borderRadius: 8, color: "#1a1a2e",
                  fontSize: 12, resize: "none", lineHeight: 1.6, boxSizing: "border-box",
                }} />
              <CopyBtn text={shareResult.caption} id="caption" copied={copied} onCopy={copyToClipboard} full />
            </Section>

            {/* Hashtags */}
            <Section label="# Hashtags">
              <div style={{ display: "flex", gap: 8 }}>
                <input readOnly value={shareResult.hashtags}
                  style={{
                    flex: 1, background: "#eef0ff", border: "1px solid rgba(108,92,231,0.2)",
                    padding: "9px 12px", borderRadius: 8, color: "#4a4a6a", fontSize: 12,
                  }} />
                <CopyBtn text={shareResult.hashtags} id="tags" copied={copied} onCopy={copyToClipboard} />
              </div>
            </Section>

            {/* CTA: Share Kit */}
            <button onClick={openShareKit} style={{
              width: "100%", padding: "14px", borderRadius: 12, marginTop: 8,
              background: "linear-gradient(135deg,#ff0050,#ff3060)",
              border: "none", color: "#1a1a2e", cursor: "pointer",
              fontSize: 14, fontWeight: 800,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}>
              ♪ Abrir TikTok para compartilhar
            </button>

            <div style={{
              marginTop: 10, padding: "10px 14px", borderRadius: 8,
              background: "rgba(0,229,160,0.05)", border: "1px solid rgba(0,229,160,0.12)",
              fontSize: 11, color: "#00e5a0", lineHeight: 1.6,
            }}>
              ✅ Você decide o que publicar no seu TikTok.<br />
              O link rastreado garante que a comissão seja registrada automaticamente.
            </div>

            <button onClick={() => setStep("connected")} style={{
              marginTop: 10, width: "100%", padding: "9px", borderRadius: 8,
              background: "rgba(255,255,255,0.03)", border: "1px solid #1e293b",
              color: "#475569", cursor: "pointer", fontSize: 11,
            }}>
              ↺ Gerar novo link
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-componentes ────────────────────────────────────────────────────────────

function Steps({ current }: { current: Step }) {
  const steps = [
    { key: "connect",    label: "1. Conectar TikTok" },
    { key: "connected",  label: "2. Gerar link" },
    { key: "ready",      label: "3. Compartilhar" },
  ]
  const activeIdx = current === "connect" || current === "idle" ? 0
    : current === "connected" || current === "generating" ? 1
    : current === "ready" ? 2 : -1

  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
      {steps.map((s, i) => (
        <div key={s.key} style={{
          flex: 1, textAlign: "center", padding: "6px 4px", borderRadius: 8, fontSize: 10,
          fontWeight: i === activeIdx ? 700 : 400,
          background: i === activeIdx ? "rgba(124,106,255,0.15)" : "rgba(255,255,255,0.02)",
          border: `1px solid ${i === activeIdx ? "rgba(124,106,255,0.3)" : "#1e293b"}`,
          color: i < activeIdx ? "#00e5a0" : i === activeIdx ? "#a78bfa" : "#334155",
        }}>
          {i < activeIdx ? "✓ " : ""}{s.label}
        </div>
      ))}
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{
        color: "#475569", fontSize: 10, fontWeight: 700,
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
        background: done ? "rgba(0,229,160,0.12)" : "rgba(124,106,255,0.12)",
        border: `1px solid ${done ? "rgba(0,229,160,0.25)" : "rgba(124,106,255,0.25)"}`,
        color: done ? "#00e5a0" : "#a78bfa",
        transition: "all .2s",
      }}
    >
      {done ? "✓ Copiado!" : "Copiar"}
    </button>
  )
}
