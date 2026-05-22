{
const LINKS = [{"product": "https://shopee.com.br/product/552896405/16692338189", "offer": "https://s.shopee.com.br/gN7WGIjdk"}, {"product": "https://shopee.com.br/product/1429781525/23394276680", "offer": "https://s.shopee.com.br/qgXiZI6In"}, {"product": "https://shopee.com.br/product/594157579/21599248399", "offer": "https://s.shopee.com.br/10zxusHSxq"}, {"product": "https://shopee.com.br/product/1295467768/55050251437", "offer": "https://s.shopee.com.br/1BJO7BGpct"}, {"product": "https://shopee.com.br/product/313660590/22893738408", "offer": "https://s.shopee.com.br/1LcoJUGCHw"}, {"product": "https://shopee.com.br/product/363220493/23994288266", "offer": "https://s.shopee.com.br/1VwEVnFYwz"}, {"product": "https://shopee.com.br/product/395166866/23994387054", "offer": "https://s.shopee.com.br/1gFei6Evc2"}, {"product": "https://shopee.com.br/product/1023760886/22996121313", "offer": "https://s.shopee.com.br/1qZ4uPEIH5"}, {"product": "https://shopee.com.br/product/313660590/22893873080", "offer": "https://s.shopee.com.br/20sV6iDew8"}, {"product": "https://shopee.com.br/product/512962451/23193680985", "offer": "https://s.shopee.com.br/2BBvJ1D1bB"}, {"product": "https://shopee.com.br/product/832036467/22892833180", "offer": "https://s.shopee.com.br/2LVLVKCOGE"}, {"product": "https://shopee.com.br/product/1585429562/22599143898", "offer": "https://s.shopee.com.br/2VolhdBkvH"}, {"product": "https://shopee.com.br/product/463957248/58200593634", "offer": "https://s.shopee.com.br/2g8BtwB7aK"}, {"product": "https://shopee.com.br/product/716194498/23699364867", "offer": "https://s.shopee.com.br/2qRc6FAUFN"}, {"product": "https://shopee.com.br/product/407760070/49603251115", "offer": "https://s.shopee.com.br/30l2IY9quQ"}, {"product": "https://shopee.com.br/product/392260640/22394412338", "offer": "https://s.shopee.com.br/3B4SUr9DZT"}, {"product": "https://shopee.com.br/product/415175805/22392992790", "offer": "https://s.shopee.com.br/3LNshA8aEW"}, {"product": "https://shopee.com.br/product/1220444950/23798560672", "offer": "https://s.shopee.com.br/3VhItT7wtZ"}, {"product": "https://shopee.com.br/product/1168608130/22298032643", "offer": "https://s.shopee.com.br/3g0j5m7JYc"}, {"product": "https://shopee.com.br/product/461633669/21098519637", "offer": "https://s.shopee.com.br/3qK9I56gDf"}, {"product": "https://shopee.com.br/product/771750144/21797631048", "offer": "https://s.shopee.com.br/40dZUO62si"}, {"product": "https://shopee.com.br/product/876866734/22494391157", "offer": "https://s.shopee.com.br/4Awzgh5PXl"}, {"product": "https://shopee.com.br/product/694125365/23493849040", "offer": "https://s.shopee.com.br/4LGPt04mCo"}, {"product": "https://shopee.com.br/product/347988064/9212570285", "offer": "https://s.shopee.com.br/4VZq5J48rr"}, {"product": "https://shopee.com.br/product/1620426618/58200509252", "offer": "https://s.shopee.com.br/4ftGHc3VWu"}, {"product": "https://shopee.com.br/product/353891630/20698275228", "offer": "https://s.shopee.com.br/4qCgTv2sBx"}, {"product": "https://shopee.com.br/product/1064041485/58201523970", "offer": "https://s.shopee.com.br/50W6gE2Er0"}, {"product": "https://shopee.com.br/product/1508524367/23798655797", "offer": "https://s.shopee.com.br/5ApWsX1bW3"}, {"product": "https://shopee.com.br/product/1045085918/23798710869", "offer": "https://s.shopee.com.br/5L8x4q0yB6"}, {"product": "https://shopee.com.br/product/448670448/23593588164", "offer": "https://s.shopee.com.br/5VSNH90Kq9"}, {"product": "https://shopee.com.br/product/482840775/41158748466", "offer": "https://s.shopee.com.br/5flnTRzhVC"}, {"product": "https://shopee.com.br/product/288105257/20697639735", "offer": "https://s.shopee.com.br/5q5Dfkz4AF"}, {"product": "https://shopee.com.br/product/511410160/20697751196", "offer": "https://s.shopee.com.br/60Ods3yQpI"}, {"product": "https://shopee.com.br/product/761647073/58250773364", "offer": "https://s.shopee.com.br/6Ai44MxnUL"}, {"product": "https://shopee.com.br/product/1006215031/27780089302", "offer": "https://s.shopee.com.br/6L1UGfxA9O"}, {"product": "https://shopee.com.br/product/1350045638/26980788215", "offer": "https://s.shopee.com.br/6VKuSywWoR"}, {"product": "https://shopee.com.br/product/1429781525/23598536942", "offer": "https://s.shopee.com.br/6feKfHvtTU"}, {"product": "https://shopee.com.br/product/644980753/22494391164", "offer": "https://s.shopee.com.br/6pxkravG8X"}, {"product": "https://shopee.com.br/product/419111099/23393729993", "offer": "https://s.shopee.com.br/70HB3tucna"}, {"product": "https://shopee.com.br/product/1575474912/22794220302", "offer": "https://s.shopee.com.br/7AabGCtzSd"}, {"product": "https://shopee.com.br/product/999239250/40319243537", "offer": "https://s.shopee.com.br/7Ku1SVtM7g"}, {"product": "https://shopee.com.br/product/1249391293/58253988189", "offer": "https://s.shopee.com.br/7VDReosimj"}, {"product": "https://shopee.com.br/product/392545055/21399888983", "offer": "https://s.shopee.com.br/7fWrr7s5Rm"}, {"product": "https://shopee.com.br/product/391739739/22892802242", "offer": "https://s.shopee.com.br/7pqI3QrS6p"}, {"product": "https://shopee.com.br/product/740111576/23392973710", "offer": "https://s.shopee.com.br/809iFjqols"}, {"product": "https://shopee.com.br/product/445101578/23193518683", "offer": "https://s.shopee.com.br/8AT8S2qBQv"}, {"product": "https://shopee.com.br/product/960891164/22098878065", "offer": "https://s.shopee.com.br/8KmYeLpY5y"}, {"product": "https://shopee.com.br/product/1424278396/58203349918", "offer": "https://s.shopee.com.br/8V5yqeoul1"}, {"product": "https://shopee.com.br/product/296363855/22197373105", "offer": "https://s.shopee.com.br/8fPP2xoHQ4"}, {"product": "https://shopee.com.br/product/465623800/18099356042", "offer": "https://s.shopee.com.br/8pipFGne57"}, {"product": "https://shopee.com.br/product/331720585/13985458428", "offer": "https://s.shopee.com.br/902FRZn0kA"}, {"product": "https://shopee.com.br/product/395166866/21678240017", "offer": "https://s.shopee.com.br/9ALfdsmNPD"}, {"product": "https://shopee.com.br/product/436104412/19450049961", "offer": "https://s.shopee.com.br/9Kf5qBlk4G"}, {"product": "https://shopee.com.br/product/358104043/18099720897", "offer": "https://s.shopee.com.br/9UyW2Ul6jJ"}, {"product": "https://shopee.com.br/product/1243683750/20599839417", "offer": "https://s.shopee.com.br/9fHwEnkTOM"}, {"product": "https://shopee.com.br/product/1553736756/23799198110", "offer": "https://s.shopee.com.br/9pbMR6jq3P"}, {"product": "https://shopee.com.br/product/1240652277/58251614409", "offer": "https://s.shopee.com.br/9zumdPjCiS"}, {"product": "https://shopee.com.br/product/1510602247/22794028329", "offer": "https://s.shopee.com.br/AAECpiiZNV"}, {"product": "https://shopee.com.br/product/1099068336/58251084924", "offer": "https://s.shopee.com.br/AKXd21hw2Y"}, {"product": "https://shopee.com.br/product/1601586606/58201048170", "offer": "https://s.shopee.com.br/AUr3EKhIhb"}, {"product": "https://shopee.com.br/product/1006215031/24442629738", "offer": "https://s.shopee.com.br/BQqvLKdfc"}, {"product": "https://shopee.com.br/product/1177903362/20697874559", "offer": "https://s.shopee.com.br/17Qj2LH0b"}, {"product": "https://shopee.com.br/product/1110883009/19797673158", "offer": "https://s.shopee.com.br/W3hJxJMzi"}, {"product": "https://shopee.com.br/product/644980753/58203925589", "offer": "https://s.shopee.com.br/LkH7eK0Kh"}, {"product": "https://shopee.com.br/product/1003085235/23798128210", "offer": "https://s.shopee.com.br/qgXiZI6Jo"}, {"product": "https://shopee.com.br/product/343762483/23093103982", "offer": "https://s.shopee.com.br/gN7WGIjen"}, {"product": "https://shopee.com.br/product/1110883009/22498129343", "offer": "https://s.shopee.com.br/1BJO7BGpdu"}, {"product": "https://shopee.com.br/product/344896374/23093848660", "offer": "https://s.shopee.com.br/10zxusHSyt"}, {"product": "https://shopee.com.br/product/961638733/42424923537", "offer": "https://s.shopee.com.br/1VwEVnFYy0"}, {"product": "https://shopee.com.br/product/969508885/23597689185", "offer": "https://s.shopee.com.br/1LcoJUGCIz"}, {"product": "https://shopee.com.br/product/616222685/22895570776", "offer": "https://s.shopee.com.br/1qZ4uPEII6"}, {"product": "https://shopee.com.br/product/1283669740/26075587372", "offer": "https://s.shopee.com.br/1gFei6Evd5"}, {"product": "https://shopee.com.br/product/1521699574/23898692172", "offer": "https://s.shopee.com.br/2BBvJ1D1cC"}, {"product": "https://shopee.com.br/product/1032838083/22298151589", "offer": "https://s.shopee.com.br/20sV6iDexB"}, {"product": "https://shopee.com.br/product/407760070/40723848736", "offer": "https://s.shopee.com.br/2VolhdBkwI"}, {"product": "https://shopee.com.br/product/386191827/11674191849", "offer": "https://s.shopee.com.br/2LVLVKCOHH"}, {"product": "https://shopee.com.br/product/1142052307/58257288693", "offer": "https://s.shopee.com.br/2qRc6FAUGO"}, {"product": "https://shopee.com.br/product/394786209/8065374301", "offer": "https://s.shopee.com.br/2g8BtwB7bN"}, {"product": "https://shopee.com.br/product/424928448/23329181038", "offer": "https://s.shopee.com.br/3B4SUr9DaU"}, {"product": "https://shopee.com.br/product/847598018/17191520281", "offer": "https://s.shopee.com.br/30l2IY9qvT"}, {"product": "https://shopee.com.br/product/1547995492/22599244908", "offer": "https://s.shopee.com.br/3VhItT7wua"}, {"product": "https://shopee.com.br/product/1494351957/22898873410", "offer": "https://s.shopee.com.br/3LNshA8aFZ"}, {"product": "https://shopee.com.br/product/463228698/22392982563", "offer": "https://s.shopee.com.br/3qK9I56gEg"}, {"product": "https://shopee.com.br/product/462426918/23794330101", "offer": "https://s.shopee.com.br/3g0j5m7JZf"}, {"product": "https://shopee.com.br/product/386263059/20797743913", "offer": "https://s.shopee.com.br/4Awzgh5PYm"}, {"product": "https://shopee.com.br/product/1515741369/58205199120", "offer": "https://s.shopee.com.br/40dZUO62tl"}, {"product": "https://shopee.com.br/product/1534896372/21199833759", "offer": "https://s.shopee.com.br/4VZq5J48ss"}, {"product": "https://shopee.com.br/product/800864347/19897425032", "offer": "https://s.shopee.com.br/4LGPt04mDr"}, {"product": "https://shopee.com.br/product/1003085235/23392567785", "offer": "https://s.shopee.com.br/4qCgTv2sCy"}, {"product": "https://shopee.com.br/product/461633669/14241654483", "offer": "https://s.shopee.com.br/4ftGHc3VXx"}, {"product": "https://shopee.com.br/product/1077139873/44451988896", "offer": "https://s.shopee.com.br/5ApWsX1bX4"}, {"product": "https://shopee.com.br/product/518931513/58201522771", "offer": "https://s.shopee.com.br/50W6gE2Es3"}, {"product": "https://shopee.com.br/product/512962451/22794296585", "offer": "https://s.shopee.com.br/5VSNH90KrA"}, {"product": "https://shopee.com.br/product/643719371/15082197029", "offer": "https://s.shopee.com.br/5L8x4q0yC9"}, {"product": "https://shopee.com.br/product/347988064/7078628796", "offer": "https://s.shopee.com.br/5q5Dfkz4BG"}, {"product": "https://shopee.com.br/product/304357487/10964824524", "offer": "https://s.shopee.com.br/5flnTRzhWF"}, {"product": "https://shopee.com.br/product/1499852820/22199186045", "offer": "https://s.shopee.com.br/6Ai44MxnVM"}, {"product": "https://shopee.com.br/product/491125955/23098743173", "offer": "https://s.shopee.com.br/60Ods3yQqL"}, {"product": "https://shopee.com.br/product/313984108/23093525798", "offer": "https://s.shopee.com.br/6VKuSywWpS"}, {"product": "https://shopee.com.br/product/1103946075/19899586753", "offer": "https://s.shopee.com.br/6L1UGfxAAR"}];
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const results = [];

// User-Agents realistas
const UAS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
];

document.getElementById("__sdl")?.remove();
const P = document.createElement("div");
P.id = "__sdl";
P.style.cssText = "position:fixed;right:12px;bottom:12px;width:520px;max-height:380px;overflow-y:auto;background:#0a0a0a;color:#0f0;font:11px monospace;padding:14px;border-radius:10px;z-index:2147483647;white-space:pre-wrap;border:1px solid #0f0;";
document.body.appendChild(P);
const log = (m,c="#0f0")=>{ const d=document.createElement("div"); d.style.color=c; d.textContent=m; P.appendChild(d); P.scrollTop=99999; };

const getRandomUA = () => UAS[Math.floor(Math.random() * UAS.length)];
const randomDelay = (min, max) => min + Math.random() * (max - min);

(async()=>{
  log("▶ Extraindo vídeos de "+LINKS.length+" produtos...","#ff0");
  log("⚠ Evitando bloqueios com delays adaptativos","#ff9");
  
  let successCount = 0;
  let failCount = 0;
  let blocked = false;
  
  for(let i=0;i<LINKS.length;i++){
    if(blocked) {
      log("🚫 BLOQUEADO por Shopee. Pausando...","#f44");
      await sleep(15000); // pausa 15s se bloqueado
      blocked = false;
    }
    
    const {product,offer} = LINKS[i];
    const m = product.match(/\/product\/(\d+)\/(\d+)/);
    if(!m){ 
      results.push({slug:offer.split("/").pop(),offer,src:null,status:"invalid_url"}); 
      failCount++;
      continue; 
    }
    
    const [,shopid,itemid] = m;
    const slug = offer.split("/").pop();
    
    try{
      // Delay adaptativo: aumenta com # de requests
      const baseDelay = 800 + (i % 20) * 150;
      const jitter = randomDelay(baseDelay, baseDelay + 500);
      await sleep(jitter);
      
      // Request com headers realistas
      const opts = {
        credentials:"include",
        headers: {
          "User-Agent": getRandomUA(),
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "pt-BR,pt;q=0.9",
          "Referer": "https://shopee.com.br/",
          "X-Requested-With": "XMLHttpRequest",
        }
      };
      
      const r = await fetch("/api/v4/item/get?itemid="+itemid+"&shopid="+shopid, opts);
      
      // Detecta rate limit
      if(r.status === 429) {
        blocked = true;
        log("⚠ Rate limit (429) detectado!","#f90");
        results.push({slug,offer,src:null,status:"rate_limited"});
        failCount++;
        continue;
      }
      
      if(!r.ok) {
        log("  [err "+(i+1)+"] HTTP "+r.status+" - "+slug,"#f88");
        results.push({slug,offer,src:null,status:"http_"+r.status});
        failCount++;
        continue;
      }
      
      const j = await r.json();
      const v = j?.data?.video_info_list?.[0];
      const src = v?.video_url?.replace("{0}","mp4")||v?.default_format?.url||v?.url||null;
      
      results.push({slug,offer,src,status:src?"ok":"no_video"});
      
      const icon = src ? "✔" : "—";
      const color = src ? "#0f0" : "#888";
      log("  [" + String(i+1).padStart(3) + "/"+LINKS.length+"] " + slug.padEnd(16) + " " + icon, color);
      
      successCount += src ? 1 : 0;
      failCount += src ? 0 : 1;
      
    }catch(e){
      log("  [err "+(i+1)+"] "+e.message+" - "+slug,"#f44");
      results.push({slug,offer,src:null,status:"fetch_error",error:e.message});
      failCount++;
    }
    
    // Pausa maior a cada 15 itens
    if((i+1) % 15 === 0 && i+1 < LINKS.length){
      const pauseTime = 5000 + Math.random() * 3000;
      log("  ⏸ pausa " + (pauseTime/1000).toFixed(1) + "s (proteção anti-bot)...","#ff0");
      await sleep(pauseTime);
    }
  }
  
  // Download resultado
  const blob = new Blob([JSON.stringify(results,null,2)],{type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "shopee_videos.json";
  document.body.appendChild(a); 
  a.click(); 
  setTimeout(()=>a.remove(),3000);
  
  log("","#0f0");
  log("✔ CONCLUÍDO: "+successCount+" vídeos encontrados, "+failCount+" sem vídeo","#0f0");
  log("✔ shopee_videos.json salvo! Agora rode o Python.","#ff0");
})();
}
