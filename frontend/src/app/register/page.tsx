"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { API_BASE as API } from "@/lib/api"
import Link from "next/link"

type RegisterForm = { name: string; email: string; password: string; confirm: string }

const fields: Array<{
  key: keyof RegisterForm;
  label: string;
  type: string;
  placeholder: string;
  autoComplete: string;
}> = [
  { key: "name",     label: "Nome",            type: "text",     placeholder: "Seu nome",             autoComplete: "name" },
  { key: "email",    label: "E-mail",          type: "email",    placeholder: "seu@email.com",        autoComplete: "email" },
  { key: "password", label: "Senha",           type: "password", placeholder: "Mínimo 6 caracteres",  autoComplete: "new-password" },
  { key: "confirm",  label: "Confirmar senha", type: "password", placeholder: "Repita a senha",       autoComplete: "new-password" },
]

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm]       = useState<RegisterForm>({ name: "", email: "", password: "", confirm: "" })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState("")

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) { setError("As senhas não coincidem."); return }
    if (form.password.length < 6) { setError("Senha deve ter pelo menos 6 caracteres."); return }
    setLoading(true)
    setError("")
    try {
      const res = await fetch(`${API}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.name, email: form.email, password: form.password }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail ?? "Erro ao cadastrar."); return }

      localStorage.setItem("bpt_token", data.access_token)
      localStorage.setItem("bpt_user", JSON.stringify(data.user))
      router.push("/dashboard")
    } catch {
      setError("Erro de conexão.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f0f4ff", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <span style={{ fontSize: 32 }}>🛍️</span>
            <p style={{ color: "#7c6aff", fontWeight: 800, fontSize: 20, margin: "8px 0 0" }}>BestPriceToday</p>
          </Link>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid rgba(108,92,231,0.2)", borderRadius: 20, padding: 32 }}>
          <h1 style={{ color: "#1a1a2e", fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Criar conta</h1>
          <p style={{ color: "#475569", fontSize: 13, marginBottom: 28 }}>Gratuito. Sem cartão de crédito.</p>

          <form onSubmit={submit}>
            {fields.map(f => (
              <div key={f.key} style={{ marginBottom: 16 }}>
                <label style={labelStyle}>{f.label}</label>
                <input
                  type={f.type} required
                  value={form[f.key]}
                  autoComplete={f.autoComplete}
                  onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                  placeholder={f.placeholder}
                  style={inputStyle}
                />
              </div>
            ))}

            {error && (
              <div style={{ background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.3)", borderRadius: 8, padding: "10px 14px", color: "#f43f5e", fontSize: 13, marginBottom: 16 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} style={btnStyle(loading)}>
              {loading ? "Criando conta..." : "Criar conta →"}
            </button>
          </form>

          <p style={{ textAlign: "center", color: "#475569", fontSize: 13, marginTop: 20 }}>
            Já tem conta?{" "}
            <Link href="/login" style={{ color: "#7c6aff", fontWeight: 600 }}>Entrar</Link>
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
