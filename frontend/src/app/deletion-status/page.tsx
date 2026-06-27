"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { Metadata } from "next";

// Note: metadata not available in client components, removed

export default function DeletionStatusPage() {
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // Check URL params for code
  useEffect(() => {
    const params = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
    const codeParam = params.get("code");
    if (codeParam) {
      setCode(codeParam);
      handleSearch(codeParam);
    }
  }, []);

  const handleSearch = async (searchCode?: string) => {
    const codeToSearch = searchCode || code;
    if (!codeToSearch.trim()) {
      setError("Por favor, insira um código de confirmação.");
      return;
    }

    setLoading(true);
    setError("");
    setSearched(true);

    try {
      const response = await apiFetch(
        `/api/v1/facebook/deletion-status/${encodeURIComponent(codeToSearch)}`
      );
      const data = await response.json();

      if (!response.ok) {
        setError("Erro ao buscar status. Tente novamente.");
        setStatus(null);
        return;
      }

      setStatus(data);
    } catch (err) {
      setError("Erro de conexão. Verifique sua internet e tente novamente.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "60px 20px 80px" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        
        {/* Header */}
        <div style={{ marginBottom: 48 }}>
          <a href="/" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            ← BestPriceToday
          </a>
          <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.5px", marginTop: 24, marginBottom: 8 }}>
            Status de Exclusão de Dados
          </h1>
          <p style={{ fontSize: 14, color: "var(--muted)", marginTop: 12, lineHeight: 1.7 }}>
            Acompanhe o andamento da sua solicitação de exclusão de dados enviada via Facebook.
          </p>
        </div>

        {/* Instructions */}
        <Section title="Como usar esta página">
          <p style={{ marginBottom: 12 }}>
            Quando você solicita a exclusão dos seus dados através do Facebook (Meta), recebe um <strong>código de confirmação</strong> e um <strong>link de status</strong>. Utilize o código abaixo para acompanhar o progresso da exclusão.
          </p>
        </Section>

        {/* Search Form */}
        <div style={{
          marginBottom: 36,
          padding: 20,
          background: "rgba(108, 92, 231, 0.08)",
          border: "1px solid rgba(108, 92, 231, 0.2)",
          borderRadius: 8,
        }}>
          <label style={{ display: "block", marginBottom: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--txt)" }}>
              Código de Confirmação
            </span>
            <input
              type="text"
              placeholder="Insira seu código de confirmação aqui"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              style={{
                width: "100%",
                padding: "10px 12px",
                marginTop: 8,
                border: "1px solid rgba(108, 92, 231, 0.3)",
                borderRadius: 6,
                fontSize: 14,
                fontFamily: "inherit",
                background: "rgba(255, 255, 255, 0.5)",
                color: "var(--txt)",
              }}
            />
          </label>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            style={{
              marginTop: 12,
              padding: "10px 16px",
              background: loading ? "rgba(108, 92, 231, 0.5)" : "rgba(108, 92, 231, 0.9)",
              color: "white",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                (e.target as HTMLButtonElement).style.background = "rgba(108, 92, 231, 1)";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                (e.target as HTMLButtonElement).style.background = "rgba(108, 92, 231, 0.9)";
              }
            }}
          >
            {loading ? "Procurando..." : "Verificar Status"}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div style={{
            marginBottom: 24,
            padding: 16,
            background: "rgba(255, 59, 48, 0.1)",
            border: "1px solid rgba(255, 59, 48, 0.3)",
            borderRadius: 6,
            color: "#FF3B30",
            fontSize: 14,
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Status Result */}
        {status && searched && (
          <div style={{
            marginBottom: 36,
            padding: 20,
            background: status.status === "completed" ? "rgba(76, 175, 80, 0.1)" : "rgba(255, 193, 7, 0.1)",
            border: `1px solid ${status.status === "completed" ? "rgba(76, 175, 80, 0.3)" : "rgba(255, 193, 7, 0.3)"}`,
            borderRadius: 8,
          }}>
            <h3 style={{
              fontSize: 18,
              fontWeight: 700,
              color: status.status === "completed" ? "#4CAF50" : "#FFC107",
              marginBottom: 12,
            }}>
              {status.status === "completed" && "✅ Exclusão Concluída"}
              {status.status === "processing" && "⏳ Processando"}
              {status.status === "failed" && "❌ Erro na Exclusão"}
              {status.status === "not_found" && "❓ Código Não Encontrado"}
            </h3>
            
            <p style={{ marginBottom: 12, fontSize: 14, lineHeight: 1.6 }}>
              {status.message}
            </p>

            {status.eta && (
              <p style={{ marginBottom: 12, fontSize: 14, color: "rgba(26, 26, 46, 0.75)" }}>
                <strong>Estimativa:</strong> {status.eta}
              </p>
            )}

            {status.deleted_fields && Object.keys(status.deleted_fields).length > 0 && (
              <div style={{ marginTop: 12 }}>
                <strong style={{ fontSize: 13 }}>Dados excluídos:</strong>
                <ul style={{ paddingLeft: 20, marginTop: 8, fontSize: 13 }}>
                  {Object.entries(status.deleted_fields).map(([key, value]) => (
                    <li key={key}>{key}: {String(value)}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid currentColor", opacity: 0.7 }}>
              <span style={{ fontSize: 12 }}>
                Código: <strong>{status.confirmation_code}</strong>
              </span>
            </div>
          </div>
        )}

        {/* Information */}
        <Section title="O que acontece durante a exclusão?">
          <ol style={{ paddingLeft: 20, lineHeight: 2.2 }}>
            <li>
              <strong>Solicitação recebida:</strong> Assim que clicamos em "Enviar solicitação" no Facebook,
              nosso sistema recebe a notificação e gera um código de confirmação único.
            </li>
            <li>
              <strong>Processamento:</strong> Seus dados pessoais são imediatamente marcados para exclusão e
              removidos de todos os registros ativos da plataforma (banco de dados principal, caches, backups).
            </li>
            <li>
              <strong>Conclusão:</strong> A exclusão é concluída em até 48 horas. Você pode usar seu código de
              confirmação aqui para acompanhar o andamento.
            </li>
          </ol>
        </Section>

        <Section title="Dados que serão excluídos">
          <ul style={{ paddingLeft: 20, lineHeight: 2.2 }}>
            <li>ID da sua conta no Facebook/Meta (se aplicável)</li>
            <li>E-mail (se fornecido)</li>
            <li>ID do Telegram (se usado para alertas)</li>
            <li>Histórico de alertas de preço</li>
            <li>Histórico de buscas e cliques na plataforma</li>
            <li>Logs de acesso associados ao seu perfil</li>
          </ul>
        </Section>

        <Section title="Dados que NÃO serão excluídos">
          <p style={{ marginBottom: 12 }}>
            Alguns dados podem ser retidos por razões legais ou técnicas:
          </p>
          <ul style={{ paddingLeft: 20, lineHeight: 2.2 }}>
            <li>
              <strong>Registros de transações de afiliados:</strong> Retidos por até 12 meses para fins de
              auditoria e conformidade fiscal.
            </li>
            <li>
              <strong>Logs de segurança:</strong> Dados agregados e anonimizados podem ser retidos para fins de
              prevenção de fraude (sem identificação pessoal).
            </li>
            <li>
              <strong>Pedidos legais:</strong> Se exigido por ordem judicial ou autoridade governamental.
            </li>
          </ul>
        </Section>

        <Section title="Dúvidas frequentes">
          <div style={{ marginBottom: 20 }}>
            <strong style={{ color: "var(--txt)" }}>P: Quanto tempo leva para meus dados serem excluídos?</strong>
            <p style={{ marginTop: 8, color: "rgba(26, 26, 46, 0.75)" }}>
              R: A exclusão é iniciada imediatamente após o envio da solicitação e completada em até 48 horas.
            </p>
          </div>

          <div style={{ marginBottom: 20 }}>
            <strong style={{ color: "var(--txt)" }}>P: Posso cancelar a solicitação?</strong>
            <p style={{ marginTop: 8, color: "rgba(26, 26, 46, 0.75)" }}>
              R: Após enviar a solicitação através do Facebook, ela não pode ser cancelada. Contate-nos se tiver
              dúvidas sobre o processo.
            </p>
          </div>

          <div style={{ marginBottom: 20 }}>
            <strong style={{ color: "var(--txt)" }}>P: Meus dados serão vendidos antes de serem excluídos?</strong>
            <p style={{ marginTop: 8, color: "rgba(26, 26, 46, 0.75)" }}>
              R: Não. Nunca vendemos dados pessoais. A exclusão começa imediatamente ao recebermos a solicitação.
            </p>
          </div>

          <div style={{ marginBottom: 20 }}>
            <strong style={{ color: "var(--txt)" }}>P: E se eu não receber um código de confirmação?</strong>
            <p style={{ marginTop: 8, color: "rgba(26, 26, 46, 0.75)" }}>
              R: Verifique sua caixa de e-mail (incluindo spam) ou entre em contato conosco em{" "}
              <a href="mailto:aletubegames@gmail.com" style={{ color: "var(--acc2)", textDecoration: "none" }}>
                aletubegames@gmail.com
              </a>
            </p>
          </div>
        </Section>

        <Section title="Contato e suporte">
          Se tiver dúvidas sobre sua solicitação de exclusão, entre em contato:<br /><br />
          📧 <a href="mailto:aletubegames@gmail.com"
                style={{ color: "var(--acc2)", textDecoration: "none" }}>
            aletubegames@gmail.com
          </a><br /><br />
          Por favor, inclua seu código de confirmação no e-mail para que possamos ajudá-lo mais rapidamente.
        </Section>

        <div style={{ marginTop: 48, paddingTop: 32, borderTop: "1px solid var(--bd)", display: "flex", gap: 24 }}>
          <a href="/privacy" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            ← Política de Privacidade
          </a>
          <a href="/" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            ← Voltar para busca
          </a>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 36 }}>
      <h2 style={{
        fontSize: 18, fontWeight: 700, letterSpacing: "-0.2px",
        marginBottom: 14, color: "var(--txt)",
      }}>
        {title}
      </h2>
      <div style={{
        fontSize: 15, lineHeight: 1.8,
        color: "rgba(26, 26, 46, 0.75)",
      }}>
        {children}
      </div>
    </section>
  );
}
