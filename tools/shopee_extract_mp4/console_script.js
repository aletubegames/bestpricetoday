(async () => {
  const STORAGE_KEY = 'shopee_dl_progress';
  const CSV_KEY     = 'shopee_csv_data';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const human = () => sleep(3000 + Math.random() * 3000);

  // ── PRODUTOS (gerado pelo generate_script.py) ────────────
  const PRODUTOS = [
  {
    "slug": "9zupangBmu",
    "shopid": "792952722",
    "itemid": "58260172435",
    "offer_link": "https://s.shopee.com.br/9zupangBmu"
  },
  {
    "slug": "AAEFn6fYRx",
    "shopid": "299222557",
    "itemid": "58252841983",
    "offer_link": "https://s.shopee.com.br/AAEFn6fYRx"
  },
  {
    "slug": "AKXfzPev70",
    "shopid": "1077144780",
    "itemid": "58209766469",
    "offer_link": "https://s.shopee.com.br/AKXfzPev70"
  },
  {
    "slug": "AUr6BieHm3",
    "shopid": "1579330222",
    "itemid": "58260056158",
    "offer_link": "https://s.shopee.com.br/AUr6BieHm3"
  },
  {
    "slug": "809lD7nnqa",
    "shopid": "368039476",
    "itemid": "58207970054",
    "offer_link": "https://s.shopee.com.br/809lD7nnqa"
  },
  {
    "slug": "8ATBPQnAVd",
    "shopid": "493828477",
    "itemid": "58207667280",
    "offer_link": "https://s.shopee.com.br/8ATBPQnAVd"
  },
  {
    "slug": "8KmbbjmXAg",
    "shopid": "1077144780",
    "itemid": "58259736335",
    "offer_link": "https://s.shopee.com.br/8KmbbjmXAg"
  },
  {
    "slug": "8V61o2ltpj",
    "shopid": "1420372901",
    "itemid": "58202126334",
    "offer_link": "https://s.shopee.com.br/8V61o2ltpj"
  },
  {
    "slug": "8fPS0LlGUm",
    "shopid": "752743341",
    "itemid": "18350470458",
    "offer_link": "https://s.shopee.com.br/8fPS0LlGUm"
  },
  {
    "slug": "8pisCekd9p",
    "shopid": "1600778769",
    "itemid": "58259146436",
    "offer_link": "https://s.shopee.com.br/8pisCekd9p"
  },
  {
    "slug": "902IOxjzos",
    "shopid": "1077144780",
    "itemid": "23699442916",
    "offer_link": "https://s.shopee.com.br/902IOxjzos"
  },
  {
    "slug": "9ALibGjMTv",
    "shopid": "287079590",
    "itemid": "58210354378",
    "offer_link": "https://s.shopee.com.br/9ALibGjMTv"
  },
  {
    "slug": "6feNcfssYS",
    "shopid": "676684389",
    "itemid": "22793679889",
    "offer_link": "https://s.shopee.com.br/6feNcfssYS"
  },
  {
    "slug": "6pxnoysFDV",
    "shopid": "1485160784",
    "itemid": "20398143226",
    "offer_link": "https://s.shopee.com.br/6pxnoysFDV"
  },
  {
    "slug": "70HE1HrbsY",
    "shopid": "1077144780",
    "itemid": "58259802662",
    "offer_link": "https://s.shopee.com.br/70HE1HrbsY"
  },
  {
    "slug": "7AaeDaqyXb",
    "shopid": "1643565306",
    "itemid": "22798989144",
    "offer_link": "https://s.shopee.com.br/7AaeDaqyXb"
  },
  {
    "slug": "7Ku4PtqLCe",
    "shopid": "321128579",
    "itemid": "17422129005",
    "offer_link": "https://s.shopee.com.br/7Ku4PtqLCe"
  },
  {
    "slug": "7VDUcCphrh",
    "shopid": "502700315",
    "itemid": "22398682323",
    "offer_link": "https://s.shopee.com.br/7VDUcCphrh"
  },
  {
    "slug": "7fWuoVp4Wk",
    "shopid": "323364785",
    "itemid": "22494052851",
    "offer_link": "https://s.shopee.com.br/7fWuoVp4Wk"
  },
  {
    "slug": "7pqL0ooRBn",
    "shopid": "1671173223",
    "itemid": "22799419082",
    "offer_link": "https://s.shopee.com.br/7pqL0ooRBn"
  },
  {
    "slug": "5L902DxxGK",
    "shopid": "364843650",
    "itemid": "19299663655",
    "offer_link": "https://s.shopee.com.br/5L902DxxGK"
  },
  {
    "slug": "5VSQEWxJvN",
    "shopid": "383740485",
    "itemid": "58205413442",
    "offer_link": "https://s.shopee.com.br/5VSQEWxJvN"
  },
  {
    "slug": "5flqQpwgaQ",
    "shopid": "676684389",
    "itemid": "20899598197",
    "offer_link": "https://s.shopee.com.br/5flqQpwgaQ"
  },
  {
    "slug": "5q5Gd8w3FT",
    "shopid": "1013333026",
    "itemid": "22297378465",
    "offer_link": "https://s.shopee.com.br/5q5Gd8w3FT"
  },
  {
    "slug": "60OgpRvPuW",
    "shopid": "1097148583",
    "itemid": "23298100712",
    "offer_link": "https://s.shopee.com.br/60OgpRvPuW"
  },
  {
    "slug": "6Ai71kumZZ",
    "shopid": "1077144780",
    "itemid": "58209798552",
    "offer_link": "https://s.shopee.com.br/6Ai71kumZZ"
  },
  {
    "slug": "6L1XE3u9Ec",
    "shopid": "1587235748",
    "itemid": "22394250261",
    "offer_link": "https://s.shopee.com.br/6L1XE3u9Ec"
  },
  {
    "slug": "6VKxQMtVtf",
    "shopid": "437985893",
    "itemid": "22392924019",
    "offer_link": "https://s.shopee.com.br/6VKxQMtVtf"
  },
  {
    "slug": "40dcRm31yC",
    "shopid": "427106553",
    "itemid": "42727283804",
    "offer_link": "https://s.shopee.com.br/40dcRm31yC"
  },
  {
    "slug": "4Ax2e52OdF",
    "shopid": "1719334016",
    "itemid": "58204987358",
    "offer_link": "https://s.shopee.com.br/4Ax2e52OdF"
  },
  {
    "slug": "4LGSqO1lII",
    "shopid": "1566452692",
    "itemid": "22594546423",
    "offer_link": "https://s.shopee.com.br/4LGSqO1lII"
  },
  {
    "slug": "4VZt2h17xL",
    "shopid": "1255854196",
    "itemid": "18799319252",
    "offer_link": "https://s.shopee.com.br/4VZt2h17xL"
  },
  {
    "slug": "4ftJF00UcO",
    "shopid": "1553079968",
    "itemid": "58253492412",
    "offer_link": "https://s.shopee.com.br/4ftJF00UcO"
  },
  {
    "slug": "4qCjRIzrHR",
    "shopid": "321104773",
    "itemid": "21999234823",
    "offer_link": "https://s.shopee.com.br/4qCjRIzrHR"
  },
  {
    "slug": "50W9dbzDwU",
    "shopid": "1567174664",
    "itemid": "23994206734",
    "offer_link": "https://s.shopee.com.br/50W9dbzDwU"
  },
  {
    "slug": "5ApZpuyabX",
    "shopid": "390229041",
    "itemid": "21298731450",
    "offer_link": "https://s.shopee.com.br/5ApZpuyabX"
  },
  {
    "slug": "2g8ErK86g4",
    "shopid": "423397470",
    "itemid": "20899597332",
    "offer_link": "https://s.shopee.com.br/2g8ErK86g4"
  },
  {
    "slug": "2qRf3d7TL7",
    "shopid": "1006215031",
    "itemid": "29379017291",
    "offer_link": "https://s.shopee.com.br/2qRf3d7TL7"
  },
  {
    "slug": "30l5Fw6q0A",
    "shopid": "332179884",
    "itemid": "21799578236",
    "offer_link": "https://s.shopee.com.br/30l5Fw6q0A"
  },
  {
    "slug": "3B4VSF6CfD",
    "shopid": "1528985481",
    "itemid": "58252601035",
    "offer_link": "https://s.shopee.com.br/3B4VSF6CfD"
  },
  {
    "slug": "3LNveY5ZKG",
    "shopid": "716194498",
    "itemid": "23699364867",
    "offer_link": "https://s.shopee.com.br/3LNveY5ZKG"
  },
  {
    "slug": "3VhLqr4vzJ",
    "shopid": "1147173683",
    "itemid": "22493168100",
    "offer_link": "https://s.shopee.com.br/3VhLqr4vzJ"
  },
  {
    "slug": "3g0m3A4IeM",
    "shopid": "876866734",
    "itemid": "23594325096",
    "offer_link": "https://s.shopee.com.br/3g0m3A4IeM"
  },
  {
    "slug": "3qKCFT3fJP",
    "shopid": "425326129",
    "itemid": "18299351006",
    "offer_link": "https://s.shopee.com.br/3qKCFT3fJP"
  },
  {
    "slug": "1LcrGsDBNw",
    "shopid": "1127030290",
    "itemid": "23098648575",
    "offer_link": "https://s.shopee.com.br/1LcrGsDBNw"
  },
  {
    "slug": "1VwHTBCY2z",
    "shopid": "1414741692",
    "itemid": "22093703234",
    "offer_link": "https://s.shopee.com.br/1VwHTBCY2z"
  },
  {
    "slug": "1gFhfUBui2",
    "shopid": "1092986401",
    "itemid": "22993896055",
    "offer_link": "https://s.shopee.com.br/1gFhfUBui2"
  },
  {
    "slug": "1qZ7rnBHN5",
    "shopid": "1414741692",
    "itemid": "22798309966",
    "offer_link": "https://s.shopee.com.br/1qZ7rnBHN5"
  },
  {
    "slug": "20sY46Ae28",
    "shopid": "314093059",
    "itemid": "9512144763",
    "offer_link": "https://s.shopee.com.br/20sY46Ae28"
  },
  {
    "slug": "2BByGPA0hB",
    "shopid": "1608192482",
    "itemid": "58204739759",
    "offer_link": "https://s.shopee.com.br/2BByGPA0hB"
  },
  {
    "slug": "2LVOSi9NME",
    "shopid": "410693248",
    "itemid": "8337296913",
    "offer_link": "https://s.shopee.com.br/2LVOSi9NME"
  },
  {
    "slug": "2Voof18k1H",
    "shopid": "428624330",
    "itemid": "22297736513",
    "offer_link": "https://s.shopee.com.br/2Voof18k1H"
  },
  {
    "slug": "17TgQIG5o",
    "shopid": "1023760886",
    "itemid": "22996121313",
    "offer_link": "https://s.shopee.com.br/17TgQIG5o"
  },
  {
    "slug": "BQtsjHckr",
    "shopid": "1469144446",
    "itemid": "19898027204",
    "offer_link": "https://s.shopee.com.br/BQtsjHckr"
  },
  {
    "slug": "LkK52GzPu",
    "shopid": "390780728",
    "itemid": "18906277158",
    "offer_link": "https://s.shopee.com.br/LkK52GzPu"
  },
  {
    "slug": "W3kHLGM4x",
    "shopid": "955543641",
    "itemid": "18099249153",
    "offer_link": "https://s.shopee.com.br/W3kHLGM4x"
  },
  {
    "slug": "gNATeFik0",
    "shopid": "1169146045",
    "itemid": "20799757649",
    "offer_link": "https://s.shopee.com.br/gNATeFik0"
  },
  {
    "slug": "qgafxF5P3",
    "shopid": "413762733",
    "itemid": "22798456969",
    "offer_link": "https://s.shopee.com.br/qgafxF5P3"
  },
  {
    "slug": "1100sGES46",
    "shopid": "362458294",
    "itemid": "43108727838",
    "offer_link": "https://s.shopee.com.br/1100sGES46"
  },
  {
    "slug": "1BJR4ZDoj9",
    "shopid": "1012214402",
    "itemid": "22998326427",
    "offer_link": "https://s.shopee.com.br/1BJR4ZDoj9"
  },
  {
    "slug": "9UyYzsi5om",
    "shopid": "1006446880",
    "itemid": "23393393737",
    "offer_link": "https://s.shopee.com.br/9UyYzsi5om"
  },
  {
    "slug": "9Kf8nZij9l",
    "shopid": "515176772",
    "itemid": "23497427455",
    "offer_link": "https://s.shopee.com.br/9Kf8nZij9l"
  },
  {
    "slug": "9pbPOUgp8s",
    "shopid": "523113851",
    "itemid": "58253658672",
    "offer_link": "https://s.shopee.com.br/9pbPOUgp8s"
  },
  {
    "slug": "9fHzCBhSTr",
    "shopid": "1388170403",
    "itemid": "22697994424",
    "offer_link": "https://s.shopee.com.br/9fHzCBhSTr"
  },
  {
    "slug": "AAEFn6fYSy",
    "shopid": "640413729",
    "itemid": "19424166010",
    "offer_link": "https://s.shopee.com.br/AAEFn6fYSy"
  },
  {
    "slug": "9zupangBnx",
    "shopid": "915563136",
    "itemid": "18699319983",
    "offer_link": "https://s.shopee.com.br/9zupangBnx"
  },
  {
    "slug": "AUr6BieHn4",
    "shopid": "1083800536",
    "itemid": "58256288846",
    "offer_link": "https://s.shopee.com.br/AUr6BieHn4"
  },
  {
    "slug": "AKXfzPev83",
    "shopid": "1180920205",
    "itemid": "22093160276",
    "offer_link": "https://s.shopee.com.br/AKXfzPev83"
  },
  {
    "slug": "8ATBPQnAWe",
    "shopid": "375051668",
    "itemid": "22793684140",
    "offer_link": "https://s.shopee.com.br/8ATBPQnAWe"
  },
  {
    "slug": "809lD7nnrd",
    "shopid": "1388170403",
    "itemid": "22597994429",
    "offer_link": "https://s.shopee.com.br/809lD7nnrd"
  },
  {
    "slug": "8V61o2ltqk",
    "shopid": "1229158295",
    "itemid": "22197745981",
    "offer_link": "https://s.shopee.com.br/8V61o2ltqk"
  },
  {
    "slug": "8KmbbjmXBj",
    "shopid": "1041039897",
    "itemid": "18299329397",
    "offer_link": "https://s.shopee.com.br/8KmbbjmXBj"
  },
  {
    "slug": "8pisCekdAq",
    "shopid": "1424278396",
    "itemid": "58203349918",
    "offer_link": "https://s.shopee.com.br/8pisCekdAq"
  },
  {
    "slug": "8fPS0LlGVp",
    "shopid": "752743341",
    "itemid": "18397679423",
    "offer_link": "https://s.shopee.com.br/8fPS0LlGVp"
  },
  {
    "slug": "9ALibGjMUw",
    "shopid": "1653736071",
    "itemid": "58254354508",
    "offer_link": "https://s.shopee.com.br/9ALibGjMUw"
  },
  {
    "slug": "902IOxjzpv",
    "shopid": "1295467768",
    "itemid": "22894246754",
    "offer_link": "https://s.shopee.com.br/902IOxjzpv"
  },
  {
    "slug": "6pxnoysFEW",
    "shopid": "912462405",
    "itemid": "22492632177",
    "offer_link": "https://s.shopee.com.br/6pxnoysFEW"
  },
  {
    "slug": "6feNcfssZV",
    "shopid": "1234355161",
    "itemid": "22294382057",
    "offer_link": "https://s.shopee.com.br/6feNcfssZV"
  },
  {
    "slug": "7AaeDaqyYc",
    "shopid": "1605400328",
    "itemid": "22694645105",
    "offer_link": "https://s.shopee.com.br/7AaeDaqyYc"
  },
  {
    "slug": "70HE1Hrbtb",
    "shopid": "1277805925",
    "itemid": "23694913081",
    "offer_link": "https://s.shopee.com.br/70HE1Hrbtb"
  },
  {
    "slug": "7VDUcCphsi",
    "shopid": "1366709144",
    "itemid": "47757324104",
    "offer_link": "https://s.shopee.com.br/7VDUcCphsi"
  },
  {
    "slug": "7Ku4PtqLDh",
    "shopid": "616222685",
    "itemid": "23795569799",
    "offer_link": "https://s.shopee.com.br/7Ku4PtqLDh"
  },
  {
    "slug": "7pqL0ooRCo",
    "shopid": "986450286",
    "itemid": "23693118990",
    "offer_link": "https://s.shopee.com.br/7pqL0ooRCo"
  },
  {
    "slug": "7fWuoVp4Xn",
    "shopid": "1384675821",
    "itemid": "22998640234",
    "offer_link": "https://s.shopee.com.br/7fWuoVp4Xn"
  },
  {
    "slug": "5VSQEWxJwO",
    "shopid": "1619784139",
    "itemid": "58209332437",
    "offer_link": "https://s.shopee.com.br/5VSQEWxJwO"
  },
  {
    "slug": "5L902DxxHN",
    "shopid": "296363855",
    "itemid": "23492848273",
    "offer_link": "https://s.shopee.com.br/5L902DxxHN"
  },
  {
    "slug": "5q5Gd8w3GU",
    "shopid": "1161906393",
    "itemid": "22597557781",
    "offer_link": "https://s.shopee.com.br/5q5Gd8w3GU"
  },
  {
    "slug": "5flqQpwgbT",
    "shopid": "1224529773",
    "itemid": "22494928254",
    "offer_link": "https://s.shopee.com.br/5flqQpwgbT"
  },
  {
    "slug": "6Ai71kumaa",
    "shopid": "1234356004",
    "itemid": "23294049109",
    "offer_link": "https://s.shopee.com.br/6Ai71kumaa"
  },
  {
    "slug": "60OgpRvPvZ",
    "shopid": "289796446",
    "itemid": "49859716861",
    "offer_link": "https://s.shopee.com.br/60OgpRvPvZ"
  },
  {
    "slug": "6VKxQMtVug",
    "shopid": "1024858829",
    "itemid": "22998660344",
    "offer_link": "https://s.shopee.com.br/6VKxQMtVug"
  },
  {
    "slug": "6L1XE3u9Ff",
    "shopid": "1263364177",
    "itemid": "20198000747",
    "offer_link": "https://s.shopee.com.br/6L1XE3u9Ff"
  },
  {
    "slug": "4Ax2e52OeG",
    "shopid": "1314293823",
    "itemid": "22094032770",
    "offer_link": "https://s.shopee.com.br/4Ax2e52OeG"
  },
  {
    "slug": "40dcRm31zF",
    "shopid": "1455490500",
    "itemid": "58204730158",
    "offer_link": "https://s.shopee.com.br/40dcRm31zF"
  },
  {
    "slug": "4VZt2h17yM",
    "shopid": "761647073",
    "itemid": "58256439593",
    "offer_link": "https://s.shopee.com.br/4VZt2h17yM"
  },
  {
    "slug": "4LGSqO1lJL",
    "shopid": "832702330",
    "itemid": "22593967188",
    "offer_link": "https://s.shopee.com.br/4LGSqO1lJL"
  },
  {
    "slug": "4qCjRIzrIS",
    "shopid": "1713632798",
    "itemid": "58252935781",
    "offer_link": "https://s.shopee.com.br/4qCjRIzrIS"
  },
  {
    "slug": "4ftJF00UdR",
    "shopid": "1580145778",
    "itemid": "58251846770",
    "offer_link": "https://s.shopee.com.br/4ftJF00UdR"
  },
  {
    "slug": "5ApZpuyacY",
    "shopid": "967211054",
    "itemid": "23299372913",
    "offer_link": "https://s.shopee.com.br/5ApZpuyacY"
  },
  {
    "slug": "50W9dbzDxX",
    "shopid": "437061636",
    "itemid": "19096967339",
    "offer_link": "https://s.shopee.com.br/50W9dbzDxX"
  }
];
  // ─────────────────────────────────────────────────────────

  let progress = {};
  let csvRows  = [];
  try { progress = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch(e) {}
  try { csvRows  = JSON.parse(localStorage.getItem(CSV_KEY)     || '[]'); } catch(e) {}

  const save = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    localStorage.setItem(CSV_KEY,     JSON.stringify(csvRows));
  };

  // overlay
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;bottom:0;right:0;width:500px;max-height:380px;overflow-y:auto;background:#111;color:#0f0;font:12px monospace;z-index:2147483647;padding:10px 14px;border-top:3px solid #0f0;border-left:3px solid #0f0';
  document.body.appendChild(box);
  const log = (msg, c='#0f0') => {
    const d = document.createElement('div');
    d.style.color = c; d.textContent = msg;
    box.appendChild(d); box.scrollTop = box.scrollHeight;
  };

  const exportCsv = () => {
    if (!csvRows.length) { log('Nenhum dado para CSV', '#f90'); return; }
    const header = 'slug,nome,preco,preco_original,desconto_pct,avaliacao,vendidos,estoque,tem_video,url,descricao';
    const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const body = csvRows.map(r =>
      [r.slug, r.nome, r.preco, r.precoOrig, r.desconto, r.avaliacao,
       r.vendidos, r.estoque, r.temVideo, r.urlFinal, r.descricao]
      .map(esc).join(',')
    ).join('\n');
    const blob = new Blob(['\ufeff' + header + '\n' + body], { type: 'text/csv;charset=utf-8' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob), download: 'shopee_videos.csv'
    });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    log(`\n📥 shopee_videos.csv (${csvRows.length} linhas)`, '#0ff');
  };

  const pending = PRODUTOS.filter(p => !progress[p.slug] || progress[p.slug] === 'timeout');

  const feitos = PRODUTOS.length - pending.length;
  log(`Total: ${PRODUTOS.length} | Feitos: ${feitos} | Pendentes: ${pending.length}`, '#ff0');

  if (!pending.length) {
    log('Tudo processado! Gerando CSV...', '#0f0');
    exportCsv();
    return;
  }

  const downloadBlob = async (url, filename) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const blob = await res.blob();
    const burl = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), { href: burl, download: filename });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(burl), 15000);
  };

  let ok = 0, sem = 0, erro = 0, timeout = 0;

  for (let i = 0; i < pending.length; i++) {
    const prod = pending[i];
    const { slug, shopid, itemid } = prod;
    log(`\n[${i+1}/${pending.length}] ${slug} (shop=${shopid} item=${itemid})`);

    try {
      await sleep(1500 + Math.random() * 1500);

      const res = await fetch(`/api/v4/item/get?itemid=${itemid}&shopid=${shopid}`, { credentials: 'include' });
      const j = await res.json().catch(() => null);

      if (!j?.data) {
        log('  ✗ API sem dados', '#f90');
        progress[slug] = 'erro'; save(); erro++;
        await human(); continue;
      }

      const d = j.data;

      const nome      = (d.name || '').replace(/[\r\n]+/g, ' ');
      const precoRaw  = d.price || d.price_min || 0;
      const origRaw   = d.price_before_discount || 0;
      const preco     = (precoRaw / 100000).toFixed(2);
      const precoOrig = origRaw ? (origRaw / 100000).toFixed(2) : preco;
      const desconto  = origRaw ? (((origRaw - precoRaw) / origRaw) * 100).toFixed(0) + '%' : '0%';
      const avaliacao = d.item_rating?.rating_star?.toFixed(1) || '';
      const vendidos  = d.historical_sold || d.sold || 0;
      const estoque   = d.stock || 0;
      const descricao = (d.description || '').replace(/[\r\n\t]+/g, ' ').slice(0, 500);
      const urlFinal  = `https://shopee.com.br/product/${shopid}/${itemid}`;
      const temVideo  = !!(d.video_info_list?.length);

      log(`  📦 ${nome.slice(0,45)} | R$${preco} | ⭐${avaliacao} | 🛒${vendidos}`, '#0ff');

      // ── vídeo via API ──────────────────────────────────────
      const vlist = d.video_info_list;
      let videoUrl = null;

      if (vlist?.length) {
        const v = vlist[0];
        videoUrl =
          v?.formats?.sort((a,b) => (b.width||0) - (a.width||0))?.[0]?.url ||
          v?.default_format?.url || null;
      }

      if (!videoUrl) {
        log('  — sem vídeo na API', '#888');
        sem++;
      } else {
        log('  baixando vídeo...', '#ff0');
        await downloadBlob(videoUrl, slug + '.mp4');
        log('  ✓ ' + slug + '.mp4', '#0f0');
        ok++;
      }

      csvRows = csvRows.filter(r => r.slug !== slug);
      csvRows.push({ slug, nome, preco, precoOrig, desconto, avaliacao, vendidos, estoque, temVideo, urlFinal, descricao });
      progress[slug] = 'ok';
      save();

    } catch(e) {
      log(`  ✗ ERRO: ${e.message}`, '#f00');
      progress[slug] = 'erro'; save(); erro++;
    }

    await human();
  }

  log(`\n══════════════════════════════`, '#ff0');
  log(`✓ vídeos baixados : ${ok}`,            '#0f0');
  log(`— sem vídeo       : ${sem}`,            '#888');
  log(`⟳ timeout (retry) : ${timeout}`,        timeout ? '#f90' : '#555');
  log(`✗ erros           : ${erro}`,            erro    ? '#f00' : '#555');
  log(`══════════════════════════════`, '#ff0');

  exportCsv();

  log('\nPara resetar: localStorage.removeItem("shopee_dl_progress"); localStorage.removeItem("shopee_csv_data")', '#555');
})();