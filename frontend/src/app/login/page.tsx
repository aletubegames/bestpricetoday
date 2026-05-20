"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API } from "@/lib/api"
import Link from "next/link"

export default function LoginPage() {
  const router = useRouter()
  const [form, setForm]     = useState({ email: "", password: "" })
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState("")

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    try {
      const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
        credentials: "include"
      })
      
      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? "Erro ao entrar.")
        return
      }
      
      const data = await res.json()
      console.log('Login success:', data)
      
      localStorage.setItem("bpt_token", data.access_token)
      localStorage.setItem("bpt_user", JSON.stringify(data.user))
      console.log('Saved to localStorage')

      if (data.user.is_admin) {
        router.push("/admin")
      } else {
        router.push("/dashboard")
      }
    } catch (err) {
      console.error('Login error:', err)
      setError("Erro de conexão.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <span style={{ fontSize: 32 }}>🛍️</span>
            <p style={{ color: "#7c6aff", fontWeight: 800, fontSize: 20, margin: "8px 0 0" }}>BestPriceToday</p>
          </Link>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 20, padding: 32 }}>
          <h1 style={{ color: "#1a1a2e", fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Entrar</h1>
          <p style={{ color: "#475569", fontSize: 13, marginBottom: 28 }}>Acesse alertas, histórico e mais.</p>

          <form onSubmit={submit}>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>E-mail</label>
              <input
                type="email" required value={form.email}
                autoComplete="email"
                onChange={e => setForm({ ...form, email: e.target.value })}
                placeholder="seu@email.com"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle}>Senha</label>
              <input
                type="password" required value={form.password}
                autoComplete="current-password"
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••"
                style={inputStyle}
              />
            </div>

            {error && (
              <div style={{ background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.3)", borderRadius: 8, padding: "10px 14px", color: "#f43f5e", fontSize: 13, marginBottom: 16 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} style={btnStyle(loading)}>
              {loading ? "Entrando..." : "Entrar →"}
            </button>
          </form>

          <p style={{ textAlign: "center", color: "#475569", fontSize: 13, marginTop: 20 }}>
            Não tem conta?{" "}
            <Link href="/register" style={{ color: "#7c6aff", fontWeight: 600 }}>Cadastre-se</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  display: "block", color: "#475569", fontSize: 11, fontWeight: 700,
  textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6,
}
const inputStyle: React.CSSProperties = {
  width: "100%", background: "#f5f7ff", border: "1px solid rgba(108,92,231,0.2)",
  padding: "11px 14px", borderRadius: 10, color: "#1a1a2e", fontSize: 14,
  boxSizing: "border-box", outline: "none",
}
const btnStyle = (loading: boolean): React.CSSProperties => ({
  width: "100%", padding: "13px", borderRadius: 12, border: "none",
  background: loading ? "rgba(108,92,231,0.2)" : "linear-gradient(135deg,#7c6aff,#a78bfa)",
  color: "#1a1a2e", fontWeight: 700, fontSize: 15, cursor: loading ? "default" : "pointer",
})
