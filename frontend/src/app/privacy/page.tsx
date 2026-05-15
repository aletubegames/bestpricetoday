import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de Privacidade — BestPriceToday",
  description: "Como o BestPriceToday coleta, usa e protege seus dados pessoais.",
  alternates: { canonical: "https://bestpricetoday.vercel.app/privacy" },
};

export default function PrivacyPage() {
  const updated = "15 de maio de 2025";

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "60px 20px 80px" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: 48 }}>
          <a href="/" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            ← BestPriceToday
          </a>
          <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.5px", marginTop: 24, marginBottom: 8 }}>
            Política de Privacidade
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted2)" }}>Última atualização: {updated}</p>
          <p style={{ fontSize: 14, color: "var(--muted)", marginTop: 12, lineHeight: 1.7 }}>
            Esta Política descreve como o BestPriceToday coleta, usa, armazena e protege suas informações pessoais,
            em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).
          </p>
        </div>

        <Section title="1. Controlador dos Dados">
          <strong style={{ color: "var(--txt)" }}>BestPriceToday</strong><br />
          Website: <a href="https://bestpricetoday.vercel.app" style={{ color: "var(--acc2)", textDecoration: "none" }}>
            bestpricetoday.vercel.app
          </a><br />
          Contato: <a href="mailto:privacidade@bestpricetoday.com.br"
                      style={{ color: "var(--acc2)", textDecoration: "none" }}>
            privacidade@bestpricetoday.com.br
          </a>
        </Section>

        <Section title="2. Dados que Coletamos">
          <strong style={{ color: "var(--txt)" }}>2.1 Dados fornecidos por você:</strong>
          <ul style={{ marginTop: 8, paddingLeft: 20, lineHeight: 2 }}>
            <li><strong>ID do Telegram:</strong> coletado quando você cria um alerta de preço via Telegram ou pela interface web</li>
            <li><strong>E-mail:</strong> coletado apenas se você se cadastrar voluntariamente (funcionalidade opcional)</li>
            <li><strong>Termos de busca:</strong> as pesquisas realizadas na plataforma, para otimização dos resultados</li>
          </ul>

          <strong style={{ color: "var(--txt)", display: "block", marginTop: 16 }}>2.2 Dados coletados automaticamente:</strong>
          <ul style={{ marginTop: 8, paddingLeft: 20, lineHeight: 2 }}>
            <li><strong>Endereço IP:</strong> registrado ao clicar em links de afiliados, para fins de analytics e prevenção de fraude</li>
            <li><strong>User-agent:</strong> tipo de navegador e dispositivo</li>
            <li><strong>Dados de navegação:</strong> páginas visitadas, tempo de sessão (via cookies de analytics, se ativados)</li>
          </ul>

          <strong style={{ color: "var(--txt)", display: "block", marginTop: 16 }}>2.3 Dados que NÃO coletamos:</strong>
          <ul style={{ marginTop: 8, paddingLeft: 20, lineHeight: 2 }}>
            <li>Dados de cartão de crédito ou informações de pagamento</li>
            <li>Senhas de outras plataformas</li>
            <li>Dados sensíveis (saúde, biometria, orientação política ou religiosa)</li>
          </ul>
        </Section>

        <Section title="3. Como Usamos seus Dados">
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14, marginTop: 8 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--bd)" }}>
                <th style={{ textAlign: "left", padding: "8px 12px 8px 0", color: "var(--txt)", fontWeight: 700 }}>Finalidade</th>
                <th style={{ textAlign: "left", padding: "8px 12px 8px 0", color: "var(--txt)", fontWeight: 700 }}>Base Legal (LGPD)</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Enviar notificações de alerta de preço", "Consentimento (art. 7º, I)"],
                ["Melhorar os resultados de busca", "Legítimo interesse (art. 7º, IX)"],
                ["Registrar cliques em links de afiliados", "Legítimo interesse (art. 7º, IX)"],
                ["Prevenção de fraude e abuso da API", "Legítimo interesse (art. 7º, IX)"],
                ["Cumprimento de obrigações legais", "Obrigação legal (art. 7º, II)"],
              ].map(([fin, base], i) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <td style={{ padding: "10px 12px 10px 0", color: "rgba(240,240,248,0.70)" }}>{fin}</td>
                  <td style={{ padding: "10px 12px 10px 0", color: "rgba(240,240,248,0.50)", fontSize: 13 }}>{base}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section title="4. Compartilhamento de Dados">
          Não vendemos seus dados pessoais. Compartilhamos apenas nas seguintes situações:

          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li>
              <strong>Marketplaces parceiros (AliExpress, Shopee, Amazon, Lomadee):</strong> ao clicar em um link
              de afiliado, você é redirecionado para o site do parceiro, que possui sua própria política de privacidade.
              Não transferimos seus dados pessoais a esses parceiros.
            </li>
            <li>
              <strong>Provedores de infraestrutura:</strong> Neon PostgreSQL (banco de dados), Upstash Redis (cache),
              Vercel (frontend), HuggingFace (backend) — todos operam sob contratos de processamento de dados adequados.
            </li>
            <li>
              <strong>Telegram:</strong> utilizado para entrega de notificações de alerta. Seu ID do Telegram é
              transmitido à API do Telegram exclusivamente para envio de mensagens.
            </li>
            <li>
              <strong>Obrigação legal:</strong> quando exigido por lei, ordem judicial ou autoridade competente.
            </li>
          </ul>
        </Section>

        <Section title="5. Retenção de Dados">
          <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
            <li><strong>Alertas de preço:</strong> mantidos enquanto ativos; excluídos sob solicitação</li>
            <li><strong>Logs de busca:</strong> retidos por até 90 dias para melhoria do serviço</li>
            <li><strong>Logs de cliques:</strong> retidos por até 12 meses para fins de analytics e auditoria de afiliados</li>
            <li><strong>Endereço IP:</strong> retido por até 30 dias em logs de acesso</li>
          </ul>
        </Section>

        <Section title="6. Seus Direitos (LGPD)">
          Como titular dos dados, você tem direito a:
          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li><strong>Confirmação e acesso:</strong> saber quais dados temos sobre você</li>
            <li><strong>Correção:</strong> atualizar dados incorretos ou desatualizados</li>
            <li><strong>Anonimização ou exclusão:</strong> solicitar a remoção dos seus dados</li>
            <li><strong>Portabilidade:</strong> receber seus dados em formato estruturado</li>
            <li><strong>Revogação do consentimento:</strong> cancelar alertas e remover seus dados a qualquer momento</li>
            <li><strong>Oposição:</strong> contestar o uso de dados baseado em legítimo interesse</li>
          </ul>
          Para exercer seus direitos, envie e-mail para{" "}
          <a href="mailto:privacidade@bestpricetoday.com.br"
             style={{ color: "var(--acc2)", textDecoration: "none" }}>
            privacidade@bestpricetoday.com.br
          </a>{" "}
          com o assunto "Direitos LGPD". Responderemos em até 15 dias úteis.
        </Section>

        <Section title="7. Cookies">
          Utilizamos cookies essenciais para o funcionamento da Plataforma (sessão, cache de busca).
          Não utilizamos cookies de rastreamento de terceiros para publicidade comportamental.
          Você pode desativar cookies nas configurações do seu navegador, mas isso pode afetar funcionalidades da Plataforma.
        </Section>

        <Section title="8. Segurança">
          Adotamos medidas técnicas e organizacionais para proteger seus dados:
          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li>Comunicações criptografadas via HTTPS/TLS</li>
            <li>Banco de dados com acesso restrito e credenciais seguras</li>
            <li>Sem armazenamento de senhas de usuários na Plataforma</li>
            <li>Monitoramento de erros via Sentry (sem dados pessoais nos logs)</li>
          </ul>
          Em caso de incidente de segurança que afete seus dados, notificaremos os titulares afetados e a ANPD
          conforme exigido pela LGPD.
        </Section>

        <Section title="9. Menores de Idade">
          O BestPriceToday não é direcionado a menores de 18 anos e não coleta intencionalmente dados de crianças
          ou adolescentes. Se tomarmos conhecimento de que coletamos dados de menor sem consentimento parental,
          os removeremos imediatamente.
        </Section>

        <Section title="10. Links para Sites Terceiros">
          A Plataforma contém links para sites de marketplaces parceiros. Não somos responsáveis pelas práticas
          de privacidade desses sites. Recomendamos a leitura das políticas de privacidade de cada plataforma
          antes de realizar uma compra.
        </Section>

        <Section title="11. Alterações nesta Política">
          Podemos atualizar esta Política periodicamente. A versão atual sempre estará disponível em{" "}
          <a href="https://bestpricetoday.vercel.app/privacy"
             style={{ color: "var(--acc2)", textDecoration: "none" }}>
            bestpricetoday.vercel.app/privacy
          </a>.
          Alterações significativas serão comunicadas por aviso na Plataforma.
        </Section>

        <Section title="12. Contato e DPO">
          Para questões de privacidade ou para exercer seus direitos:<br /><br />
          📧 <a href="mailto:privacidade@bestpricetoday.com.br"
                style={{ color: "var(--acc2)", textDecoration: "none" }}>
            privacidade@bestpricetoday.com.br
          </a><br />
          🌐 <a href="https://bestpricetoday.vercel.app"
                style={{ color: "var(--acc2)", textDecoration: "none" }}>
            bestpricetoday.vercel.app
          </a>
        </Section>

        <div style={{ marginTop: 48, paddingTop: 32, borderTop: "1px solid var(--bd)", display: "flex", gap: 24 }}>
          <a href="/terms" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            Termos de Uso →
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
        color: "rgba(240,240,248,0.70)",
      }}>
        {children}
      </div>
    </section>
  );
}
