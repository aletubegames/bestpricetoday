"use client";

import { motion } from "framer-motion";
import { useState, useEffect, useMemo } from "react";
import { useTrendingSearches } from "@/hooks/useTrendingSearches";
import { API_BASE } from "@/lib/api";
import styles from "./FeaturedOffers.module.css";

const CATEGORIES = [
  { label: "📱 Celulares", query: "celular", color: "#f97316" },
  { label: "💻 Eletrônicos", query: "eletrônicos", color: "#f97316" },
  { label: "🏠 Casa", query: "casa e cozinha", color: "#f97316" },
  { label: "🎮 Games", query: "games", color: "#f97316" },
  { label: "👕 Moda", query: "moda", color: "#f97316" },
  { label: "🏋️ Esportes", query: "esportes", color: "#f97316" },
  { label: "📚 Livros", query: "livros", color: "#f97316" },
  { label: "🐾 Pets", query: "pets", color: "#f97316" },
];

const FALLBACK_PRODUCTS = [
  { emoji: "🎧", query: "fone bluetooth jbl" },
  { emoji: "🍟", query: "air fryer 5l" },
  { emoji: "⌚", query: "smartwatch xiaomi" },
  { emoji: "⌨️", query: "teclado mecânico redragon" },
  { emoji: "🖥️", query: "monitor gamer 27" },
  { emoji: "🤖", query: "aspirador robô" },
  { emoji: "📱", query: "iphone 16" },
  { emoji: "💡", query: "lâmpada smart" },
  { emoji: "🎮", query: "controle ps5" },
  { emoji: "📷", query: "câmera segurança" },
  { emoji: "🔊", query: "caixa de som bluetooth" },
  { emoji: "🖨️", query: "impressora multifuncional" },
];

// Mapeia palavras-chave → emoji. Ordem importa: primeira match vence.
const EMOJI_RULES: { keywords: string[]; emoji: string }[] = [
  { keywords: ["iphone", "celular", "smartphone", "redmi", "galaxy", "motorola", "poco", "xiaomi phone"], emoji: "📱" },
  { keywords: ["air fryer", "airfryer", "fritadeira"], emoji: "🍟" },
  { keywords: ["fone", "headphone", "earbud", "tws", "bluetooth fone", "jbl", "airpod"], emoji: "🎧" },
  { keywords: ["smartwatch", "relogio", "relógio", "band", "watch"], emoji: "⌚" },
  { keywords: ["teclado", "keyboard"], emoji: "⌨️" },
  { keywords: ["mouse"], emoji: "🖱️" },
  { keywords: ["monitor", "tela", "display"], emoji: "🖥️" },
  { keywords: ["notebook", "laptop", "ultrabook", "chromebook"], emoji: "💻" },
  { keywords: ["ps5", "playstation", "controle", "xbox", "nintendo", "switch", "game", "jogo", "gamer"], emoji: "🎮" },
  { keywords: ["aspirador", "robô", "robo"], emoji: "🤖" },
  { keywords: ["lâmpada", "lampada", "smart light", "luz smart"], emoji: "💡" },
  { keywords: ["câmera", "camera", "segurança", "security", "dvr"], emoji: "📷" },
  { keywords: ["caixa de som", "caixa som", "speaker", "soundbar", "jbl"], emoji: "🔊" },
  { keywords: ["impressora", "printer", "multifuncional"], emoji: "🖨️" },
  { keywords: ["tv", "smart tv", "led", "oled", "qled"], emoji: "📺" },
  { keywords: ["tablet", "ipad", "kindle"], emoji: "📋" },
  { keywords: ["drone"], emoji: "🚁" },
  { keywords: ["bike", "bicicleta", "mtb", "caloi", "monark"], emoji: "🚲" },
  { keywords: ["pelicula", "película", "tempered", "capa", "case", "cover"], emoji: "🛡️" },
  { keywords: ["carregador", "charger", "cabo", "usb", "fonte"], emoji: "🔌" },
  { keywords: ["ssd", "hd", "disco", "armazenamento", "pendrive", "memoria"], emoji: "💾" },
  { keywords: ["rtx", "placa de video", "gpu", "geforce", "radeon"], emoji: "🎮" },
  { keywords: ["processador", "ryzen", "intel", "cpu"], emoji: "⚙️" },
  { keywords: ["cadeira", "chair", "gamer cadeira"], emoji: "🪑" },
  { keywords: ["café", "cafe", "cafeteira", "expresso"], emoji: "☕" },
  { keywords: ["ventilador", "ar condicionado", "climatizador"], emoji: "🌀" },
  { keywords: ["geladeira", "refrigerador", "freezer", "frigobar"], emoji: "🧊" },
  { keywords: ["lava", "maquina de lavar", "lavadora", "secadora"], emoji: "🧺" },
  { keywords: ["microondas", "forno"], emoji: "🔥" },
  { keywords: ["bicicleta", "bike"], emoji: "🚲" },
  { keywords: ["ferramenta", "martelo", "furadeira", "parafusadeira", "serra"], emoji: "🔧" },
  { keywords: ["batedeira", "liquidificador", "mixer"], emoji: "🥤" },
  { keywords: ["cama", "colchão", "colchonete", "travesseiro"], emoji: "🛏️" },
  { keywords: ["mesa", "mesa escritorio", "escrivaninha"], emoji: "🪵" },
  { keywords: ["câmera foto", "dslr", "mirrorless", "gopro"], emoji: "📸" },
  { keywords: ["power bank", "powerbank", "bateria portatil"], emoji: "🔋" },
  { keywords: ["roteador", "router", "wifi", "mesh"], emoji: "📡" },
  { keywords: ["hdmi", "cabo hdmi", "adaptador"], emoji: "🔌" },
  { keywords: ["suporte", "suporte tv", "suporte celular", "mochila", "bag"], emoji: "🎒" },
  { keywords: ["shaver", "barbeador", "depilador", "cuidado pessoal"], emoji: "🪒" },
  { keywords: ["perfume", "fragrância", "colonha"], emoji: "🌸" },
  { keywords: ["tênis", "tenis", "sapato", "calça", "camisa", "roupa"], emoji: "👟" },
  { keywords: ["livro", "book", "kindle book"], emoji: "📚" },
  { keywords: ["pet", "cachorro", "gato", "ração", "cama pet"], emoji: "🐾" },
  { keywords: ["brinquedo", "toy", "lego", "boneco", "carrinho"], emoji: "🧸" },
  { keywords: ["bebe", "bebê", "fralda", "chupeta", "mamadeira"], emoji: "🍼" },
  { keywords: ["suplemento", "whey", "creatina", "proteina", "vitamina"], emoji: "💊" },
  { keywords: ["raquete", "tenis mesa", "ping pong", "futebol", "bola"], emoji: "⚽" },
  { keywords: ["violão", "violao", "guitarra", "teclado musical", "instrumento"], emoji: "🎸" },
  { keywords: ["pneu", "roda", "automotivo", "óleo motor", "oleo motor"], emoji: "🚗" },
  { keywords: ["capacete", "moto", "motocicleta"], emoji: "🏍️" },
];

function inferEmoji(query: string): string {
  const q = query.toLowerCase();
  for (const rule of EMOJI_RULES) {
    if (rule.keywords.some((kw) => q.includes(kw))) {
      return rule.emoji;
    }
  }
  return "🏷️"; // emoji genérico de oferta
}

const BRAND_COLORS = ["#7c3aed", "#f97316", "#1a1a2e", "#ec7000", "#8b5cf6", "#ea580c"];

interface ProductItem {
  emoji: string;
  query: string;
  label: string;
  color: string;
}

export default function FeaturedOffers({ onSearch }: { onSearch: (q: string) => void }) {
  const { data: trendingData } = useTrendingSearches(20);
  const [couponCount, setCouponCount] = useState(0);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/affiliate/coupons?active_only=true&limit=1`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d?.total ? setCouponCount(d.total) : null)
      .catch(() => {});
  }, []);

  const products: ProductItem[] = useMemo(() => {
    const items = trendingData?.items ?? [];
    if (items.length >= 6) {
      // Use trending items dynamically — emoji inferido pelo título/query
      return items.slice(0, 12).map((item, i) => ({
        emoji: inferEmoji(item.query),
        query: item.query,
        label: item.query.length > 28 ? item.query.slice(0, 28) + "…" : item.query,
        color: BRAND_COLORS[i % BRAND_COLORS.length],
      }));
    }
    // Fallback: rotate through fixed list
    return FALLBACK_PRODUCTS.map((p, i) => ({
      ...p,
      label: p.query,
      color: BRAND_COLORS[i % BRAND_COLORS.length],
    }));
  }, [trendingData]);

  return (
    <div className={styles.root}>
      {/* ── Featured Products ── */}
      <h2 className={styles.title}>
        <span className={styles.titleAccent}>Ofertas</span> em destaque
      </h2>
      <p className={styles.subtitle}>
        Produtos com maior economia agora. Clique pra ver o preço em tempo real.
      </p>

      {couponCount > 0 && (
        <a href="/cupons" className={styles.couponBanner}>
          <span className={styles.couponIcon}>🏷️</span>
          <span className={styles.couponText}>
            {couponCount} cupom{couponCount > 1 ? "s" : ""} ativo{couponCount > 1 ? "s" : ""} agora — ver produtos com desconto!
          </span>
          <span className={styles.couponArrow}>→</span>
        </a>
      )}

      <div className={styles.grid}>
        {products.map((product, i) => (
          <motion.button
            key={product.query + i}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.04 + i * 0.04, duration: 0.3 }}
            onClick={() => onSearch(product.query)}
            className={styles.card}
          >
            <span className={styles.cardEmoji}>{product.emoji}</span>
            <div className={styles.cardLabel}>
              {product.label}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
