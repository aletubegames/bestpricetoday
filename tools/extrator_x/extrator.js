(()=>{
  const STORAGE='xpi_data';
  let captured=[];
  let step=0;
  let active=false;

  const panel=document.createElement('div');
  panel.style.cssText='position:fixed;bottom:0;right:0;width:480px;max-height:420px;background:#111;color:#0f0;font:12px monospace;z-index:2147483647;border-top:3px solid #ff0050;border-left:3px solid #ff0050;display:flex;flex-direction:column';

  panel.innerHTML=`
    <div style="background:#1a1a1a;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #333;flex-shrink:0">
      <span style="color:#ff0050;font-weight:bold">🎯 XPath Inspector</span>
      <div style="display:flex;gap:6px">
        <button id="xpi-toggle" style="background:#1d6b1d;color:#0f0;border:none;border-radius:3px;padding:3px 10px;cursor:pointer;font:12px monospace">▶ Ativar captura</button>
        <button id="xpi-gen" style="background:#333;color:#ff0;border:none;border-radius:3px;padding:3px 10px;cursor:pointer;font:12px monospace">Gerar JS final</button>
        <button id="xpi-clear" style="background:#333;color:#f66;border:none;border-radius:3px;padding:3px 10px;cursor:pointer;font:12px monospace">Limpar</button>
      </div>
    </div>
    <div id="xpi-log" style="flex:1;overflow-y:auto;padding:8px 12px"></div>
    <div style="background:#0a0a0a;border-top:1px solid #333;padding:6px 12px;flex-shrink:0">
      <textarea id="xpi-out" style="width:100%;height:80px;background:#0a0a0a;color:#ff0;border:none;resize:none;font:11px monospace;outline:none" placeholder="Output aparece aqui..."></textarea>
    </div>
  `;
  document.body.appendChild(panel);

  const log=panel.querySelector('#xpi-log');
  const out=panel.querySelector('#xpi-out');
  const toggleBtn=panel.querySelector('#xpi-toggle');

  function addLog(step,el,smart,full){
    const d=document.createElement('div');
    d.style.cssText='margin:4px 0;padding:6px 8px;background:#1a1a1a;border-left:3px solid #333;border-radius:2px';
    const tag=el.tagName.toLowerCase();
    const txt=(el.textContent||'').trim().slice(0,40);
    const id=el.id?'#'+el.id:'';
    const testid=el.getAttribute('data-testid')||'';
    const aria=el.getAttribute('aria-label')||'';
    d.innerHTML=`
      <div style="color:#ff0050;font-size:11px">Passo ${step}: <span id="lbl-${step}" style="color:#fff;cursor:pointer" title="clique para renomear">${el.getAttribute('data-step-name')||'clique para nomear'}</span></div>
      <div style="color:#0af">&lt;${tag}${id?' id="'+id+'"':''}${testid?' data-testid="'+testid+'"':''}${aria?' aria-label="'+aria+'"':''}&gt;${txt?txt.slice(0,30)+'…':''}</div>
      <div style="color:#ff0;font-size:10px;margin-top:2px">🎯 Smart: ${smart}</div>
      <div style="color:#0f0;font-size:10px;margin-top:1px">📌 Full:  ${full.slice(0,80)}${full.length>80?'…':''}</div>
    `;
    log.appendChild(d);
    log.scrollTop=log.scrollHeight;
    d.querySelector('#lbl-'+step).addEventListener('click',()=>{
      const n=prompt('Nome para este elemento (ex: btnUpload):');
      if(n){
        d.querySelector('#lbl-'+step).textContent=n;
        captured[step-1].name=n;
      }
    });
  }

  function getSmartXPath(el){
    if(el.id) return '//*[@id="'+el.id+'"]';
    const testid=el.getAttribute('data-testid');
    if(testid) return '//*[@data-testid="'+testid+'"]';
    const aria=el.getAttribute('aria-label');
    if(aria) return '//'+el.tagName.toLowerCase()+'[@aria-label="'+aria+'"]';
    const txt=(el.textContent||'').trim().slice(0,30);
    if(txt && el.tagName!=='DIV') return '//'+el.tagName.toLowerCase()+'[normalize-space()="'+txt+'"]';
    const role=el.getAttribute('role');
    if(role) return '//'+el.tagName.toLowerCase()+'[@role="'+role+'"]';
    return null;
  }

  function getFullXPath(el){
    const parts=[];
    while(el && el.nodeType===1){
      let idx=1;
      let sib=el.previousSibling;
      while(sib){if(sib.nodeType===1&&sib.tagName===el.tagName)idx++;sib=sib.previousSibling;}
      parts.unshift(el.tagName.toLowerCase()+'['+idx+']');
      el=el.parentNode;
    }
    return '/'+parts.join('/');
  }

  function onClick(e){
    if(!active) return;
    if(panel.contains(e.target)) return;
    e.stopPropagation();
    e.preventDefault();
    step++;
    const smart=getSmartXPath(e.target)||'(sem atributo estável)';
    const full=getFullXPath(e.target);
    captured.push({step,name:'elemento_'+step,smart,full,tag:e.target.tagName.toLowerCase()});
    e.target.style.outline='2px solid #ff0050';
    setTimeout(()=>e.target.style.outline='',1500);
    addLog(step,e.target,smart,full);
  }

  toggleBtn.addEventListener('click',()=>{
    active=!active;
    toggleBtn.style.background=active?'#6b1d1d':'#1d6b1d';
    toggleBtn.style.color=active?'#f66':'#0f0';
    toggleBtn.textContent=active?'⏹ Parar captura':'▶ Ativar captura';
    if(active){
      document.addEventListener('click',onClick,true);
      const d=document.createElement('div');
      d.style.cssText='margin:4px 0;color:#ff0;font-size:11px';
      d.textContent='◉ Captura ativa — clique nos elementos da página';
      log.appendChild(d);
    } else {
      document.removeEventListener('click',onClick,true);
    }
  });

  panel.querySelector('#xpi-clear').addEventListener('click',()=>{
    captured=[];step=0;log.innerHTML='';out.value='';
  });

  panel.querySelector('#xpi-gen').addEventListener('click',()=>{
    if(!captured.length){out.value='// Nenhum elemento capturado ainda.';return;}
    let js='// XPaths capturados — substitua no tiktok_post.js\n\n';
    js+='// ── Versão ROBUSTA (recomendada) ──\n';
    captured.forEach(c=>{
      js+='const '+c.name+' = await waitXP(\''+c.smart+'\');\n';
    });
    js+='\n// ── Versão POSIÇÃO (fallback) ──\n';
    captured.forEach(c=>{
      js+='// '+c.name+': \''+c.full.slice(0,80)+'\'\n';
    });
    out.value=js;
    out.select();
    document.execCommand('copy');
    out.style.borderTop='2px solid #0f0';
    setTimeout(()=>out.style.borderTop='',1000);
  });

  const d=document.createElement('div');
  d.style.cssText='padding:6px 0;color:#888;font-size:11px';
  d.textContent='Clique em "Ativar captura" e depois clique nos elementos da página.';
  log.appendChild(d);
})();