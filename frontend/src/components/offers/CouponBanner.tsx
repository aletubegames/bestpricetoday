"use client"

import { useState, useEffect, useCallback } from "react"
import { API_BASE as API } from "@/lib/api"
import { trackCopyCoupon } from "@/lib/analytics"
import styles from "./CouponBanner.module.css"

interface Coupon {
  coupon_code: string
  discount_text: string | null
  discount_percent: number | null
  discount_value: number | null
  store_name: string | null
  expires_at: string | null
}

/**
 * Banner de cupom — mostra cupons ativos do Mercado Livre na página de produto.
 * Os cupons ML são genéricos (valem para qualquer produto da loja),
 * então basta mostrar os disponíveis.
 *
 * Botão "Copiar e ir para loja" copia o cupom e rola até o primeiro
 * card de oferta ("Ver oferta") da página.
 */
export default function CouponBanner({ provider }: { provider?: string }) {
  const [coupons, setCoupons] = useState<Coupon[]>([])
  const [copied, setCopied] = useState<string | null>(null)

  const fetchCoupons = useCallback(async () => {
    // Só busca cupons do ML (outros providers não têm cupom via scraper)
    const targetProvider = provider || "mercadolivre"
    try {
      const r = await fetch(`${API}/api/v1/affiliate/coupons?provider=${targetProvider}&active_only=true&limit=3`)
      if (!r.ok) return
      const d = await r.json()
      if (d.coupons && d.coupons.length > 0) {
        setCoupons(d.coupons.slice(0, 3))
      }
    } catch {
      // silencioso
    }
  }, [provider])

  useEffect(() => {
    fetchCoupons()
  }, [fetchCoupons])

  const handleCopyAndGo = (code: string, coupon: Coupon) => {
    navigator.clipboard.writeText(code)
    setCopied(code)
    trackCopyCoupon({
      coupon_code: code,
      discount_text: coupon.discount_text || undefined,
      store_name: coupon.store_name || undefined,
    })
    // Rola até o primeiro card de oferta da página
    const firstOffer = document.querySelector("[data-offer-card]")
    if (firstOffer) {
      firstOffer.scrollIntoView({ behavior: "smooth", block: "center" })
    }
    setTimeout(() => setCopied(null), 3000)
  }

  if (coupons.length === 0) return null

  return (
    <div className={styles.banner}>
      <div className={styles.header}>
        <span className={styles.icon}>🎫</span>
        <span className={styles.title}>Cupom disponível</span>
      </div>
      <div className={styles.coupons}>
        {coupons.map((c) => (
          <div key={c.coupon_code} className={styles.couponItem}>
            <div className={styles.couponInfo}>
              <code className={styles.code}>{c.coupon_code}</code>
              {c.discount_text && <span className={styles.discount}>{c.discount_text}</span>}
            </div>
            <button
              className={styles.copyBtn}
              onClick={() => handleCopyAndGo(c.coupon_code, c)}
            >
              {copied === c.coupon_code ? "✓ Copiado! Veja abaixo →" : "Copiar e ir para loja"}
            </button>
          </div>
        ))}
      </div>
      <p className={styles.hint}>
        Copie o cupom, clique na oferta abaixo e cole no checkout da loja!
      </p>
    </div>
  )
}
