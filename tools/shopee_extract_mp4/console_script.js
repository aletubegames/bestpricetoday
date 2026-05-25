(async () => {
  const STORAGE_KEY = 'shopee_dl_progress';
  const CSV_KEY     = 'shopee_csv_data';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const human = () => sleep(3000 + Math.random() * 3000);

  // ── PRODUTOS (gerado pelo generate_script.py) ────────────
  const PRODUTOS = [
  {
    "slug": "4Ax3GKm307",
    "shopid": "1501144405",
    "itemid": "23194950027",
    "offer_link": "https://s.shopee.com.br/4Ax3GKm307"
  },
  {
    "slug": "50WAFrisJI",
    "shopid": "464590540",
    "itemid": "58209590119",
    "offer_link": "https://s.shopee.com.br/50WAFrisJI"
  },
  {
    "slug": "5ApaSAiEyL",
    "shopid": "1626133283",
    "itemid": "58208960692",
    "offer_link": "https://s.shopee.com.br/5ApaSAiEyL"
  },
  {
    "slug": "4ftJrFk8zG",
    "shopid": "1328679905",
    "itemid": "58255768158",
    "offer_link": "https://s.shopee.com.br/4ftJrFk8zG"
  },
  {
    "slug": "4qCk3YjVeJ",
    "shopid": "299582074",
    "itemid": "58259333831",
    "offer_link": "https://s.shopee.com.br/4qCk3YjVeJ"
  },
  {
    "slug": "30l5sBqUMy",
    "shopid": "587578299",
    "itemid": "23598568886",
    "offer_link": "https://s.shopee.com.br/30l5sBqUMy"
  },
  {
    "slug": "3B4W4Upr21",
    "shopid": "1340072116",
    "itemid": "22898461699",
    "offer_link": "https://s.shopee.com.br/3B4W4Upr21"
  },
  {
    "slug": "2g8FTZrl2w",
    "shopid": "541804501",
    "itemid": "58207868279",
    "offer_link": "https://s.shopee.com.br/2g8FTZrl2w"
  },
  {
    "slug": "2qRffsr7hz",
    "shopid": "979558874",
    "itemid": "42351035536",
    "offer_link": "https://s.shopee.com.br/2qRffsr7hz"
  },
  {
    "slug": "3g0mfPnx1A",
    "shopid": "1442787125",
    "itemid": "55259766596",
    "offer_link": "https://s.shopee.com.br/3g0mfPnx1A"
  },
  {
    "slug": "3qKCrinJgD",
    "shopid": "1399701658",
    "itemid": "52609416948",
    "offer_link": "https://s.shopee.com.br/3qKCrinJgD"
  },
  {
    "slug": "3LNwGnpDh8",
    "shopid": "594102844",
    "itemid": "58006470123",
    "offer_link": "https://s.shopee.com.br/3LNwGnpDh8"
  },
  {
    "slug": "3VhMT6oaMB",
    "shopid": "1587733934",
    "itemid": "45658530663",
    "offer_link": "https://s.shopee.com.br/3VhMT6oaMB"
  },
  {
    "slug": "70HEdXbGFs",
    "shopid": "681967866",
    "itemid": "41178806100",
    "offer_link": "https://s.shopee.com.br/70HEdXbGFs"
  },
  {
    "slug": "7Aaepqacuv",
    "shopid": "983645094",
    "itemid": "27951088537",
    "offer_link": "https://s.shopee.com.br/7Aaepqacuv"
  },
  {
    "slug": "6feOEvcWvq",
    "shopid": "1551697817",
    "itemid": "23994269065",
    "offer_link": "https://s.shopee.com.br/6feOEvcWvq"
  },
  {
    "slug": "6pxoREbtat",
    "shopid": "705761751",
    "itemid": "23198661449",
    "offer_link": "https://s.shopee.com.br/6pxoREbtat"
  },
  {
    "slug": "7fWvQlYiu4",
    "shopid": "681967866",
    "itemid": "52706391547",
    "offer_link": "https://s.shopee.com.br/7fWvQlYiu4"
  },
  {
    "slug": "7pqLd4Y5Z7",
    "shopid": "824474412",
    "itemid": "23931899885",
    "offer_link": "https://s.shopee.com.br/7pqLd4Y5Z7"
  },
  {
    "slug": "7Ku529Zza2",
    "shopid": "1551697817",
    "itemid": "20698271319",
    "offer_link": "https://s.shopee.com.br/7Ku529Zza2"
  },
  {
    "slug": "7VDVESZMF5",
    "shopid": "542438037",
    "itemid": "21798141466",
    "offer_link": "https://s.shopee.com.br/7VDVESZMF5"
  },
  {
    "slug": "5flr35gKxk",
    "shopid": "681967866",
    "itemid": "54958027125",
    "offer_link": "https://s.shopee.com.br/5flr35gKxk"
  },
  {
    "slug": "5q5HFOfhcn",
    "shopid": "1124636121",
    "itemid": "46607981788",
    "offer_link": "https://s.shopee.com.br/5q5HFOfhcn"
  },
  {
    "slug": "5L90eThbdi",
    "shopid": "369623161",
    "itemid": "16829247820",
    "offer_link": "https://s.shopee.com.br/5L90eThbdi"
  },
  {
    "slug": "5VSQqmgyIl",
    "shopid": "979558874",
    "itemid": "24844165608",
    "offer_link": "https://s.shopee.com.br/5VSQqmgyIl"
  },
  {
    "slug": "6L1XqJdnbw",
    "shopid": "681967866",
    "itemid": "57657873051",
    "offer_link": "https://s.shopee.com.br/6L1XqJdnbw"
  },
  {
    "slug": "6VKy2cdAGz",
    "shopid": "1086519436",
    "itemid": "23197452801",
    "offer_link": "https://s.shopee.com.br/6VKy2cdAGz"
  },
  {
    "slug": "60OhRhf4Hu",
    "shopid": "1228604047",
    "itemid": "23898408578",
    "offer_link": "https://s.shopee.com.br/60OhRhf4Hu"
  },
  {
    "slug": "6Ai7e0eQwx",
    "shopid": "1104180297",
    "itemid": "26107655539",
    "offer_link": "https://s.shopee.com.br/6Ai7e0eQwx"
  },
  {
    "slug": "9fHzoRR6qe",
    "shopid": "603782959",
    "itemid": "50007702992",
    "offer_link": "https://s.shopee.com.br/9fHzoRR6qe"
  },
  {
    "slug": "9pbQ0kQTVh",
    "shopid": "1025213096",
    "itemid": "24898131886",
    "offer_link": "https://s.shopee.com.br/9pbQ0kQTVh"
  },
  {
    "slug": "9Kf9PpSNWc",
    "shopid": "1316980618",
    "itemid": "52758437928",
    "offer_link": "https://s.shopee.com.br/9Kf9PpSNWc"
  },
  {
    "slug": "9UyZc8RkBf",
    "shopid": "905229815",
    "itemid": "23292853843",
    "offer_link": "https://s.shopee.com.br/9UyZc8RkBf"
  },
  {
    "slug": "AKXgbfOZUq",
    "shopid": "880951566",
    "itemid": "22794806088",
    "offer_link": "https://s.shopee.com.br/AKXgbfOZUq"
  },
  {
    "slug": "AUr6nyNw9t",
    "shopid": "1483307846",
    "itemid": "28888735945",
    "offer_link": "https://s.shopee.com.br/AUr6nyNw9t"
  },
  {
    "slug": "9zuqD3PqAo",
    "shopid": "1196446677",
    "itemid": "23793877414",
    "offer_link": "https://s.shopee.com.br/9zuqD3PqAo"
  },
  {
    "slug": "AAEGPMPCpr",
    "shopid": "532620463",
    "itemid": "22197697652",
    "offer_link": "https://s.shopee.com.br/AAEGPMPCpr"
  },
  {
    "slug": "8KmcDzWBYW",
    "shopid": "681967866",
    "itemid": "40007124196",
    "offer_link": "https://s.shopee.com.br/8KmcDzWBYW"
  },
  {
    "slug": "8V62QIVYDZ",
    "shopid": "1499606732",
    "itemid": "23293957278",
    "offer_link": "https://s.shopee.com.br/8V62QIVYDZ"
  },
  {
    "slug": "809lpNXSEU",
    "shopid": "975780170",
    "itemid": "22399429963",
    "offer_link": "https://s.shopee.com.br/809lpNXSEU"
  },
  {
    "slug": "8ATC1gWotX",
    "shopid": "1098585909",
    "itemid": "23992851334",
    "offer_link": "https://s.shopee.com.br/8ATC1gWotX"
  },
  {
    "slug": "902J1DTeCi",
    "shopid": "1651851128",
    "itemid": "58259468957",
    "offer_link": "https://s.shopee.com.br/902J1DTeCi"
  },
  {
    "slug": "9ALjDWT0rl",
    "shopid": "897545291",
    "itemid": "58204266757",
    "offer_link": "https://s.shopee.com.br/9ALjDWT0rl"
  },
  {
    "slug": "8fPScbUusg",
    "shopid": "426378412",
    "itemid": "41528739305",
    "offer_link": "https://s.shopee.com.br/8fPScbUusg"
  },
  {
    "slug": "8pisouUHXj",
    "shopid": "386803813",
    "itemid": "55156312780",
    "offer_link": "https://s.shopee.com.br/8pisouUHXj"
  },
  {
    "slug": "1qZ8U2uvkO",
    "shopid": "1027899621",
    "itemid": "58206430216",
    "offer_link": "https://s.shopee.com.br/1qZ8U2uvkO"
  },
  {
    "slug": "1gFiHjvZ5N",
    "shopid": "703205897",
    "itemid": "29302254546",
    "offer_link": "https://s.shopee.com.br/1gFiHjvZ5N"
  },
  {
    "slug": "1VwI5QwCQM",
    "shopid": "759746224",
    "itemid": "18697662220",
    "offer_link": "https://s.shopee.com.br/1VwI5QwCQM"
  },
  {
    "slug": "1Lcrt7wplL",
    "shopid": "1140971409",
    "itemid": "18099297420",
    "offer_link": "https://s.shopee.com.br/1Lcrt7wplL"
  },
  {
    "slug": "2VopHGsOOa",
    "shopid": "681967866",
    "itemid": "28685749130",
    "offer_link": "https://s.shopee.com.br/2VopHGsOOa"
  },
  {
    "slug": "2LVP4xt1jZ",
    "shopid": "1114798043",
    "itemid": "22498290460",
    "offer_link": "https://s.shopee.com.br/2LVP4xt1jZ"
  },
  {
    "slug": "2BBysetf4Y",
    "shopid": "807834195",
    "itemid": "23596652808",
    "offer_link": "https://s.shopee.com.br/2BBysetf4Y"
  },
  {
    "slug": "20sYgLuIPX",
    "shopid": "215743890",
    "itemid": "17592293854",
    "offer_link": "https://s.shopee.com.br/20sYgLuIPX"
  },
  {
    "slug": "W3ktb00SG",
    "shopid": "603314742",
    "itemid": "26694187942",
    "offer_link": "https://s.shopee.com.br/W3ktb00SG"
  },
  {
    "slug": "LkKhI0dnF",
    "shopid": "532620463",
    "itemid": "23797677332",
    "offer_link": "https://s.shopee.com.br/LkKhI0dnF"
  },
  {
    "slug": "BQuUz1H8E",
    "shopid": "393412132",
    "itemid": "41658528448",
    "offer_link": "https://s.shopee.com.br/BQuUz1H8E"
  },
  {
    "slug": "17UIg1uTD",
    "shopid": "934481538",
    "itemid": "18771976729",
    "offer_link": "https://s.shopee.com.br/17UIg1uTD"
  },
  {
    "slug": "1BJRgoxT6S",
    "shopid": "681967866",
    "itemid": "53653167344",
    "offer_link": "https://s.shopee.com.br/1BJRgoxT6S"
  },
  {
    "slug": "1101UVy6RR",
    "shopid": "1571989376",
    "itemid": "23594254443",
    "offer_link": "https://s.shopee.com.br/1101UVy6RR"
  },
  {
    "slug": "qgbICyjmQ",
    "shopid": "638405707",
    "itemid": "58256198616",
    "offer_link": "https://s.shopee.com.br/qgbICyjmQ"
  },
  {
    "slug": "gNB5tzN7P",
    "shopid": "409390748",
    "itemid": "23493788895",
    "offer_link": "https://s.shopee.com.br/gNB5tzN7P"
  },
  {
    "slug": "4VZtewkmLA",
    "shopid": "1219303534",
    "itemid": "23293839264",
    "offer_link": "https://s.shopee.com.br/4VZtewkmLA"
  },
  {
    "slug": "4LGTSdlPg9",
    "shopid": "578296496",
    "itemid": "20599252009",
    "offer_link": "https://s.shopee.com.br/4LGTSdlPg9"
  },
  {
    "slug": "4Ax3GKm318",
    "shopid": "309054905",
    "itemid": "22194167768",
    "offer_link": "https://s.shopee.com.br/4Ax3GKm318"
  },
  {
    "slug": "40dd41mgM7",
    "shopid": "492581216",
    "itemid": "58256202702",
    "offer_link": "https://s.shopee.com.br/40dd41mgM7"
  },
  {
    "slug": "5ApaSAiEzM",
    "shopid": "1594623535",
    "itemid": "23399388879",
    "offer_link": "https://s.shopee.com.br/5ApaSAiEzM"
  },
  {
    "slug": "50WAFrisKL",
    "shopid": "1232477773",
    "itemid": "25895949709",
    "offer_link": "https://s.shopee.com.br/50WAFrisKL"
  },
  {
    "slug": "4qCk3YjVfK",
    "shopid": "233494148",
    "itemid": "8264636434",
    "offer_link": "https://s.shopee.com.br/4qCk3YjVfK"
  },
  {
    "slug": "4ftJrFk90J",
    "shopid": "1463484615",
    "itemid": "22293819530",
    "offer_link": "https://s.shopee.com.br/4ftJrFk90J"
  },
  {
    "slug": "3B4W4Upr32",
    "shopid": "1029350442",
    "itemid": "55656062557",
    "offer_link": "https://s.shopee.com.br/3B4W4Upr32"
  },
  {
    "slug": "30l5sBqUO1",
    "shopid": "1615518944",
    "itemid": "58008963826",
    "offer_link": "https://s.shopee.com.br/30l5sBqUO1"
  },
  {
    "slug": "2qRffsr7j0",
    "shopid": "1491044633",
    "itemid": "22999005497",
    "offer_link": "https://s.shopee.com.br/2qRffsr7j0"
  },
  {
    "slug": "2g8FTZrl3z",
    "shopid": "448112122",
    "itemid": "25942546248",
    "offer_link": "https://s.shopee.com.br/2g8FTZrl3z"
  },
  {
    "slug": "3qKCrinJhE",
    "shopid": "1003127601",
    "itemid": "57656539787",
    "offer_link": "https://s.shopee.com.br/3qKCrinJhE"
  },
  {
    "slug": "3g0mfPnx2D",
    "shopid": "835273654",
    "itemid": "24647669313",
    "offer_link": "https://s.shopee.com.br/3g0mfPnx2D"
  },
  {
    "slug": "3VhMT6oaNC",
    "shopid": "1156488266",
    "itemid": "49657837082",
    "offer_link": "https://s.shopee.com.br/3VhMT6oaNC"
  },
  {
    "slug": "3LNwGnpDiB",
    "shopid": "290234225",
    "itemid": "22398357106",
    "offer_link": "https://s.shopee.com.br/3LNwGnpDiB"
  },
  {
    "slug": "7Aaepqacvw",
    "shopid": "448654639",
    "itemid": "23498635174",
    "offer_link": "https://s.shopee.com.br/7Aaepqacvw"
  },
  {
    "slug": "70HEdXbGGv",
    "shopid": "913580882",
    "itemid": "22593855144",
    "offer_link": "https://s.shopee.com.br/70HEdXbGGv"
  },
  {
    "slug": "6pxoREbtbu",
    "shopid": "1515141336",
    "itemid": "22094307312",
    "offer_link": "https://s.shopee.com.br/6pxoREbtbu"
  },
  {
    "slug": "6feOEvcWwt",
    "shopid": "1613326394",
    "itemid": "58256053530",
    "offer_link": "https://s.shopee.com.br/6feOEvcWwt"
  },
  {
    "slug": "7pqLd4Y5a8",
    "shopid": "426378412",
    "itemid": "19995489287",
    "offer_link": "https://s.shopee.com.br/7pqLd4Y5a8"
  },
  {
    "slug": "7fWvQlYiv7",
    "shopid": "434137487",
    "itemid": "22719347247",
    "offer_link": "https://s.shopee.com.br/7fWvQlYiv7"
  },
  {
    "slug": "7VDVESZMG6",
    "shopid": "979558874",
    "itemid": "26634367824",
    "offer_link": "https://s.shopee.com.br/7VDVESZMG6"
  },
  {
    "slug": "7Ku529Zzb5",
    "shopid": "508073754",
    "itemid": "23599348819",
    "offer_link": "https://s.shopee.com.br/7Ku529Zzb5"
  },
  {
    "slug": "5q5HFOfhdo",
    "shopid": "498322826",
    "itemid": "58205694476",
    "offer_link": "https://s.shopee.com.br/5q5HFOfhdo"
  },
  {
    "slug": "5flr35gKyn",
    "shopid": "399604109",
    "itemid": "3685599753",
    "offer_link": "https://s.shopee.com.br/5flr35gKyn"
  },
  {
    "slug": "5VSQqmgyJm",
    "shopid": "1583529285",
    "itemid": "22794859890",
    "offer_link": "https://s.shopee.com.br/5VSQqmgyJm"
  },
  {
    "slug": "5L90eThbel",
    "shopid": "426378412",
    "itemid": "48358580737",
    "offer_link": "https://s.shopee.com.br/5L90eThbel"
  },
  {
    "slug": "6VKy2cdAI0",
    "shopid": "1058666705",
    "itemid": "54657379904",
    "offer_link": "https://s.shopee.com.br/6VKy2cdAI0"
  },
  {
    "slug": "6L1XqJdncz",
    "shopid": "866139490",
    "itemid": "22193060864",
    "offer_link": "https://s.shopee.com.br/6L1XqJdncz"
  },
  {
    "slug": "6Ai7e0eQxy",
    "shopid": "239927339",
    "itemid": "58202703589",
    "offer_link": "https://s.shopee.com.br/6Ai7e0eQxy"
  },
  {
    "slug": "60OhRhf4Ix",
    "shopid": "1104180297",
    "itemid": "25370623316",
    "offer_link": "https://s.shopee.com.br/60OhRhf4Ix"
  },
  {
    "slug": "9pbQ0kQTWi",
    "shopid": "681967866",
    "itemid": "41114214520",
    "offer_link": "https://s.shopee.com.br/9pbQ0kQTWi"
  },
  {
    "slug": "9fHzoRR6rh",
    "shopid": "1006215031",
    "itemid": "52354364262",
    "offer_link": "https://s.shopee.com.br/9fHzoRR6rh"
  },
  {
    "slug": "9UyZc8RkCg",
    "shopid": "1157950131",
    "itemid": "54905119793",
    "offer_link": "https://s.shopee.com.br/9UyZc8RkCg"
  },
  {
    "slug": "9Kf9PpSNXf",
    "shopid": "243235332",
    "itemid": "27364817132",
    "offer_link": "https://s.shopee.com.br/9Kf9PpSNXf"
  },
  {
    "slug": "AUr6nyNwAu",
    "shopid": "290234225",
    "itemid": "23498379918",
    "offer_link": "https://s.shopee.com.br/AUr6nyNwAu"
  },
  {
    "slug": "AKXgbfOZVt",
    "shopid": "1206706107",
    "itemid": "58204626361",
    "offer_link": "https://s.shopee.com.br/AKXgbfOZVt"
  },
  {
    "slug": "AAEGPMPCqs",
    "shopid": "1178899059",
    "itemid": "22898051635",
    "offer_link": "https://s.shopee.com.br/AAEGPMPCqs"
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