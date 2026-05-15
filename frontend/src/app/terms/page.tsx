import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Termos de Uso — BestPriceToday",
  description: "Termos e condições de uso da plataforma BestPriceToday.",
  alternates: { canonical: "https://bestpricetoday.vercel.app/terms" },
};

export default function TermsPage() {
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
            Termos de Uso
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted2)" }}>Última atualização: {updated}</p>
        </div>

        <Section title="1. Aceitação dos Termos">
          Ao acessar ou usar o BestPriceToday ("Plataforma"), você concorda com estes Termos de Uso. Se não concordar,
          não utilize a Plataforma. O uso continuado após alterações implica aceitação das novas condições.
        </Section>

        <Section title="2. Descrição do Serviço">
          O BestPriceToday é um comparador de preços que agrega e exibe ofertas de produtos de marketplaces parceiros
          (como AliExpress, Shopee, Amazon e Lomadee) para fins informativos e de comparação. A Plataforma não vende
          produtos diretamente e não é responsável pelas transações realizadas nos sites de terceiros.
        </Section>

        <Section title="3. Links de Afiliados">
          Alguns links exibidos na Plataforma são links de afiliados. Isso significa que podemos receber uma comissão
          quando você realiza uma compra por meio de nossos links, sem custo adicional para você. Essa comissão é a
          principal fonte de receita da Plataforma e nos permite oferecer o serviço gratuitamente.
        </Section>

        <Section title="4. Precisão das Informações">
          Os preços, disponibilidades e condições exibidos são obtidos em tempo real de APIs de terceiros e podem
          não refletir o preço final no momento da compra. O BestPriceToday não garante a exatidão, integridade ou
          atualidade das informações exibidas. Sempre verifique o preço no site do vendedor antes de concluir a compra.
        </Section>

        <Section title="5. Uso Permitido">
          Você pode usar a Plataforma para:
          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li>Comparar preços de produtos</li>
            <li>Criar alertas de preço para uso pessoal</li>
            <li>Compartilhar links de ofertas com terceiros</li>
          </ul>
          É proibido:
          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li>Usar bots, scrapers ou automações para acessar a Plataforma sem autorização</li>
            <li>Tentar comprometer a segurança ou disponibilidade do serviço</li>
            <li>Reproduzir ou redistribuir o conteúdo da Plataforma com fins comerciais sem autorização</li>
          </ul>
        </Section>

        <Section title="6. Alertas de Preço">
          Ao criar um alerta de preço, você fornece voluntariamente informações de contato (como ID do Telegram).
          Essas informações são usadas exclusivamente para o envio de notificações de preço e não são compartilhadas
          com terceiros.
        </Section>

        <Section title="7. Isenção de Responsabilidade">
          A Plataforma é fornecida "como está", sem garantias de qualquer tipo. Não somos responsáveis por:
          <ul style={{ marginTop: 12, paddingLeft: 20, lineHeight: 2 }}>
            <li>Prejuízos decorrentes de preços incorretos ou produtos indisponíveis</li>
            <li>Problemas com pedidos, entregas ou devoluções nos sites de terceiros</li>
            <li>Indisponibilidade temporária do serviço</li>
          </ul>
        </Section>

        <Section title="8. Propriedade Intelectual">
          Todo o conteúdo original da Plataforma (design, código, textos e marca BestPriceToday) é protegido por
          direitos autorais e pertence aos seus criadores. Os dados de produtos são de propriedade dos respectivos
          marketplaces.
        </Section>

        <Section title="9. Modificações">
          Podemos atualizar estes Termos a qualquer momento. Alterações significativas serão comunicadas por aviso
          na Plataforma. O uso continuado após a publicação das alterações implica aceitação.
        </Section>

        <Section title="10. Lei Aplicável">
          Estes Termos são regidos pelas leis da República Federativa do Brasil. Eventuais disputas serão resolvidas
          no foro da comarca de São Paulo, SP.
        </Section>

        <Section title="11. Contato">
          Para dúvidas sobre estes Termos, entre em contato: <br />
          <a href="mailto:aletubegames@gmail.com"
             style={{ color: "var(--acc2)", textDecoration: "none" }}>
            aletubegames@gmail.com
          </a>
        </Section>

        <div style={{ marginTop: 48, paddingTop: 32, borderTop: "1px solid var(--bd)", display: "flex", gap: 24 }}>
          <a href="/privacy" style={{ fontSize: 13, color: "var(--muted2)", textDecoration: "none" }}>
            Política de Privacidade →
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
