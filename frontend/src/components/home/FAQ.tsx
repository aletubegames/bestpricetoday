"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { IconChevronDown } from "@tabler/icons-react";
import styles from "./FAQ.module.css";

interface FaqItem {
  q: string;
  a: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    q: "O preço aqui é maior do que na loja?",
    a: "Não. O link leva direto pra plataforma oficial pelo mesmo preço. Nunca cobramos nada a mais.",
  },
  {
    q: "Como vocês ganham dinheiro?",
    a: "Recebemos comissão da plataforma quando você compra pelo nosso link. Esse valor é pago pela loja, não por você.",
  },
  {
    q: "Os preços são atualizados em tempo real?",
    a: "Sim. Nossa busca roda automaticamente e exibe o preço atual de cada plataforma no momento da sua pesquisa.",
  },
  {
    q: "A compra é feita aqui no site?",
    a: "Não. Você é redirecionado para Shopee, Mercado Livre, AliExpress ou Lomadee e compra com toda a proteção e garantia delas.",
  },
  {
    q: "Vocês têm todos os produtos?",
    a: "Monitoramos mais de 10.000 produtos. Se não encontrar, tente termos diferentes ou volte em breve — adicionamos novos regularmente.",
  },
  {
    q: "É seguro comprar pelo link de vocês?",
    a: "Sim. Você compra diretamente na plataforma oficial. Nós apenas mostramos onde está mais barato.",
  },
];

function FaqAccordion({ item, isOpen, onToggle }: { item: FaqItem; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className={`${styles.item} ${isOpen ? styles.itemOpen : ""}`}>
      <button onClick={onToggle} className={styles.toggle}>
        <span className={styles.question}>
          {item.q}
        </span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.25 }}
          className={styles.icon}
        >
          <IconChevronDown size={20} stroke={2} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className={styles.content}
          >
            <p className={styles.answer}>
              {item.a}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div>
      <h2 className={styles.title}>
        Dúvidas frequentes
      </h2>

      <div className={styles.list}>
        {FAQ_ITEMS.map((item, i) => (
          <FaqAccordion
            key={i}
            item={item}
            isOpen={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? null : i)}
          />
        ))}
      </div>
    </div>
  );
}
