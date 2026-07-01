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
];

export function getTestimonials(): Review[] {
  const now = new Date();
  const dayOfMon = now.getDate();
  // Rotação: 3 grupos de 6, cicla a cada ~10 dias
  const group = dayOfMon % 3;

  // Seleciona 6 dos 9, rotacionando grupos
  if (group === 0) return ALL_REVIEWS.slice(0, 6); // 0-5
  if (group === 1) return ALL_REVIEWS.slice(2, 8); // 2-7
  return ALL_REVIEWS.slice(3, 9); // 3-8
}
