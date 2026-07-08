"use client";

import { motion } from "framer-motion";
import styles from "./HowItWorks.module.css";

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
    text: "Veja lado a lado preços, frete, histórico e score de oferta. Tudo em segundos, sem abrir 10 abas.",
    color: "#f97316",
  },
  {
    emoji: "🛒",
    title: "Compre",
    text: "Clique e vá direto pra loja oficial. Sem cadastro, sem taxas escondidas. Você só economiza.",
    color: "#1a1a2e",
  },
];

export default function HowItWorks() {
  return (
    <div className={styles.root}>
      <h2 className={styles.title}>
        Como funciona
      </h2>
      <p className={styles.subtitle}>
        Menos de 5 segundos pra achar o menor preço do Brasil
      </p>

      <div className={styles.grid}>
        {STEPS.map((step, i) => (
          <motion.div
            key={step.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1, duration: 0.4 }}
            className={styles.card}
          >
            <div className={styles.iconWrap} style={{ background: `${step.color}15` }}>
              {step.emoji}
            </div>
            <div className={styles.stepTitle} style={{ color: step.color }}>
              {step.title}
            </div>
            <p className={styles.text}>
              {step.text}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
