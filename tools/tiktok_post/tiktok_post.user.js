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
    "slug": "4Ax3GKm307",
    "video": "4Ax3GKm307.mp4",
    "offer_link": "https://s.shopee.com.br/4Ax3GKm307",
    "caption": "Vestido Feminino Brasil Copa 2026 Bandeira Frente Única Torcedora\nDe R$69.90 por R$59.90 (14% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "50WAFrisJI",
    "video": "50WAFrisJI.mp4",
    "offer_link": "https://s.shopee.com.br/50WAFrisJI",
    "caption": "Camiseta Personalizada do Brasil Blusa Feminina e Masculina 100% Algodão\nDe R$75.90 por R$34.91 (54% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5ApaSAiEyL",
    "video": "5ApaSAiEyL.mp4",
    "offer_link": "https://s.shopee.com.br/5ApaSAiEyL",
    "caption": "Cropped Moletom Moda Tendencia Femenina Blusa De Frio Brasil Copa Do Mundo 2026\nDe R$145.90 por R$78.79 (46% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4ftJrFk8zG",
    "video": "4ftJrFk8zG.mp4",
    "offer_link": "https://s.shopee.com.br/4ftJrFk8zG",
    "caption": "Conjunto Body e Saia Brasil Copa – Moletinho com Elastano, Modelagem Ajustada e \nDe R$100.00 por R$55.00 (45% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4qCk3YjVeJ",
    "video": "4qCk3YjVeJ.mp4",
    "offer_link": "https://s.shopee.com.br/4qCk3YjVeJ",
    "caption": "Jaqueta Feminina Lã Batida Premium Casaco Curto Inverno Chic 2026\nDe R$89.99 por R$69.99 (22% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "30l5sBqUMy",
    "video": "30l5sBqUMy.mp4",
    "offer_link": "https://s.shopee.com.br/30l5sBqUMy",
    "caption": "Cropped Top Feminino Personalizado Copa 2026 ESTHER BRAZIL\nDe R$49.90 por R$29.94 (40% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3B4W4Upr21",
    "video": "3B4W4Upr21.mp4",
    "offer_link": "https://s.shopee.com.br/3B4W4Upr21",
    "caption": "Saia Festa Junina São João Arraiá Quadrilha Caipira Curta Juvenil Adulta Rodada \nDe R$229.90 por R$99.90 (57% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2g8FTZrl2w",
    "video": "2g8FTZrl2w.mp4",
    "offer_link": "https://s.shopee.com.br/2g8FTZrl2w",
    "caption": "Kit 2 Camiseta Camisa Casal Brazil Frase Criativa Juntos na Copa Brasil Tendênci\nDe R$54.90 por R$54.90 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3g0mfPnx1A",
    "video": "3g0mfPnx1A.mp4",
    "offer_link": "https://s.shopee.com.br/3g0mfPnx1A",
    "caption": "Kit Camiseta Casal Brasil Nome Personalizado 100% Algodão Estampada Copa do Mund\nDe R$99.99 por R$64.99 (35% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3qKCrinJgD",
    "video": "3qKCrinJgD.mp4",
    "offer_link": "https://s.shopee.com.br/3qKCrinJgD",
    "caption": "Meias Estilo Primavera Para Pilates E fitness , Absorventes De Suor Respiráveis \nDe R$39.00 por R$15.99 (59% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3LNwGnpDh8",
    "video": "3LNwGnpDh8.mp4",
    "offer_link": "https://s.shopee.com.br/3LNwGnpDh8",
    "caption": "Conjunto Brasil cropped Canelado e short. Estilo verão,copa do mundo 2026 vibe  \nDe R$79.90 por R$34.90 (56% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3VhMT6oaMB",
    "video": "3VhMT6oaMB.mp4",
    "offer_link": "https://s.shopee.com.br/3VhMT6oaMB",
    "caption": "Conjunto Moletom Feminino Abrigo Blusa e Calça de Frio Flanelado Canguru Capuz I\nDe R$159.00 por R$119.00 (25% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "70HEdXbGFs",
    "video": "70HEdXbGFs.mp4",
    "offer_link": "https://s.shopee.com.br/70HEdXbGFs",
    "caption": "Blusa Feminina Brasil T-shirt Verão Algodão\nDe R$79.90 por R$31.96 (60% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7Aaepqacuv",
    "video": "7Aaepqacuv.mp4",
    "offer_link": "https://s.shopee.com.br/7Aaepqacuv",
    "caption": "Adultos e Crianças Pijamas de Inverno de Flanela Quente Confortável, Design Anim\nDe R$110.00 por R$55.00 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6feOEvcWvq",
    "video": "6feOEvcWvq.mp4",
    "offer_link": "https://s.shopee.com.br/6feOEvcWvq",
    "caption": "Conjunto Zíper Listrado Inverno\nDe R$70.00 por R$70.00 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6pxoREbtat",
    "video": "6pxoREbtat.mp4",
    "offer_link": "https://s.shopee.com.br/6pxoREbtat",
    "caption": "Casaco de Lã Batida Feminino 2026 Sobretudo Elegante Premium de Inverno luxoquen\nDe R$299.00 por R$215.28 (28% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7fWvQlYiu4",
    "video": "7fWvQlYiu4.mp4",
    "offer_link": "https://s.shopee.com.br/7fWvQlYiu4",
    "caption": "Camiseta Brasil Feminina Verde Torcida Estilosa Copa 2026 Algodão Premium Confor\nDe R$79.90 por R$31.96 (60% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7pqLd4Y5Z7",
    "video": "7pqLd4Y5Z7.mp4",
    "offer_link": "https://s.shopee.com.br/7pqLd4Y5Z7",
    "caption": "Macacao Feminino Decotado Alcinha 2 Fendas Pantalona\nDe R$49.99 por R$49.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7Ku529Zza2",
    "video": "7Ku529Zza2.mp4",
    "offer_link": "https://s.shopee.com.br/7Ku529Zza2",
    "caption": "Conjunto Ziper Inverno Pantalona\nDe R$70.00 por R$70.00 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7VDVESZMF5",
    "video": "7VDVESZMF5.mp4",
    "offer_link": "https://s.shopee.com.br/7VDVESZMF5",
    "caption": "Bady Doll Pijama Personagens Estampado Suede Com Detalhe de Renda Roupa de Dormi\nDe R$34.90 por R$19.90 (43% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5flr35gKxk",
    "video": "5flr35gKxk.mp4",
    "offer_link": "https://s.shopee.com.br/5flr35gKxk",
    "caption": "Blusa Feminina T-shirt Brasil com S 100% Algodão Premium Envio Imediato\nDe R$68.99 por R$29.67 (57% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5q5HFOfhcn",
    "video": "5q5HFOfhcn.mp4",
    "offer_link": "https://s.shopee.com.br/5q5HFOfhcn",
    "caption": "Saia Xadrez Feminino Curta De Inverno e Festa Junina Com Costura Reforçada Estil\nDe R$77.89 por R$29.90 (62% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5L90eThbdi",
    "video": "5L90eThbdi.mp4",
    "offer_link": "https://s.shopee.com.br/5L90eThbdi",
    "caption": "Conjunto Feminino Inverno Plush. Tamanhos: P ao Plus Size - Com zíper, capuz e b\nDe R$139.99 por R$116.99 (16% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5VSQqmgyIl",
    "video": "5VSQqmgyIl.mp4",
    "offer_link": "https://s.shopee.com.br/5VSQqmgyIl",
    "caption": "Joyjoy Conjunto de Pijamas de Seda Alta para Mulheres – Verão e Outono, Manga Lo\nDe R$120.57 por R$28.99 (76% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6L1XqJdnbw",
    "video": "6L1XqJdnbw.mp4",
    "offer_link": "https://s.shopee.com.br/6L1XqJdnbw",
    "caption": "Blusa Feminina Brasil South America T-shirt Verão Manga Curta Envio Imediato\nDe R$69.90 por R$38.00 (46% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6VKy2cdAGz",
    "video": "6VKy2cdAGz.mp4",
    "offer_link": "https://s.shopee.com.br/6VKy2cdAGz",
    "caption": "Casaco Teddy Feminino Pelúcia Tipo Pele de Carneiro Inverno Quentinho Macio Casu\nDe R$89.90 por R$89.90 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "60OhRhf4Hu",
    "video": "60OhRhf4Hu.mp4",
    "offer_link": "https://s.shopee.com.br/60OhRhf4Hu",
    "caption": "Conjunto Feminino Lanzinha Inverno Blusa Cropped e Saia Midi com Fendas Laterais\nDe R$59.90 por R$59.90 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6Ai7e0eQwx",
    "video": "6Ai7e0eQwx.mp4",
    "offer_link": "https://s.shopee.com.br/6Ai7e0eQwx",
    "caption": "Anime Dos Desenhos Animados Charlie Brown Conjunto de Pijamas Snoopy Mulheres No\nDe R$49.71 por R$28.99 (42% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9fHzoRR6qe",
    "video": "9fHzoRR6qe.mp4",
    "offer_link": "https://s.shopee.com.br/9fHzoRR6qe",
    "caption": "Blusa Feminina Cores Brasil Brasão Copa Do Mundo Gola Redonda Manga Curta Baby L\nDe R$54.90 por R$26.90 (51% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9pbQ0kQTVh",
    "video": "9pbQ0kQTVh.mp4",
    "offer_link": "https://s.shopee.com.br/9pbQ0kQTVh",
    "caption": "Calça Legging Termica Flanelada Peluciada Cós Alto Leg Feminina\nDe R$110.00 por R$38.99 (65% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9Kf9PpSNWc",
    "video": "9Kf9PpSNWc.mp4",
    "offer_link": "https://s.shopee.com.br/9Kf9PpSNWc",
    "caption": "Camiseta Brasileira Feminina Infantil e Adulto T-shirt Tal Mãe Tal Filha Brasil \nDe R$59.90 por R$59.90 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9UyZc8RkBf",
    "video": "9UyZc8RkBf.mp4",
    "offer_link": "https://s.shopee.com.br/9UyZc8RkBf",
    "caption": "Vestido Longo Feminino Alcinha Fina ,Costa Nua com Bojo ,Canelado Lisa , Fenda L\nDe R$59.90 por R$43.73 (27% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "AKXgbfOZUq",
    "video": "AKXgbfOZUq.mp4",
    "offer_link": "https://s.shopee.com.br/AKXgbfOZUq",
    "caption": "2 camisa do Brasil casal copa do mundo/ Kit casal 2 blusa do Brasil\nDe R$149.00 por R$149.00 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "AUr6nyNw9t",
    "video": "AUr6nyNw9t.mp4",
    "offer_link": "https://s.shopee.com.br/AUr6nyNw9t",
    "caption": "Meia 3D Cano Alto Volta às Aulas - Meia Patty Algodão Premium Personagens Divert\nDe R$39.80 por R$19.90 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9zuqD3PqAo",
    "video": "9zuqD3PqAo.mp4",
    "offer_link": "https://s.shopee.com.br/9zuqD3PqAo",
    "caption": "Conjunto Femenino Lanzinha Ribi canelada 2 Peças Blusa e Pantalona plus size\nDe R$79.99 por R$79.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "AAEGPMPCpr",
    "video": "AAEGPMPCpr.mp4",
    "offer_link": "https://s.shopee.com.br/AAEGPMPCpr",
    "caption": "Calça Wide Leg Jeans Feminina Cintura Alta Pantalona\nDe R$99.90 por R$64.99 (35% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "8KmcDzWBYW",
    "video": "8KmcDzWBYW.mp4",
    "offer_link": "https://s.shopee.com.br/8KmcDzWBYW",
    "caption": "Camiseta Feminina Preta 100% Algodão Academia Docinho Florzinha Lindinha Look Tr\nDe R$120.90 por R$32.65 (73% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "8V62QIVYDZ",
    "video": "8V62QIVYDZ.mp4",
    "offer_link": "https://s.shopee.com.br/8V62QIVYDZ",
    "caption": "Meia-calça térmica preta com forro peluciado –De Lã  quente para o inverno 2025,\nDe R$56.90 por R$29.60 (48% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "809lpNXSEU",
    "video": "809lpNXSEU.mp4",
    "offer_link": "https://s.shopee.com.br/809lpNXSEU",
    "caption": "Conjunto Feminino Body e Saia do Brasil Blusa da Seleção Brasileira\nDe R$99.98 por R$49.98 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "8ATC1gWotX",
    "video": "8ATC1gWotX.mp4",
    "offer_link": "https://s.shopee.com.br/8ATC1gWotX",
    "caption": "Shorts Tendencia Alfaiataria Com Cinto De Couro Modelo Social Short\nDe R$50.00 por R$23.50 (53% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "902J1DTeCi",
    "video": "902J1DTeCi.mp4",
    "offer_link": "https://s.shopee.com.br/902J1DTeCi",
    "caption": "Camiseta FemininaT-shirts Brasil Copa Camisa Roupa Blusinha Futebol Blusa Algodã\nDe R$59.90 por R$27.90 (53% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "9ALjDWT0rl",
    "video": "9ALjDWT0rl.mp4",
    "offer_link": "https://s.shopee.com.br/9ALjDWT0rl",
    "caption": "Kit 2 Peças Camisola + Pijama Baby Doll Feminino Sexy Lingerie Estampado Coração\nDe R$74.99 por R$32.99 (56% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "8fPScbUusg",
    "video": "8fPScbUusg.mp4",
    "offer_link": "https://s.shopee.com.br/8fPScbUusg",
    "caption": "Lovito Vestido Boho sem costas vestido primavera/verão para mulheres LK3LD389\nDe R$83.00 por R$57.90 (30% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "8pisouUHXj",
    "video": "8pisouUHXj.mp4",
    "offer_link": "https://s.shopee.com.br/8pisouUHXj",
    "caption": "Conjunto Brasil cropped e short. Estilo verão,copa do mundo 2026 vibe  looks do \nDe R$29.90 por R$18.90 (37% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1qZ8U2uvkO",
    "video": "1qZ8U2uvkO.mp4",
    "offer_link": "https://s.shopee.com.br/1qZ8U2uvkO",
    "caption": "Cropped Brasil Feminino Torcedora Copa Canelado Bordado Manga Curta Verde Amarel\nDe R$59.90 por R$29.95 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1gFiHjvZ5N",
    "video": "1gFiHjvZ5N.mp4",
    "offer_link": "https://s.shopee.com.br/1gFiHjvZ5N",
    "caption": "Casaco De Pelúcia Inverno Feminino De Manga Longa Fofa Quente\nDe R$105.57 por R$84.99 (19% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1VwI5QwCQM",
    "video": "1VwI5QwCQM.mp4",
    "offer_link": "https://s.shopee.com.br/1VwI5QwCQM",
    "caption": "Poncho Casaco Lã Feminino Trico Blusa De Frio Inverno Bico\nDe R$107.01 por R$78.90 (26% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1Lcrt7wplL",
    "video": "1Lcrt7wplL.mp4",
    "offer_link": "https://s.shopee.com.br/1Lcrt7wplL",
    "caption": "CALÇA MONTARIA FLANELADA FEMENINA COM RECORTE LATERAL NO COURO FAKE   ESTILOSA B\nDe R$59.99 por R$45.99 (23% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2VopHGsOOa",
    "video": "2VopHGsOOa.mp4",
    "offer_link": "https://s.shopee.com.br/2VopHGsOOa",
    "caption": "Blusa T-shirt Feminina Cruz Coração Confortável 100% Algodão Presente Dia Das Mã\nDe R$79.90 por R$9.59 (88% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2LVP4xt1jZ",
    "video": "2LVP4xt1jZ.mp4",
    "offer_link": "https://s.shopee.com.br/2LVP4xt1jZ",
    "caption": "Vestido Femenino Chemise Longo Elegante Plus Size Con Botões, Manga Ajustable,3/\nDe R$85.00 por R$67.15 (21% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2BBysetf4Y",
    "video": "2BBysetf4Y.mp4",
    "offer_link": "https://s.shopee.com.br/2BBysetf4Y",
    "caption": "Kit 2 unidades Cardigan Tricot Aberto Casaquinho Manga Longa\nDe R$59.80 por R$36.90 (38% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "20sYgLuIPX",
    "video": "20sYgLuIPX.mp4",
    "offer_link": "https://s.shopee.com.br/20sYgLuIPX",
    "caption": "Blusa Feminina De Tricot Manga Longa Colmeia Onda Tricô Inverno Suéter Trico\nDe R$56.90 por R$48.90 (14% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "W3ktb00SG",
    "video": "W3ktb00SG.mp4",
    "offer_link": "https://s.shopee.com.br/W3ktb00SG",
    "caption": "Regatas do Brasil Feminina Ribana Copa Bandeira BORDADA\nDe R$49.90 por R$49.90 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "LkKhI0dnF",
    "video": "LkKhI0dnF.mp4",
    "offer_link": "https://s.shopee.com.br/LkKhI0dnF",
    "caption": "Calça Cargo Jeans Feminina Bolso Lateral Cintura Alta  Wide Leg Pantalona\nDe R$140.00 por R$64.99 (54% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "BQuUz1H8E",
    "video": "BQuUz1H8E.mp4",
    "offer_link": "https://s.shopee.com.br/BQuUz1H8E",
    "caption": "Mulheres Outono Inverno Camisola Grossa Quente Manga Longa Sólida De Malha Velud\nDe R$109.50 por R$78.84 (28% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "17UIg1uTD",
    "video": "17UIg1uTD.mp4",
    "offer_link": "https://s.shopee.com.br/17UIg1uTD",
    "caption": "Conjunto Feminino basico short feminino cropped basico feminino conjunto academi\nDe R$50.00 por R$42.99 (14% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1BJRgoxT6S",
    "video": "1BJRgoxT6S.mp4",
    "offer_link": "https://s.shopee.com.br/1BJRgoxT6S",
    "caption": "Blusa Cristã Tua Graça me Basta Religiosa Camiseta Manga Curta Várias Cores\nDe R$59.90 por R$29.95 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "1101UVy6RR",
    "video": "1101UVy6RR.mp4",
    "offer_link": "https://s.shopee.com.br/1101UVy6RR",
    "caption": "Blusa de Frio Feminina Estilosa Tricot Corações Roupa Feminina Elegante de Inver\nDe R$79.90 por R$44.90 (44% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "qgbICyjmQ",
    "video": "qgbICyjmQ.mp4",
    "offer_link": "https://s.shopee.com.br/qgbICyjmQ",
    "caption": "Calça Pantalona Feminina Lanzinha Cintura Alta  com Bolso Moda pra Inverno Tende\nDe R$32.98 por R$27.38 (17% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "gNB5tzN7P",
    "video": "gNB5tzN7P.mp4",
    "offer_link": "https://s.shopee.com.br/gNB5tzN7P",
    "caption": "Vestido Lenço Várias Formas de Usar Vestido De bico Vestido De Pontas Verão\nDe R$19.99 por R$19.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4VZtewkmLA",
    "video": "4VZtewkmLA.mp4",
    "offer_link": "https://s.shopee.com.br/4VZtewkmLA",
    "caption": "Body Feminina mula manca  Decote Ombro Só Fivela Bory EleganteTem Bojo\nDe R$34.99 por R$27.29 (22% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4LGTSdlPg9",
    "video": "4LGTSdlPg9.mp4",
    "offer_link": "https://s.shopee.com.br/4LGTSdlPg9",
    "caption": "Saia Festa Junina São João Arraiá Quadrilha Caipira Curta Juvenil Adulta Rodada \nDe R$229.90 por R$99.90 (57% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4Ax3GKm318",
    "video": "4Ax3GKm318.mp4",
    "offer_link": "https://s.shopee.com.br/4Ax3GKm318",
    "caption": "Kit 12 Peças (6 Conjuntos) Pijama Feminino Baby Doll Short Doll Roupa Dormir 6 S\nDe R$150.00 por R$64.90 (57% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "40dd41mgM7",
    "video": "40dd41mgM7.mp4",
    "offer_link": "https://s.shopee.com.br/40dd41mgM7",
    "caption": "Conjunto Feminino Brasil Body Cavado e Saia Roupa Copa do Mundo Tam Único Verde \nDe R$129.99 por R$71.99 (45% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "5ApaSAiEzM",
    "video": "5ApaSAiEzM.mp4",
    "offer_link": "https://s.shopee.com.br/5ApaSAiEzM",
    "caption": "Camisa Camiseta Brazil Blusa Brasil Copa Lançamento 100% Algodão\nDe R$44.90 por R$26.49 (41% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "50WAFrisKL",
    "video": "50WAFrisKL.mp4",
    "offer_link": "https://s.shopee.com.br/50WAFrisKL",
    "caption": "Meia Stitch Infantil 3D Cano Alto Cartoon Desenho Animado Meia Maluca Divertida \nDe R$37.80 por R$19.90 (47% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4qCk3YjVfK",
    "video": "4qCk3YjVfK.mp4",
    "offer_link": "https://s.shopee.com.br/4qCk3YjVfK",
    "caption": "Jaqueta Parka  Bobojaco Casaco Sobretudo Feminino forrada pelúcia Blusa Frio Env\nDe R$129.00 por R$129.00 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "4ftJrFk90J",
    "video": "4ftJrFk90J.mp4",
    "offer_link": "https://s.shopee.com.br/4ftJrFk90J",
    "caption": "Vestido Longo Com FORO e BOJO, Feminino Com manga Variados super confortáveis e \nDe R$74.99 por R$74.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3B4W4Upr32",
    "video": "3B4W4Upr32.mp4",
    "offer_link": "https://s.shopee.com.br/3B4W4Upr32",
    "caption": "Cropped do Brasil Feminino Bicolor Manga Curta Ribana Babylook Copa Do Mundo Ten\nDe R$46.80 por R$29.95 (36% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "30l5sBqUO1",
    "video": "30l5sBqUO1.mp4",
    "offer_link": "https://s.shopee.com.br/30l5sBqUO1",
    "caption": "Saia Festa Junina Xadrez Luxo Feminina Adulto Juvenil Caipira São João Quadrilha\nDe R$89.90 por R$72.89 (19% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2qRffsr7j0",
    "video": "2qRffsr7j0.mp4",
    "offer_link": "https://s.shopee.com.br/2qRffsr7j0",
    "caption": "Macacão Feminino Pantalona Largo Alcinha Regulável Decote V P M G GG Tecido Duna\nDe R$89.90 por R$49.89 (45% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "2g8FTZrl3z",
    "video": "2g8FTZrl3z.mp4",
    "offer_link": "https://s.shopee.com.br/2g8FTZrl3z",
    "caption": "2 Peças/1 Conjunto Outono Inverno Solto Doce Casual Pijamas Feminino Grosso Lã M\nDe R$166.00 por R$87.98 (47% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3qKCrinJhE",
    "video": "3qKCrinJhE.mp4",
    "offer_link": "https://s.shopee.com.br/3qKCrinJhE",
    "caption": "Regata Baby look Alcinha Brasil Y2K Moda Gringa Virginia Regatinha Copa\nDe R$34.99 por R$29.90 (15% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3g0mfPnx2D",
    "video": "3g0mfPnx2D.mp4",
    "offer_link": "https://s.shopee.com.br/3g0mfPnx2D",
    "caption": "Mulheres Lã De Cordeiro Jaqueta Quente Outono Inverno Gola Dupla Espessamento Cu\nDe R$235.00 por R$164.50 (30% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3VhMT6oaNC",
    "video": "3VhMT6oaNC.mp4",
    "offer_link": "https://s.shopee.com.br/3VhMT6oaNC",
    "caption": "Conjunto Feminino Body Gola Alta Marrom + Saia Couro Plissada\nDe R$89.99 por R$89.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "3LNwGnpDiB",
    "video": "3LNwGnpDiB.mp4",
    "offer_link": "https://s.shopee.com.br/3LNwGnpDiB",
    "caption": "Casaco De Frio Luxo Com Detalhes e Botões De Tricot Tendência 2025 Blusa de frio\nDe R$49.99 por R$49.99 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7Aaepqacvw",
    "video": "7Aaepqacvw.mp4",
    "offer_link": "https://s.shopee.com.br/7Aaepqacvw",
    "caption": "Cropped Top Feminino Alcinha Frente Forrada Personalizado Copa 2026 ESTHER BRASI\nDe R$48.90 por R$28.85 (41% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "70HEdXbGGv",
    "video": "70HEdXbGGv.mp4",
    "offer_link": "https://s.shopee.com.br/70HEdXbGGv",
    "caption": "Calça Alfaiataria Feminina Cintura Alta Com Zíper Na Lateral\nDe R$49.90 por R$39.92 (20% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6pxoREbtbu",
    "video": "6pxoREbtbu.mp4",
    "offer_link": "https://s.shopee.com.br/6pxoREbtbu",
    "caption": "Jaqueta Jeans Feminina Manga Longa Denim Linha Premium\nDe R$74.80 por R$74.80 (0% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "6feOEvcWwt",
    "video": "6feOEvcWwt.mp4",
    "offer_link": "https://s.shopee.com.br/6feOEvcWwt",
    "caption": "Short Alfaiataria Feminino Social Com Cinto Cintura Alta PROMOÇAO\nDe R$89.90 por R$20.80 (77% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7pqLd4Y5a8",
    "video": "7pqLd4Y5a8.mp4",
    "offer_link": "https://s.shopee.com.br/7pqLd4Y5a8",
    "caption": "Lovito Regata Casual Com Botão Liso De Metal Redondo Para Mulheres LNL38050 (Bra\nDe R$45.50 por R$31.20 (31% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7fWvQlYiv7",
    "video": "7fWvQlYiv7.mp4",
    "offer_link": "https://s.shopee.com.br/7fWvQlYiv7",
    "caption": "Conjunto Feminino Livia Cropped e Saia Longa\nDe R$120.00 por R$65.00 (46% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7VDVESZMG6",
    "video": "7VDVESZMG6.mp4",
    "offer_link": "https://s.shopee.com.br/7VDVESZMG6",
    "caption": "Jaqueta Casual Feminina Estilo Coreano, Novo Design de Alta Qualidade – Azul, Ta\nDe R$47.41 por R$24.99 (47% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
  },
  {
    "slug": "7Ku529Zzb5",
    "video": "7Ku529Zzb5.mp4",
    "offer_link": "https://s.shopee.com.br/7Ku529Zzb5",
    "caption": "vestido brasil vestido tubinho tomara Brasil\nDe R$100.00 por R$50.00 (50% OFF)\nLink na biografia deste perfil\n#shopee #oferta #promocao"
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

        const PASSOS_COM_PRODUTO = ['POSTAR'];
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

                    log('Postagem finalizada! Iniciando proximo video...', 'OK', '#0f0');
                    saveState('START', null, true);
                    await sleep(3000);

                    navigateTo(
                        'https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video',
                        'AGUARDAR_VIDEO', null
                    );
                    return;
                }

                // ── IR_COMENTARIOS (removido — link agora na bio) ──
                case 'IR_COMENTARIOS': {
                    saveState('START', null, true);
                    await sleep(1000);
                    break;
                }

                // ── ENVIAR_LINK (removido — link agora na bio) ────
                case 'ENVIAR_LINK': {
                    saveState('START', null, true);
                    await sleep(1000);
                    break;
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