"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { IconChevronDown } from "@tabler/icons-react";

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
    <div
      style={{
        background: "#fff",
        border: `1px solid ${isOpen ? "#7c3aed" : "#e0e0f0"}`,
        borderRadius: 14,
        overflow: "hidden",
        transition: "border-color 0.2s",
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "16px 20px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 600, color: "#1a1a2e", flex: 1 }}>
          {item.q}
        </span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.25 }}
          style={{ color: "#7c3aed", flexShrink: 0, display: "flex" }}
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
            style={{ overflow: "hidden" }}
          >
            <p style={{ padding: "0 20px 16px", fontSize: 14, lineHeight: 1.7, color: "rgba(26,26,46,0.6)", margin: 0 }}>
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
      <h2 style={{
        fontFamily: "var(--font-syne), 'Syne', system-ui, sans-serif",
        fontSize: 28, fontWeight: 800, color: "#1a1a2e",
        textAlign: "center", marginBottom: 28,
      }}>
        Dúvidas frequentes
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 720, margin: "0 auto" }}>
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
