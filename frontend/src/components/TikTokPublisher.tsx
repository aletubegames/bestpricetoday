"use client"
/**
 * TikTokPublisher — Compartilhamento simples de oferta
 * =====================================================
 * Botão que permite ao usuário compartilhar o produto com amigos.
 * Não exibe comissão, não conecta conta TikTok, não publica nada.
 */

import { useState } from "react"
import { API_BASE as API, apiFetch } from "@/lib/api"
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

interface ShareResult {
  short_link: string
  caption: string
  hashtags: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function fmt(n: number) {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TikTokPublisher({ offer }: TikTokPublisherProps) {
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const share = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(`${API}/api/v1/tiktok/share/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          affiliate_url: offer.affiliate_url,
          provider: offer.provider,
          product_title: offer.title,
          price: offer.final_price,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json() as ShareResult

      const text = `${data.caption}\n\n${data.short_link}\n\n${data.hashtags}`

      if (navigator.share) {
        await navigator.share({
          title: offer.title || "Oferta",
          text,
          url: data.short_link,
        })
      } else {
        await navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2500)
      }
    } catch (e: unknown) {
      console.warn("Share failed:", getErrorMessage(e))
      setError("Erro ao compartilhar. Tente novamente.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={share}
      disabled={loading}
      style={{
        marginTop: 8,
        width: "100%",
        padding: "10px",
        borderRadius: 10,
        background: "rgba(255,0,80,0.08)",
        border: "1px solid rgba(255,0,80,0.25)",
        color: "#ff3060",
        cursor: loading ? "wait" : "pointer",
        fontSize: 13,
        fontWeight: 700,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        opacity: loading ? 0.7 : 1,
      }}
    >
      {loading ? "⏳ Gerando link..." : copied ? "✅ Copiado!" : error ? "❌ Erro" : "↗️ Compartilhar oferta"}
    </button>
  )
}
