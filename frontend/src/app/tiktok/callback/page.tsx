"use client"
/**
 * /tiktok/callback — Página de callback OAuth TikTok
 *
 * O TikTok redireciona para esta página após autorização.
 * Ela troca o code pelo token via backend e:
 * - Salva o open_id no localStorage
 * - Notifica o pai via postMessage (se foi aberto como popup)
 * - Exibe resultado para o usuário
 */

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { API_BASE as API } from "@/lib/api"
import { Suspense } from "react"

function TikTokCallbackInner() {
  const params  = useSearchParams()
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [message, setMessage] = useState("")
  const [account, setAccount] = useState<any>(null)

  useEffect(() => {
    const code  = params.get("code")
    const state = params.get("state")
    const error = params.get("error")

    if (error) {
      setStatus("error")
      setMessage(error === "access_denied"
        ? "Você cancelou a conexão com o TikTok."
        : `Erro TikTok: ${error}`)
      return
    }

    if (!code) {
      setStatus("error")
      setMessage("Código de autorização não encontrado.")
      return
    }

    // Detectar modo (admin ou user) pelo state salvo
    const savedState = localStorage.getItem("tiktok_oauth_state")
    const mode       = localStorage.getItem("tiktok_oauth_mode") || "user"

    const exchange = async () => {
      try {
        const res = await fetch(
          `${API}/api/v1/tiktok/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || "")}&mode=${mode}`
        )

        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || "Erro ao trocar o token")
        }

        const data = await res.json()

        // Salvar open_id no localStorage para uso posterior
        if (data.tiktok_open_id || data.open_id) {
          localStorage.setItem("tiktok_open_id", data.tiktok_open_id || data.open_id)
        }
        localStorage.removeItem("tiktok_oauth_state")
        localStorage.removeItem("tiktok_oauth_mode")

        setAccount(data)
        setStatus("success")
        setMessage(`Conta @${data.display_name} conectada com sucesso!`)

        // Notificar a janela pai (se popup)
        if (window.opener) {
          window.opener.postMessage({ type: "TIKTOK_AUTH_SUCCESS", data }, "*")
          setTimeout(() => window.close(), 2000)
        }
      } catch (e: any) {
        setStatus("error")
        setMessage(e.message || "Erro desconhecido")
        if (window.opener) {
          window.opener.postMessage({ type: "TIKTOK_AUTH_ERROR", error: e.message }, "*")
        }
      }
    }

    exchange()
  }, [params])

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "#060610", padding: 24,
    }}>
      <div style={{
        background: "#0d0d1a", border: "1px solid #2a2a3a", borderRadius: 20,
        padding: 32, maxWidth: 380, width: "100%", textAlign: "center",
      }}>
        {/* Logo TikTok */}
        <div style={{
          width: 56, height: 56, borderRadius: 16, margin: "0 auto 20px",
          background: "linear-gradient(135deg,#ff0050,#010101,#69c9d0)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 28,
        }}>♪</div>

        {status === "loading" && (
          <>
            <h2 style={{ color: "#fff", fontSize: 18, marginBottom: 8 }}>Conectando...</h2>
            <p style={{ color: "#64748b", fontSize: 13 }}>Autorizando com o TikTok</p>
            <div style={{ marginTop: 20 }}>
              <div style={{
                width: 36, height: 36, border: "3px solid #ff0050",
                borderTopColor: "transparent", borderRadius: "50%",
                animation: "spin 0.8s linear infinite", margin: "0 auto",
              }} />
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </>
        )}

        {status === "success" && (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
            <h2 style={{ color: "#00e5a0", fontSize: 18, marginBottom: 8 }}>TikTok conectado!</h2>
            {account?.avatar_url && (
              <img
                src={account.avatar_url}
                alt=""
                style={{ width: 56, height: 56, borderRadius: "50%", margin: "12px auto", display: "block" }}
              />
            )}
            <p style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 700 }}>
              @{account?.display_name}
              {account?.is_verified && <span style={{ color: "#60a5fa", marginLeft: 4 }}>✓</span>}
            </p>
            <p style={{ color: "#64748b", fontSize: 12, marginTop: 8 }}>
              {window.opener ? "Esta janela fechará automaticamente..." : "Você pode fechar esta aba."}
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div style={{ fontSize: 40, marginBottom: 12 }}>❌</div>
            <h2 style={{ color: "#f87171", fontSize: 18, marginBottom: 8 }}>Erro na conexão</h2>
            <p style={{ color: "#94a3b8", fontSize: 13, marginBottom: 20 }}>{message}</p>
            <button
              onClick={() => window.close()}
              style={{
                padding: "10px 24px", borderRadius: 10,
                background: "rgba(255,255,255,0.05)", border: "1px solid #2a2a3a",
                color: "#94a3b8", cursor: "pointer", fontSize: 13,
              }}
            >
              Fechar
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default function TikTokCallbackPage() {
  return (
    <Suspense fallback={
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "#060610", color: "#64748b", fontSize: 14,
      }}>
        Carregando...
      </div>
    }>
      <TikTokCallbackInner />
    </Suspense>
  )
}
