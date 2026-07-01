"use client";

import { motion } from "framer-motion";
import { IconChartLine, IconBell, IconShieldCheck, IconBolt } from "@tabler/icons-react";

const REASONS = [
  {
    icon: <IconChartLine size={28} stroke={1.5} />,
    title: "Histórico de preços",
    text: "Sabe aquele \"de R$ 999 por R$ 499\" que nunca custou 999? A gente acompanha o preço real e te mostra se a oferta é de verdade.",
    color: "#7c3aed",
  },
  {
    icon: <IconBell size={28} stroke={1.5} />,
    title: "Alertas de queda",
    text: "Quer esperar mais um pouco? Crie um alerta e te avisamos quando o preço cair. Sem precisar ficar olhando todo dia.",
    color: "#f97316",
  },
  {
    icon: <IconShieldCheck size={28} stroke={1.5} />,
    title: "Sem promoção fake",
    text: "Cada oferta tem um score real baseado no histórico. Se o desconto for furado, a gente te avisa antes de clicar.",
    color: "#00b894",
  },
  {
    icon: <IconBolt size={28} stroke={1.5} />,
    title: "Comparação em segundos",
    text: "Mercado Livre, Amazon, Shopee, AliExpress e mais — tudo lado a lado, frete e tudo. Sem abrir 10 abas.",
    color: "#1a1a2e",
  },
];

export default function WhyUs() {
  return (
    <div style={{ textAlign: "center" }}>
      <h2
        style={{
          fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
          fontSize: 26,
          fontWeight: 800,
          color: "#1a1a2e",
          marginBottom: 6,
        }}
      >
        Por que usar o BestPriceToday?
      </h2>
      <p style={{ fontSize: 14, color: "rgba(26,26,46,0.5)", marginBottom: 32 }}>
        Economia de verdade — não &quot;metade do dobro&quot;
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 20,
        }}
      >
        {REASONS.map((r, i) => (
          <motion.div
            key={r.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1, duration: 0.4 }}
            style={{
              background: "#fff",
              border: "1px solid #e0e0f0",
              borderRadius: 16,
              padding: "28px 22px",
              textAlign: "left",
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: `${r.color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: r.color,
                margin: "0 auto 16px",
              }}
            >
              {r.icon}
            </div>
            <div
              style={{
                fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
                fontSize: 17,
                fontWeight: 800,
                color: r.color,
                marginBottom: 8,
                textAlign: "center",
              }}
            >
              {r.title}
            </div>
            <p
              style={{
                fontSize: 13,
                lineHeight: 1.6,
                color: "rgba(26,26,46,0.6)",
                margin: 0,
              }}
            >
              {r.text}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
