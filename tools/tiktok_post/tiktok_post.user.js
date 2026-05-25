// ==UserScript==
// @name         Bot TikTok Fiel v10
// @namespace    http://tampermonkey.net/
// @version      10.0
// @description  Bot TikTok com retry, confirmacao de publicacao, XPath flexivel
// @author       Alessandro
// @match        https://www.tiktok.com/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(async () => {
    if (window.__tt_bot_running__) return;
    window.__tt_bot_running__ = true;

    const PK = 'tt_progress';
    const SK = 'tt_state';
    const LISTA = [
  {
    "slug": "AAEFn6fYRx",
    "video": "AAEFn6fYRx.mp4",
    "offer_link": "https://s.shopee.com.br/AAEFn6fYRx",
    "caption": "1/2/3 Cola Calçados Cola Pra Conserto De Sapatos Cola Para Conserto De Sapatos R\nOferta Especial: R$11,98\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "AKXfzPev70",
    "video": "AKXfzPev70.mp4",
    "offer_link": "https://s.shopee.com.br/AKXfzPev70",
    "caption": "Moletom Canguru Masculino Banda Stray Kids Blusa de Frio Premium Casaco Inverno \nOferta Especial: R$99,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8ATBPQnAVd",
    "video": "8ATBPQnAVd.mp4",
    "offer_link": "https://s.shopee.com.br/8ATBPQnAVd",
    "caption": "3 / 6 / 9 / 12 / 18 / 24 Pares de Meias Femininas Soquete Cano Curto Estampadas \nOferta Especial: R$12,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8KmbbjmXAg",
    "video": "8KmbbjmXAg.mp4",
    "offer_link": "https://s.shopee.com.br/8KmbbjmXAg",
    "caption": "Moletom Canguru Masculino Exclusiva Aranha Streetwear Algodão Premium Blusa de F\nOferta Especial: R$99,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8fPS0LlGUm",
    "video": "8fPS0LlGUm.mp4",
    "offer_link": "https://s.shopee.com.br/8fPS0LlGUm",
    "caption": "Mochila Bolsa Reforçada Notebook Resistente Trabalho Faculdade Coreana\nOferta Especial: R$31,5\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8pisCekd9p",
    "video": "8pisCekd9p.mp4",
    "offer_link": "https://s.shopee.com.br/8pisCekd9p",
    "caption": "Meia Grossa Térmica de Lã com Sola Antiderrapante Unissex Criança e Adulto Quent\nOferta Especial: R$12,59\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "902IOxjzos",
    "video": "902IOxjzos.mp4",
    "offer_link": "https://s.shopee.com.br/902IOxjzos",
    "caption": "Moletom Canguru Feminino Stray Kids Banda Kpop Skz Skzoo Unissex Premium Blusa d\nOferta Especial: R$99,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "9ALibGjMTv",
    "video": "9ALibGjMTv.mp4",
    "offer_link": "https://s.shopee.com.br/9ALibGjMTv",
    "caption": "Kit 3 Gel Sebo de Carneiro Hidratante Pele Renovada Nati Corporal Pés + Necessai\nOferta Especial: R$14,95\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6pxnoysFDV",
    "video": "6pxnoysFDV.mp4",
    "offer_link": "https://s.shopee.com.br/6pxnoysFDV",
    "caption": "Base BB Cream Cushion /Corretivo com Esponja co Formato de Cogumelo  Base Clarea\nOferta Especial: R$24,88\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "70HE1HrbsY",
    "video": "70HE1HrbsY.mp4",
    "offer_link": "https://s.shopee.com.br/70HE1HrbsY",
    "caption": "Moletom Canguru Masculino Estampado Skyline Gtr R34  Blusa De Frio Premium Carro\nOferta Especial: R$99,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7AaeDaqyXb",
    "video": "7AaeDaqyXb.mp4",
    "offer_link": "https://s.shopee.com.br/7AaeDaqyXb",
    "caption": "Kit 6 e 12 Pares de Meias Masculino para Recém Nascidos e Bebê Menino c/ Antider\nOferta Especial: R$15,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7Ku4PtqLCe",
    "video": "7Ku4PtqLCe.mp4",
    "offer_link": "https://s.shopee.com.br/7Ku4PtqLCe",
    "caption": "Kit com 5 - Lenço Umedecido Turminha da Bagunça Toalha Umedecida 48 Unidades\nOferta Especial: R$18,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7fWuoVp4Wk",
    "video": "7fWuoVp4Wk.mp4",
    "offer_link": "https://s.shopee.com.br/7fWuoVp4Wk",
    "caption": "Maquiagem junina adesiva, autocolante  kit 1 maquiagem completa contendo, 2 band\nOferta Especial: R$19,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7pqL0ooRBn",
    "video": "7pqL0ooRBn.mp4",
    "offer_link": "https://s.shopee.com.br/7pqL0ooRBn",
    "caption": "Meia-Calça Térmica Feminina Peluciada Translúcida Alta Elasticidade Super Quente\nOferta Especial: R$21,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "5q5Gd8w3FT",
    "video": "5q5Gd8w3FT.mp4",
    "offer_link": "https://s.shopee.com.br/5q5Gd8w3FT",
    "caption": "Kit 12 Pares de Meia Cano Alto\nOferta Especial: R$10,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "60OgpRvPuW",
    "video": "60OgpRvPuW.mp4",
    "offer_link": "https://s.shopee.com.br/60OgpRvPuW",
    "caption": "Protetor De Sapato Impermeável De Silicone Capa de Chuva Para Tênis Colorido e U\nOferta Especial: R$11,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6Ai71kumZZ",
    "video": "6Ai71kumZZ.mp4",
    "offer_link": "https://s.shopee.com.br/6Ai71kumZZ",
    "caption": "Moletom Canguru Masculino Estampa Capivara Milk Fofa Tumblr Com Capuz Casaco Blu\nOferta Especial: R$99,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6L1XE3u9Ec",
    "video": "6L1XE3u9Ec.mp4",
    "offer_link": "https://s.shopee.com.br/6L1XE3u9Ec",
    "caption": "Calça Feminina TACTEL COM ELASTANO PREMIUM jogger / ideal para academia,yoga, ca\nOferta Especial: R$36,49\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "4Ax2e52OdF",
    "video": "4Ax2e52OdF.mp4",
    "offer_link": "https://s.shopee.com.br/4Ax2e52OdF",
    "caption": "NOVA Luva motoqueiro inverno Frio Touch Screen  Motociclista Cano longo Adequado\nOferta Especial: R$8,2\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "4LGSqO1lII",
    "video": "4LGSqO1lII.mp4",
    "offer_link": "https://s.shopee.com.br/4LGSqO1lII",
    "caption": "Cola adesiva forte para sapatos - para reparação de calçado, soluções de reparaç\nOferta Especial: R$14,97\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "4ftJF00UcO",
    "video": "4ftJF00UcO.mp4",
    "offer_link": "https://s.shopee.com.br/4ftJF00UcO",
    "caption": "Blusa Manga Longa Feminina moda fitness modeladora  yoga casaco academia proteçã\nOferta Especial: R$44,47\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "50W9dbzDwU",
    "video": "50W9dbzDwU.mp4",
    "offer_link": "https://s.shopee.com.br/50W9dbzDwU",
    "caption": "Jaqueta Masculina Casaco Lã Blusa De Frio Inverno Tricô Com Bolsos\nOferta Especial: R$69,23\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "5ApZpuyabX",
    "video": "5ApZpuyabX.mp4",
    "offer_link": "https://s.shopee.com.br/5ApZpuyabX",
    "caption": "KIT DE MEIA FEMININA BRANCA FOFO COM TEXTURA ALGODAO POLIESTER 35-40 IDEAL PARA \nOferta Especial: R$14,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "3B4VSF6CfD",
    "video": "3B4VSF6CfD.mp4",
    "offer_link": "https://s.shopee.com.br/3B4VSF6CfD",
    "caption": "Meia Calça Fina7D ANTICELULITE Fio  70 Plus Size – Veste do 36 ao 54 | Conforto \nOferta Especial: R$27,97\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "3qKCFT3fJP",
    "video": "3qKCFT3fJP.mp4",
    "offer_link": "https://s.shopee.com.br/3qKCFT3fJP",
    "caption": "Kit 1 - 4  Pares Nova Meia Aveludada Térmica Flanelada Inverno  tamanho único e \nOferta Especial: R$11,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "1VwHTBCY2z",
    "video": "1VwHTBCY2z.mp4",
    "offer_link": "https://s.shopee.com.br/1VwHTBCY2z",
    "caption": "3d Hydra Lipgloss Kiko Milano\nOferta Especial: R$24\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "1qZ7rnBHN5",
    "video": "1qZ7rnBHN5.mp4",
    "offer_link": "https://s.shopee.com.br/1qZ7rnBHN5",
    "caption": "Meia-Calça Térmica Feminina Plus Size M-GG Forrada Peluciada Translúcida de Lã  \nOferta Especial: R$25,98\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "20sY46Ae28",
    "video": "20sY46Ae28.mp4",
    "offer_link": "https://s.shopee.com.br/20sY46Ae28",
    "caption": "Kit 2 Calças Legging Lisa Fitness Feminina Suplex  Envio Rapido Moda LLevo\nOferta Especial: R$49,54\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "2BByGPA0hB",
    "video": "2BByGPA0hB.mp4",
    "offer_link": "https://s.shopee.com.br/2BByGPA0hB",
    "caption": "Shampoo Escurecedor Cabelos Brancos Tonalizante Preto, Avelã, Marsala Platinado \nOferta Especial: R$15\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "2Voof18k1H",
    "video": "2Voof18k1H.mp4",
    "offer_link": "https://s.shopee.com.br/2Voof18k1H",
    "caption": "Kit  Pares de Meias Soquete Feminina Adulto Estampada Cores Delicadas\nOferta Especial: R$11,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "17TgQIG5o",
    "video": "17TgQIG5o.mp4",
    "offer_link": "https://s.shopee.com.br/17TgQIG5o",
    "caption": "Areia Catbio Biodegradável 4 Kg - Max Clean - Grãos Finos\nOferta Especial: R$46,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "LkK52GzPu",
    "video": "LkK52GzPu.mp4",
    "offer_link": "https://s.shopee.com.br/LkK52GzPu",
    "caption": "Tinta para Tecido Acrilex 37ml - Cores Avulsas e Kits Temáticos - Alta Cobertura\nOferta Especial: R$7,5\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "W3kHLGM4x",
    "video": "W3kHLGM4x.mp4",
    "offer_link": "https://s.shopee.com.br/W3kHLGM4x",
    "caption": "Meia-calça grossa e elástica alta para meninas no inverno\nOferta Especial: R$22,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "qgafxF5P3",
    "video": "qgafxF5P3.mp4",
    "offer_link": "https://s.shopee.com.br/qgafxF5P3",
    "caption": "calça moletom de lã grossa unissex (envio imediato)\nOferta Especial: R$74,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "9Kf8nZij9l",
    "video": "9Kf8nZij9l.mp4",
    "offer_link": "https://s.shopee.com.br/9Kf8nZij9l",
    "caption": "Calça Alfaiataria Feminina Cintura Alta Lançamento Com Zíper Social Slim Fino Bl\nOferta Especial: R$32,95\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "9fHzCBhSTr",
    "video": "9fHzCBhSTr.mp4",
    "offer_link": "https://s.shopee.com.br/9fHzCBhSTr",
    "caption": "Kit ate 6 pares de meia/meias soquete térmica grossa flanelada fleece inverno fr\nOferta Especial: R$19,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "AAEFn6fYSy",
    "video": "AAEFn6fYSy.mp4",
    "offer_link": "https://s.shopee.com.br/AAEFn6fYSy",
    "caption": "Kit 4 Travesseiros de Manta com Fibra Mista Macia Travesseiro tnt\nOferta Especial: R$19\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "AKXfzPev83",
    "video": "AKXfzPev83.mp4",
    "offer_link": "https://s.shopee.com.br/AKXfzPev83",
    "caption": "2025 Nova Série 8 Relógio T800 Ultra Smart Watch Esportivo Sem Fio À Prova D'águ\nOferta Especial: R$36,88\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8V61o2ltqk",
    "video": "8V61o2ltqk.mp4",
    "offer_link": "https://s.shopee.com.br/8V61o2ltqk",
    "caption": "Escova 3 Em 1 Vassoura Rodo Gap Limpeza Esfregão Mop Limpa\nOferta Especial: R$15,88\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8KmbbjmXBj",
    "video": "8KmbbjmXBj.mp4",
    "offer_link": "https://s.shopee.com.br/8KmbbjmXBj",
    "caption": "Kit 3 pares Meia Calça Infantil Menina e Menino Diversas Estampas Super Confortá\nOferta Especial: R$26,7\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "8fPS0LlGVp",
    "video": "8fPS0LlGVp.mp4",
    "offer_link": "https://s.shopee.com.br/8fPS0LlGVp",
    "caption": "Mochila Mala Reforçada Notebook Impermeável Escolar Trabalho Oferta\nOferta Especial: R$29,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "902IOxjzpv",
    "video": "902IOxjzpv.mp4",
    "offer_link": "https://s.shopee.com.br/902IOxjzpv",
    "caption": "BODY SPLASH MASCULINO BARBARIUS 200ML - PRIMACIAL PERFUME AMADEIRADO\nOferta Especial: R$28,45\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6feNcfssZV",
    "video": "6feNcfssZV.mp4",
    "offer_link": "https://s.shopee.com.br/6feNcfssZV",
    "caption": "Camisola Renda Feminina Pijama Sexy Sensual Lingerie Conforto Linha Noite sem Bo\nOferta Especial: R$16,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7AaeDaqyYc",
    "video": "7AaeDaqyYc.mp4",
    "offer_link": "https://s.shopee.com.br/7AaeDaqyYc",
    "caption": "TOYADENTEscova Dental TOYADENT Ultra Soft, Kit 3 Unidades, 5500+ Cerdas, Cores V\nOferta Especial: R$17,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "70HE1Hrbtb",
    "video": "70HE1Hrbtb.mp4",
    "offer_link": "https://s.shopee.com.br/70HE1Hrbtb",
    "caption": "Calça Pantalona Feminina Tecido texturado Calça Feminino Cintura Alta Pantalona \nOferta Especial: R$39,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7VDUcCphsi",
    "video": "7VDUcCphsi.mp4",
    "offer_link": "https://s.shopee.com.br/7VDUcCphsi",
    "caption": "Meia Calça Feminina Plus Size Térmica Grossa Super Elástica Translucida Super St\nOferta Especial: R$23,98\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7pqL0ooRCo",
    "video": "7pqL0ooRCo.mp4",
    "offer_link": "https://s.shopee.com.br/7pqL0ooRCo",
    "caption": "Kit 2000 Peças Bolsa Elástico De Cabelo Feminino Descartável Multicolorido\nOferta Especial: R$4,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "7fWuoVp4Xn",
    "video": "7fWuoVp4Xn.mp4",
    "offer_link": "https://s.shopee.com.br/7fWuoVp4Xn",
    "caption": "Luminária Solar Parede 21W LED Controle Remoto De Jardim À Prova D'água Indução \nOferta Especial: R$24,89\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "5VSQEWxJwO",
    "video": "5VSQEWxJwO.mp4",
    "offer_link": "https://s.shopee.com.br/5VSQEWxJwO",
    "caption": "Moedor Elétrico Café Grãos Inox 150W Multifuncional 110V 220V Compacto Potente P\nOferta Especial: R$41,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "5L902DxxHN",
    "video": "5L902DxxHN.mp4",
    "offer_link": "https://s.shopee.com.br/5L902DxxHN",
    "caption": "Cobertor Casal 200x180 Antialérgico Estampado e Cor Lisa - Toque Macio - Manta C\nOferta Especial: R$28,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "5q5Gd8w3GU",
    "video": "5q5Gd8w3GU.mp4",
    "offer_link": "https://s.shopee.com.br/5q5Gd8w3GU",
    "caption": "Meia-Calça Térmica Forrado Grosso Translúcido Leggings De Lã Quente Das Mulheres\nOferta Especial: R$15,99\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6Ai71kumaa",
    "video": "6Ai71kumaa.mp4",
    "offer_link": "https://s.shopee.com.br/6Ai71kumaa",
    "caption": "Sandália Babuche Adulto Feminino  Nuvem com 8 Bottons aleatórios\nOferta Especial: R$32,9\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6VKxQMtVug",
    "video": "6VKxQMtVug.mp4",
    "offer_link": "https://s.shopee.com.br/6VKxQMtVug",
    "caption": "Película Cerâmica 9D 3D iPhone Gel Hidrogel Flexível película iphone 13 11 12 14\nOferta Especial: R$4,98\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "6L1XE3u9Ff",
    "video": "6L1XE3u9Ff.mp4",
    "offer_link": "https://s.shopee.com.br/6L1XE3u9Ff",
    "caption": "Kit Feira Cronolola Bemdita Ghee 100g Nutrição Hidratação e Reconstrução\nOferta Especial: R$28,49\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  },
  {
    "slug": "4Ax2e52OeG",
    "video": "4Ax2e52OeG.mp4",
    "offer_link": "https://s.shopee.com.br/4Ax2e52OeG",
    "caption": "calças fler com bolso tecido grosso 38/40/42/44/46/48/50/52/54\nOferta Especial: R$29,49\nLink nos comentarios 👇\n#shopee #achadinhos #promocao"
  }
];
    const MAX_RETRIES = 3;

    const readLocal = (k, fb) => { try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };
    const readSession = (k, fb) => { try { const r = sessionStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } };

    let progress = readLocal(PK, {});
    let state = readSession(SK, { current: { step: 'START', slug: null, retries: 0 }, history: [], future: [] });

    const saveState = (step, slug = state.current.slug, pushToHistory = true) => {
        if (pushToHistory && (state.history.length === 0 || state.history[state.history.length - 1].step !== state.current.step)) {
            state.history.push({ ...state.current });
            state.future = [];
        }
        state.current = { step, slug, retries: 0 };
        sessionStorage.setItem(SK, JSON.stringify(state));
    };

    const saveProgress = () => localStorage.setItem(PK, JSON.stringify(progress));

    const navigateTo = (url, step, slug = state.current.slug, pushToHistory = true) => {
        saveState(step, slug, pushToHistory);
        location.href = url;
    };

    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const log = (msg, status = 'INFO', color = '#fff') => {
        const s = document.getElementById('bot-status');
        const m = document.getElementById('bot-msg');
        if (s) s.innerText = 'Status: ' + status;
        if (m) { m.innerText = msg; m.style.color = color; }
        console.log('[BOT]', status, '-', msg);
    };

    // ── XPath com múltiplos fallbacks ──────────────────────────
    const waitAnyXP = async (xpaths, timeout = 15000) => {
        const deadline = Date.now() + timeout;
        while (Date.now() < deadline) {
            for (const xp of xpaths) {
                try {
                    const el = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el && el.isConnected) return el;
                } catch (e) {}
            }
            await sleep(1000);
        }
        return null;
    };

    // ── Safe paste em contenteditable ──────────────────────────
    const safePaste = async (el, text) => {
        el.focus();
        el.click();
        await sleep(500);
        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            const ev = new ClipboardEvent('paste', {
                bubbles: true, cancelable: true,
                clipboardData: new DataTransfer()
            });
            ev.clipboardData.setData('text/plain', text);
            el.dispatchEvent(ev);
            await sleep(1000);
            if (!el.textContent.trim()) document.execCommand('insertText', false, text);
        } catch (e) {
            el.textContent = text;
        }
        el.dispatchEvent(new InputEvent('input', {
            bubbles: true, cancelable: true,
            inputType: 'insertText', data: text
        }));
        await sleep(1000);
    };

    // ── Detectar produto na página ─────────────────────────────
    const detectarProduto = () => {
        const pageText = document.body.innerText + document.body.innerHTML;
        for (const p of LISTA) {
            if (pageText.includes(p.video) || pageText.includes(p.slug)) return p;
        }
        try {
            const desc = document.evaluate(
                '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
            ).singleNodeValue;
            if (desc) {
                const txt = desc.textContent.trim();
                for (const p of LISTA) {
                    if (txt.includes(p.slug)) return p;
                }
            }
        } catch (e) {}
        return null;
    };

    // ── Painel UI ──────────────────────────────────────────────
    if (!document.getElementById('bot-panel')) {
        const panel = document.createElement('div');
        panel.id = 'bot-panel';
        panel.style = 'position:fixed;top:10px;right:10px;z-index:999999;background:rgba(0,0,0,0.9);color:#0f0;padding:15px;border:1px solid #ff0050;font-family:monospace;width:340px;border-radius:8px;box-shadow:0 0 10px #ff0050;';
        panel.innerHTML = `
            <h4 style="color:#ff0050;margin:0">BOT TIKTOK v10</h4>
            <div id="bot-status" style="margin-top:10px;font-weight:bold;">Iniciando...</div>
            <div id="bot-msg" style="font-size:12px;color:#fff;margin-top:5px;word-wrap:break-word;min-height:40px;"></div>
            <div id="bot-produto" style="font-size:11px;color:#0ff;margin-top:5px;word-wrap:break-word;"></div>
            <div style="margin-top:10px;display:flex;gap:5px;">
                <button id="btn-back" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Voltar</button>
                <button id="btn-forward" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Avancar</button>
                <button id="btn-reset" style="cursor:pointer;background:#222;color:white;border:1px solid #555;padding:5px;flex:1;border-radius:4px;font-size:11px;">Recarregar</button>
                <button id="btn-clear" style="cursor:pointer;background:#500;color:white;border:1px solid #f00;padding:5px;flex:1;border-radius:4px;font-size:11px;font-weight:bold;">Apagar Memoria</button>
            </div>`;
        document.body.appendChild(panel);

        document.getElementById('btn-reset').addEventListener('click', () => {
            sessionStorage.removeItem(SK);
            location.reload();
        });
        document.getElementById('btn-back').addEventListener('click', () => {
            if (state.history.length > 0) {
                state.future.unshift(state.current);
                state.current = state.history.pop();
                sessionStorage.setItem(SK, JSON.stringify(state));
                location.reload();
            }
        });
        document.getElementById('btn-forward').addEventListener('click', () => {
            if (state.future.length > 0) {
                state.history.push(state.current);
                state.current = state.future.shift();
                sessionStorage.setItem(SK, JSON.stringify(state));
                location.reload();
            }
        });
        document.getElementById('btn-clear').addEventListener('click', () => {
            if (confirm('Apagar memoria? O bot vai repostar os mesmos videos.')) {
                localStorage.removeItem(PK);
                progress = {};
                sessionStorage.removeItem(SK);
                alert('Memoria limpa!');
                location.reload();
            }
        });
    }

    const logProduto = (p) => {
        const el = document.getElementById('bot-produto');
        if (el) el.innerText = p ? `Produto: ${p.slug}` : '';
    };

    await sleep(1500);

    // ── Loop principal ─────────────────────────────────────────
    while (true) {
        state = readSession(SK, { current: { step: 'START', slug: null, retries: 0 }, history: [], future: [] });

        const PASSOS_COM_PRODUTO = ['POSTAR', 'IR_COMENTARIOS', 'ENVIAR_LINK'];
        if (PASSOS_COM_PRODUTO.includes(state.current.step) && !state.current.slug) {
            log('Estado invalido (sem slug). Reiniciando...', 'AUTO-RESET', '#ff0');
            saveState('START', null);
            await sleep(1000);
            continue;
        }

        const produtoAtual = state.current.slug ? LISTA.find(p => p.slug === state.current.slug) : null;
        if (produtoAtual) logProduto(produtoAtual);
        log(`Passo: ${state.current.step}${state.current.slug ? ' | ' + state.current.slug : ''}`);

        try {
            switch (state.current.step) {

                // ── START ────────────────────────────────────────
                case 'START': {
                    if (!location.pathname.includes('/upload')) {
                        navigateTo(
                            'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                            'AGUARDAR_VIDEO', null
                        );
                        return;
                    }
                    saveState('AGUARDAR_VIDEO', null, false);
                    await sleep(2000);
                    break;
                }

                // ── AGUARDAR_VIDEO ──────────────────────────────
                case 'AGUARDAR_VIDEO': {
                    const btnSel = await waitAnyXP([
                        '//*[@data-e2e="select_video_button"]',
                        '//button[contains(@aria-label,"elecionar")]',
                        '//button[contains(@aria-label,"elect")]',
                        '//span[contains(text(),"Selecionar")]/ancestor::button',
                    ], 15000);
                    if (!btnSel) throw new Error('Botao Selecionar Video nao encontrado');

                    log('Escolha o video na janela do Windows', 'AGUARDANDO USUARIO', '#0ff');
                    btnSel.click();

                    const campoTexto = await waitAnyXP([
                        '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                        '//div[@contenteditable="true"]',
                    ], 300000);
                    if (!campoTexto) throw new Error('Timeout: nenhum video selecionado');

                    log('Video detectado! Aguardando tela estabilizar...', 'AGUARDANDO', '#ff0');
                    await sleep(10000);

                    let produto = detectarProduto();
                    if (!produto) {
                        log('Nao identifiquei o video. Clique no produto correto:', 'ESCOLHA', '#ff0');
                        produto = await new Promise(resolve => {
                            const wrap = document.createElement('div');
                            wrap.id = 'manual-picker';
                            wrap.style = 'max-height:180px;overflow-y:auto;margin-top:6px;';
                            const disponiveis = LISTA.filter(p => progress[p.slug] !== 'ok');
                            disponiveis.forEach(p => {
                                const b = document.createElement('button');
                                b.textContent = p.slug;
                                b.style = 'display:block;width:100%;margin:2px 0;background:#111;color:#0ff;border:1px solid #0ff;padding:4px 6px;font-size:10px;cursor:pointer;border-radius:3px;text-align:left;';
                                b.onclick = () => { wrap.remove(); resolve(p); };
                                wrap.appendChild(b);
                            });
                            document.getElementById('bot-panel').appendChild(wrap);
                        });
                    }

                    if (progress[produto.slug] === 'ok') {
                        log(`Aviso: "${produto.slug}" ja foi postado.`, 'AVISO', '#ff0');
                    }

                    log(`Produto: ${produto.slug}`, 'IDENTIFICADO', '#0f0');
                    logProduto(produto);
                    saveState('POSTAR', produto.slug, true);
                    await sleep(1000);
                    break;
                }

                // ── POSTAR (com retry) ──────────────────────────
                case 'POSTAR': {
                    if (!produtoAtual) throw new Error('Produto nao identificado. Reinicie.');

                    let publicado = false;

                    for (let tentativa = 1; tentativa <= MAX_RETRIES && !publicado; tentativa++) {
                        if (tentativa > 1) {
                            log(`Retry ${tentativa}/${MAX_RETRIES}...`, 'RETRY', '#ff0');
                            await sleep(3000);
                        }

                        try {
                            const descBox = await waitAnyXP([
                                '//div[contains(@class,"public-DraftEditor-content") or @data-contents="true"]',
                                '//div[@contenteditable="true"]',
                            ], 30000);
                            if (!descBox) throw new Error('Campo de legenda nao encontrado');

                            log(`Preenchendo legenda (tentativa ${tentativa})...`, 'AGUARDANDO', '#ff0');
                            await safePaste(descBox, produtoAtual.caption);
                            await sleep(4000);

                            if ((descBox.textContent || '').trim().length < 5) {
                                throw new Error('Legenda ficou vazia');
                            }

                            // fechar dialog se aparecer
                            try {
                                for (const xp of [
                                    '//*[@id=":rbv:"]/div[1]/div/svg',
                                    '//div[starts-with(@id,":r")]/div[1]/div/svg',
                                    '//div[@role="dialog"]//svg',
                                ]) {
                                    const svg = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                    if (svg) {
                                        const btn = svg.closest('button') || svg.closest('div[role="button"]') || svg.parentElement;
                                        if (btn) { btn.click(); await sleep(2000); }
                                        break;
                                    }
                                }
                            } catch (e) {}

                            const btnPub = await waitAnyXP([
                                '//*[@id="root"]/div/div/div[2]/div[2]/div/div/div/div[6]/div/button[1]',
                                '//button[contains(., "Publicar")]',
                                '//button[contains(., "Post")]',
                            ], 10000);
                            if (!btnPub) throw new Error('Botao Publicar nao encontrado');

                            btnPub.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            await sleep(2000);

                            log('Publicando video...', 'PUBLICANDO', '#0f0');
                            btnPub.click();

                            // ── Confirmar publicação ────────────
                            log('Aguardando confirmacao de publicacao...', 'CONFIRMANDO', '#ff0');
                            const confirmado = await new Promise(resolve => {
                                const deadline = Date.now() + 60000;
                                const check = setInterval(async () => {
                                    const url = location.href;
                                    const body = document.body.innerText;

                                    // sinais de sucesso
                                    if (
                                        url.includes('/creator-center') ||
                                        url.includes('/content') ||
                                        body.includes('Seu vídeo foi publicado') ||
                                        body.includes('Seu video foi publicado') ||
                                        body.includes('Publicado') ||
                                        body.includes('Your video has been posted')
                                    ) {
                                        clearInterval(check);
                                        resolve(true);
                                        return;
                                    }

                                    if (Date.now() > deadline) {
                                        clearInterval(check);
                                        resolve(false);
                                    }
                                }, 2000);
                            });

                            if (confirmado) {
                                log('Publicacao confirmada!', 'OK', '#0f0');
                                progress[produtoAtual.slug] = 'ok';
                                saveProgress();
                                publicado = true;
                            } else {
                                log('Timeout confirmando publicacao', 'TIMEOUT', '#f90');
                            }

                        } catch (stepErr) {
                            log(`Erro tentativa ${tentativa}: ${stepErr.message}`, 'ERRO', '#f00');
                        }
                    }

                    if (!publicado) {
                        throw new Error(`Falha ao publicar após ${MAX_RETRIES} tentativas`);
                    }

                    await sleep(5000);
                    saveState('IR_COMENTARIOS', produtoAtual.slug, true);
                    break;
                }

                // ── IR_COMENTARIOS ──────────────────────────────
                case 'IR_COMENTARIOS': {
                    log('Abrindo comentarios...', 'COMENTARIOS', '#0ff');

                    const comentariosBtn = await waitAnyXP([
                        '//span[contains(text(),"Comentarios") or contains(text(),"Comentários")]',
                        '//button[contains(., "Comentarios") or contains(., "Comentários")]',
                        '//a[contains(., "Comentarios") or contains(., "Comentários")]',
                    ], 20000);

                    if (comentariosBtn) {
                        comentariosBtn.click();
                        await sleep(4000);
                    } else {
                        log('Botao comentarios nao encontrado, continuando...', 'AVISO', '#ff0');
                    }

                    saveState('ENVIAR_LINK', produtoAtual.slug, true);
                    break;
                }

                // ── ENVIAR_LINK ─────────────────────────────────
                case 'ENVIAR_LINK': {
                    if (!produtoAtual) throw new Error('Produto perdido');

                    log('Enviando link afiliado...', 'LINK', '#ff0');

                    const campoComentario = await waitAnyXP([
                        '//div[@contenteditable="true"]',
                        '//textarea',
                    ], 20000);

                    if (!campoComentario) {
                        throw new Error('Campo comentario nao encontrado');
                    }

                    await safePaste(campoComentario, produtoAtual.offer_link);
                    await sleep(2000);

                    const enviarBtn = await waitAnyXP([
                        '//button[contains(., "Postar")]',
                        '//button[contains(., "Enviar")]',
                        '//button[contains(., "Reply")]',
                    ], 10000);

                    if (enviarBtn) {
                        enviarBtn.click();
                        await sleep(3000);
                    }

                    log('Postagem finalizada!', 'OK', '#0f0');
                    saveState('START', null, true);
                    await sleep(5000);

                    navigateTo(
                        'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                        'AGUARDAR_VIDEO', null
                    );
                    return;
                }

                default: {
                    log('Estado desconhecido. Resetando...', 'RESET', '#f00');
                    saveState('START', null);
                    await sleep(2000);
                    break;
                }
            }
        } catch (err) {
            console.error(err);
            log(err?.message || 'Erro desconhecido', 'ERRO', '#f00');
            await sleep(5000);
        }
    }
})();