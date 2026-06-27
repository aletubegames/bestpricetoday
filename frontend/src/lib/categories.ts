/**
 * categories.ts — Configuração das páginas de categoria (hubs de nicho).
 *
 * Cada categoria mapeia para um slug URL (/categoria/[slug]) e contém:
 * - name: nome exibido
 * - description: para SEO/meta
 * - icon: emoji
 * - queries: queries populares do nicho (para buscar top produtos + links internos)
 * - related: categorias relacionadas (link juice interno)
 */

export interface CategoryConfig {
  slug: string
  name: string
  description: string
  icon: string
  queries: string[]
  related: string[]
}

export const CATEGORIES: CategoryConfig[] = [
  {
    slug: "celular",
    name: "Celulares e Smartphones",
    description: "Menores preços em iPhones, Samsung Galaxy, Xiaomi, Motorola e mais. Compare ofertas de celulares com cupons automáticos.",
    icon: "📱",
    queries: [
      "iphone-16-pro", "iphone-15", "samsung-galaxy-s25", "samsung-galaxy-a55",
      "redmi-note-13", "motorola-edge", "realme-c65", "poco-x6-pro",
      "iphone-14", "iphone-13", "samsung-galaxy-m55", "tablet-android",
    ],
    related: ["eletronicos", "games", "beleza"],
  },
  {
    slug: "games",
    name: "Games e Videogames",
    description: "PlayStation 5, Xbox Series X, Nintendo Switch, jogos e acessórios gamer com os menores preços do Brasil.",
    icon: "🎮",
    queries: [
      "playstation-5", "ps5-slim", "xbox-series-x", "xbox-series-s",
      "nintendo-switch", "controle-ps5", "controle-xbox", "jogo-ps5",
      "jogo-xbox", "notebook-gamer", "cadeira-gamer", "mouse-gamer",
      "headset-gamer", "teclado-mecanico", "monitor-gamer-144hz", "volante-gamer",
    ],
    related: ["eletronicos", "celular"],
  },
  {
    slug: "casa",
    name: "Casa e Eletrodomésticos",
    description: "Airfryer, geladeira, máquina de lavar, ar condicionado e tudo para sua casa com os melhores preços.",
    icon: "🏠",
    queries: [
      "airfryer", "airfryer-philips", "ar-condicionado-split", "geladeira-brastemp",
      "geladeira-electrolux", "maquina-de-lavar", "lava-e-seca", "microondas",
      "fogao-4-bocas", "aspirador-robo", "liquidificador", "cafeteira-express",
      "lava-louca", "panela-eletrica", "ventilador-de-teto", "umidificador-de-ar",
    ],
    related: ["beleza", "ferramentas", "pet"],
  },
  {
    slug: "beleza",
    name: "Beleza e Cuidados",
    description: "Secador, prancha, perfumes importados, skincare e maquiagem com cupons automáticos aplicados.",
    icon: "💄",
    queries: [
      "secador-cabelo", "prancha-cabelo", "escova-rotativa", "kit-maquiagem",
      "perfume-importado", "perfume-feminino", "perfume-masculino",
      "creme-facial", "serum-vitamina-c", "protetor-solar-fps50",
      "barbeador-philips", "escova-dente-eletrica", "tratamento-cabelo",
    ],
    related: ["casa", "moda", "celular"],
  },
  {
    slug: "ferramentas",
    name: "Ferramentas e Construção",
    description: "Furadeira, parafusadeira, conjuntos de ferramentas e equipamentos para construção com menores preços.",
    icon: "🔧",
    queries: [
      "furadeira-impacto", "parafusadeira", "lixadeira-orbital", "martelo-rotativo",
      "conjunto-ferramentas", "caixa-ferramentas", "kit-ferramentas-jardim",
      "cortador-grama", "aparador-grama", "churrasqueira-carvao",
    ],
    related: ["casa", "auto", "esportes"],
  },
  {
    slug: "eletronicos",
    name: "Eletrônicos e Informática",
    description: "Notebooks, placas de vídeo, monitores, SSDs, fones e acessórios de informática com os melhores preços.",
    icon: "💻",
    queries: [
      "notebook-gamer", "notebook-dell", "notebook-lenovo", "macbook-air",
      "rtx-4070", "rtx-4060", "placa-de-video", "ssd-nvme-1tb",
      "monitor-gamer-144hz", "monitor-27-polegadas", "teclado-mecanico",
      "mouse-gamer", "airpods-pro", "galaxy-buds", "jbl-flip-6",
      "smart-tv-55", "roteador-wifi-6", "hd-externo-2tb",
    ],
    related: ["celular", "games"],
  },
  {
    slug: "moda",
    name: "Moda e Acessórios",
    description: "Tênis, roupas, relógios, óculos e bolsas com cupons automáticos nas melhores lojas.",
    icon: "👟",
    queries: [
      "tenis-nike", "tenis-adidas", "tenis-corrida", "tenis-masculino",
      "tenis-feminino", "mochila-notebook", "relogio-smartwatch", "apple-watch",
      "oculos-de-sol", "bolsa-feminina", "carteira-masculina", "blusa-feminina",
      "vestido-longo", "calca-jeans-masculina", "jaqueta-jeans",
    ],
    related: ["beleza", "esportes", "celular"],
  },
  {
    slug: "esportes",
    name: "Esportes e Fitness",
    description: "Bicicletas, esteiras, halteres, equipamentos de ginástica e artigos esportivos com menores preços.",
    icon: "⚽",
    queries: [
      "bicicleta-mtb", "esteira-eletrica", "halteres-ajustaveis", "banco-musculacao",
      "peso-de-mao", "patins-rodas", "skate-profissional", "bola-futebol",
      "bola-basquete", "raquete-tenis", "mochila-escolar",
    ],
    related: ["moda", "games", "casa"],
  },
  {
    slug: "pet",
    name: "Pet Shop",
    description: "Ração, areia, camas, brinquedos e acessórios para cachorros, gatos e outros pets com cupons automáticos.",
    icon: "🐕",
    queries: [
      "racao-15kg", "racao-golden", "areia-gato", "arranhador-gato",
      "coleira-cachorro", "cama-pet", "brinquedo-cachorro", "racao-premium",
      "racao-para-gato", "aquario-60l", "comedouro-automatico",
    ],
    related: ["casa", "beleza"],
  },
  {
    slug: "bebe",
    name: "Bebê e Infantil",
    description: "Carrinho de bebê, cadeira auto, fraldas, mamadeiras e tudo para o seu bebê com os melhores preços.",
    icon: "👶",
    queries: [
      "carrinho-de-bebe", "cadeira-auto", "berco-portatil", "mamadeira-anticolica",
      "chupeta", "fralda-pampers", "mochila-escolar-infantil", "livro-infantil",
    ],
    related: ["casa", "beleza", "moda"],
  },
]

export const CATEGORY_MAP: Record<string, CategoryConfig> = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c])
)

export function getCategory(slug: string): CategoryConfig | undefined {
  return CATEGORY_MAP[slug]
}

export function getAllCategorySlugs(): string[] {
  return CATEGORIES.map(c => c.slug)
}
