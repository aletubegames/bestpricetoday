/**
 * mockData.ts — D server-side com variação diária via semente (data atual).
 * Nenhum fetch, nenhuma API, nenhum banco. Zero hydration mismatch.
 */

function dayOfYear(d: Date): number {
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

function seededRandom(seed: number): () => number {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function getTodaySeed(): number {
  const now = new Date();
  return now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
}

// ─── Stats ─────────────────────────────────────────────────────────────────────

export interface Stats {
  productsMonitored: number;
  weeklySearches: number;
  platforms: number;
}

export function getStats(): Stats {
  const now = new Date();
  const day = now.getDate();
  const rand = seededRandom(getTodaySeed());

  // Base + incremento diário orgânico
  const productsBase = 9800;
  const productsDaily = 50 + Math.floor(rand() * 100); // 50–150 por dia do mês
  const productsMonitored = productsBase + day * productsDaily;

  const searchesBase = 5800;
  const searchesDaily = 200 + Math.floor(rand() * 400); // 200–600 por dia
  const weeklySearches = searchesBase + day * searchesDaily;

  return {
    productsMonitored,
    weeklySearches,
    platforms: 5,
  };
}

// ─── Chart ─────────────────────────────────────────────────────────────────────

export interface ChartDay {
  day: string;
  value: number;
}

const DAY_LABELS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

export function getChartData(): ChartDay[] {
  const now = new Date();
  const rand = seededRandom(getTodaySeed() + 7); // semente diferente dos stats

  const days: ChartDay[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const idx = 6 - i; // 0..6
    // Valor entre 1200 e 2000, orgânico
    const value = 1200 + Math.floor(rand() * 800);
    days.push({
      day: DAY_LABELS[d.getDay()],
      value,
    });
  }
  return days;
}

// ─── Testimonials ──────────────────────────────────────────────────────────────

export interface Review {
  initials: string;
  name: string;
  state: string;
  stars: number;
  text: string;
  savings: string;
  productTag: string;
  avatarColor: string;
}

const ALL_REVIEWS: Review[] = [
  {
    initials: "MF",
    name: "Mariana F.",
    state: "SP",
    stars: 5,
    text: "Achei um fone bluetooth JBL por um preço absurdo de baixo. Chegou rápido e funcionou perfeito!",
    savings: "R$ 55",
    productTag: "Fone Bluetooth JBL",
    avatarColor: "#7c3aed",
  },
  {
    initials: "RC",
    name: "Rafael C.",
    state: "MG",
    stars: 5,
    text: "Já comprei três coisas pelo site. A air fryer de 5L veio R$ 98 mais barato que na loja. Recomendo demais!",
    savings: "R$ 98",
    productTag: "Air Fryer 5L",
    avatarColor: "#f97316",
  },
  {
    initials: "JS",
    name: "Juliana S.",
    state: "PR",
    stars: 5,
    text: "Uso toda semana. Os preços realmente são mais baixos e eu confio porque compra direto na plataforma oficial.",
    savings: "R$ 210+",
    productTag: "Diversos produtos",
    avatarColor: "#00b894",
  },
  {
    initials: "TM",
    name: "Thiago M.",
    state: "PE",
    stars: 5,
    text: "O teclado mecânico Redragon que eu queria há meses apareceu R$ 67 mais barato. Melhor investimento que fiz.",
    savings: "R$ 67",
    productTag: "Teclado Mecânico Redragon",
    avatarColor: "#e74c3c",
  },
  {
    initials: "LC",
    name: "Larissa C.",
    state: "CE",
    stars: 5,
    text: "Câmera de segurança que eu pesquisava estava R$ 80 mais caro em todo lugar. Aqui achei o melhor preço fácil.",
    savings: "R$ 80",
    productTag: "Câmera de Segurança",
    avatarColor: "#f59e0b",
  },
  {
    initials: "PB",
    name: "Paulo B.",
    state: "RS",
    stars: 4,
    text: "Notebook Dell i5 com R$ 210 de economia! Só queria que tivesse mais categorias, mas o que tem é ótimo.",
    savings: "R$ 210",
    productTag: "Notebook Dell i5",
    avatarColor: "#8b5cf6",
  },
  {
    initials: "CA",
    name: "Carlos A.",
    state: "RJ",
    stars: 5,
    text: "Smartwatch que eu queria custava R$ 380 na loja. Pelo BestPriceToday achei por R$ 237. Economia real!",
    savings: "R$ 143",
    productTag: "Smartwatch",
    avatarColor: "#ef4444",
  },
  {
    initials: "FL",
    name: "Fernanda L.",
    state: "GO",
    stars: 5,
    text: "Aspirador robô por menos da metade do preço! Minha vida mudou. Todo mundo em casa.",
    savings: "R$ 189",
    productTag: "Aspirador Robô",
    avatarColor: "#10b981",
  },
  {
    initials: "BT",
    name: "Bruno T.",
    state: "BA",
    stars: 5,
    text: "Monitor gamer 27\" que eu estava de olho caiu R$ 320. Comprei sem pensar duas vezes.",
    savings: "R$ 320",
    productTag: "Monitor Gamer 27\"",
    avatarColor: "#3b82f6",
  },
  {
    initials: "GP",
    name: "Gabriel P.",
    state: "SC",
    stars: 5,
    text: "Película de vidro para celular com cupom saiu de graça praticamente. Paguei só o frete.",
    savings: "R$ 25",
    productTag: "Película Vidro",
    avatarColor: "#6366f1",
  },
  {
    initials: "AM",
    name: "Ana M.",
    state: "PA",
    stars: 5,
    text: "Ar-condicionado 9.000 BTUs por R$ 450 a menos. Entrega foi direto da loja oficial, super seguro.",
    savings: "R$ 450",
    productTag: "Ar-condicionado 9.000 BTUs",
    avatarColor: "#06b6d4",
  },
  {
    initials: "DO",
    name: "Diego O.",
    state: "ES",
    stars: 4,
    text: "Bicicleta aro 29 com R$ 180 de desconto. A única coisa que não gostei foi que demorou um pouco pra atualizar o preço.",
    savings: "R$ 180",
    productTag: "Bicicleta Aro 29",
    avatarColor: "#84cc16",
  },
  {
    initials: "RS",
    name: "Renata S.",
    state: "DF",
    stars: 5,
    text: "Máquina de café que eu queria custava R$ 1.200. Aqui achei por R$ 890 com cupom. Sensacional!",
    savings: "R$ 310",
    productTag: "Máquina de Café",
    avatarColor: "#d946ef",
  },
  {
    initials: "NG",
    name: "Nicolas G.",
    state: "MT",
    stars: 5,
    text: "SSD 1TB NVMe com R$ 90 de economia. Agora meu PC voa. Muito obrigado BestPriceToday!",
    savings: "R$ 90",
    productTag: "SSD 1TB NVMe",
    avatarColor: "#14b8a6",
  },
  {
    initials: "VR",
    name: "Valentina R.",
    state: "SE",
    stars: 5,
    text: "Secador de cabelo profissional com R$ 120 de desconto. Produto original, nota fiscal tudo certo.",
    savings: "R$ 120",
    productTag: "Secador Profissional",
    avatarColor: "#f43f5e",
  },
  {
    initials: "HP",
    name: "Henrique P.",
    state: "PB",
    stars: 5,
    text: "Controle de videogame original com R$ 70 de desconto. Já economizei mais de R$ 500 no ano.",
    savings: "R$ 500+",
    productTag: "Controle PS5",
    avatarColor: "#8b5cf6",
  },
  {
    initials: "IS",
    name: "Isabela S.",
    state: "RN",
    stars: 5,
    text: "Impressora multifuncional com R$ 160 de desconto. Indico pra todo mundo que pergunta onde comprar barato.",
    savings: "R$ 160",
    productTag: "Impressora Multifuncional",
    avatarColor: "#0ea5e9",
  },
  {
    initials: "MO",
    name: "Miguel O.",
    state: "AL",
    stars: 4,
    text: "Geladeira com R$ 600 de desconto. A diferença pagou a instalação. Só acho que poderia ter mais marcas de eletro.",
    savings: "R$ 600",
    productTag: "Geladeira",
    avatarColor: "#a855f7",
  },
  {
    initials: "CS",
    name: "Camila S.",
    state: "PI",
    stars: 5,
    text: "Cadeira ergonômica com R$ 230 de desconto. Trabalho em casa ficou muito melhor. Valeu a dica!",
    savings: "R$ 230",
    productTag: "Cadeira Ergonômica",
    avatarColor: "#ec4899",
  },
  {
    initials: "LP",
    name: "Lucas P.",
    state: "AM",
    stars: 5,
    text: "Tablet pra minha filha com R$ 280 de desconto. Comprei no dia certo e ainda usei um cupom.",
    savings: "R$ 280",
    productTag: "Tablet Infantil",
    avatarColor: "#22c55e",
  },
];

export function getTestimonials(): Review[] {
  const now = new Date();
  const day = dayOfYear(now);
  // Mostra 9 depoimentos por dia, deslizando a janela ao longo dos 21 disponíveis
  const windowSize = 9;
  const start = day % Math.max(1, ALL_REVIEWS.length - windowSize + 1);
  return ALL_REVIEWS.slice(start, start + windowSize);
}
