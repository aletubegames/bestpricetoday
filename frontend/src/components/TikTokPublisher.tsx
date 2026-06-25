"use client"
/**
 * ShareButton — Compartilhar oferta com amigos
 * ============================================
 * Simples botão para copiar o link da oferta e compartilhar.
 */

import { useState } from "react"
import type { Offer } from "@/types"

interface ShareButtonProps {
  offer: Partial<Offer> & {
    affiliate_url?: string
    image_url?: string
    provider: string
    title?: string
    final_price?: number | null
  }
}

function fmt(n: number) {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ShareButton({ offer }: ShareButtonProps) {
  const [copied, setCopied] = useState(false)

  const handleShare = async () => {
    const link = offer.affiliate_url || ""
    const price = offer.final_price ?? 0
    const text = `🔥 ${offer.title?.slice(0, 60)}\n💰 R$ ${fmt(price)} no ${offer.provider?.toUpperCase()}\n\n${link}`
    
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error("Erro ao copiar:", e)
    }
  }

  return (
    <button
      onClick={handleShare}
      style={{
        marginTop: 8, width: "100%", padding: "10px", borderRadius: 10,
        background: "rgba(108,92,231,0.08)", border: "1px solid rgba(108,92,231,0.25)",
        color: "#6c6aff", cursor: "pointer", fontSize: 13, fontWeight: 700,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
      }}
    >
      {copied ? "✓ Copiado" : "📤 Compartilhar com amigos"}
    </button>
  )
}
