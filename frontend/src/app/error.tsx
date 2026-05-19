"use client"
import { useEffect } from "react"
import Link from "next/link"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div style={{
      minHeight: "100vh", background: "#07070f",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "system-ui", padding: 24,
    }}>
      <div style={{ textAlign: "center", maxWidth: 480 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>⚠️</div>
        <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 900, marginBottom: 8 }}>
          Algo deu errado
        </h1>
        <p style={{ color: "#475569", fontSize: 14, marginBottom: 32, lineHeight: 1.6 }}>
          Ocorreu um erro inesperado. Tente novamente ou volte para a página inicial.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <button
            onClick={reset}
            style={{
              padding: "11px 24px", borderRadius: 10, cursor: "pointer",
              background: "#7c6aff", border: "none", color: "#fff",
              fontWeight: 700, fontSize: 14,
            }}
          >
            ↺ Tentar novamente
          </button>
          <Link href="/" style={{
            padding: "11px 24px", borderRadius: 10,
            background: "rgba(255,255,255,0.05)", border: "1px solid #2a2a3a",
            color: "#94a3b8", fontWeight: 600, fontSize: 14, textDecoration: "none",
          }}>
            ← Início
          </Link>
        </div>
        {error.digest && (
          <p style={{ color: "#334155", fontSize: 10, marginTop: 24, fontFamily: "monospace" }}>
            ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  )
}
