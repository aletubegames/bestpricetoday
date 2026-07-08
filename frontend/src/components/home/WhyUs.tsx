"use client";

import { motion } from "framer-motion";
import { IconChartLine, IconBell, IconShieldCheck, IconBolt } from "@tabler/icons-react";
import styles from "./WhyUs.module.css";

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
    <div className={styles.root}>
      <h2 className={styles.title}>
        Por que usar o BestPriceToday?
      </h2>
      <p className={styles.subtitle}>
        Economia de verdade — não &quot;metade do dobro&quot;
      </p>

      <div className={styles.grid}>
        {REASONS.map((r, i) => (
          <motion.div
            key={r.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1, duration: 0.4 }}
            className={styles.card}
          >
            <div className={styles.iconWrap} style={{ background: `${r.color}15`, color: r.color }}>
              {r.icon}
            </div>
            <div className={styles.cardTitle} style={{ color: r.color }}>
              {r.title}
            </div>
            <p className={styles.text}>
              {r.text}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
