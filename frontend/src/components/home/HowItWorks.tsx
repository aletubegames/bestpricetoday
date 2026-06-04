"use client";

import { motion } from "framer-motion";

const STEPS = [
  {
    emoji: "🔍",
    title: "Busque",
    text: "Digite o produto que você quer. A gente busca em Mercado Livre, Amazon, Shopee, AliExpress e mais.",
    color: "#7c3aed",
  },
  {
    emoji: "⚖️",
    title: "Compare",
    text: "Veja lado a lado preços, cupons, frete e score de oferta. Tudo em segundos, sem abrir 10 abas.",
    color: "#f97316",
  },
  {
    emoji: "🛒",
    title: "Compre",
    text: "Clique e vá direto pra loja oficial. Sem cadastro, sem taxas escondidas. Você só economiza.",
    color: "#00b894",
  },
];

export default function HowItWorks() {
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
        Como funciona
      </h2>
      <p style={{ fontSize: 14, color: "rgba(26,26,46,0.5)", marginBottom: 32 }}>
        Menos de 5 segundos pra achar o menor preço do Brasil
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 20,
        }}
      >
        {STEPS.map((step, i) => (
          <motion.div
            key={step.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1, duration: 0.4 }}
            style={{
              background: "#fff",
              border: "1px solid #e0e0f0",
              borderRadius: 16,
              padding: "28px 20px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: `${step.color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 26,
                margin: "0 auto 16px",
              }}
            >
              {step.emoji}
            </div>
            <div
              style={{
                fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
                fontSize: 18,
                fontWeight: 800,
                color: step.color,
                marginBottom: 6,
              }}
            >
              {step.title}
            </div>
            <p
              style={{
                fontSize: 13,
                lineHeight: 1.6,
                color: "rgba(26,26,46,0.55)",
                margin: 0,
              }}
            >
              {step.text}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
