import Link from "next/link"

export default function NotFound() {
  return (
    <div style={{
      minHeight: "100vh", background: "#f0f4ff",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "system-ui", padding: 24,
    }}>
      <div style={{ textAlign: "center", maxWidth: 480 }}>
        <div style={{
          fontSize: 96, fontWeight: 900, lineHeight: 1,
          background: "linear-gradient(135deg,#7c6aff,#a78bfa)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          marginBottom: 8,
        }}>
          404
        </div>
        <h1 style={{ color: "#1a1a2e", fontSize: 22, fontWeight: 800, marginBottom: 8 }}>
          Página não encontrada
        </h1>
        <p style={{ color: "#475569", fontSize: 14, marginBottom: 32, lineHeight: 1.6 }}>
          O link pode ter expirado, o produto foi removido, ou a URL está incorreta.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/" style={{
            padding: "12px 28px", borderRadius: 10,
            background: "#7c6aff", color: "#1a1a2e",
            fontWeight: 700, fontSize: 14, textDecoration: "none",
          }}>
            🛍️ Buscar ofertas
          </Link>
          <Link href="/alertas" style={{
            padding: "12px 24px", borderRadius: 10,
            background: "rgba(255,255,255,0.05)", border: "1px solid rgba(108,92,231,0.2)",
            color: "#4a4a6a", fontWeight: 600, fontSize: 14, textDecoration: "none",
          }}>
            🔔 Criar alerta
          </Link>
        </div>
      </div>
    </div>
  )
}
