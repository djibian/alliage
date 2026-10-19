/* Alliage Quarto v0.4. Pas d'IA intégrée et aucune publication. */
(() => {
  "use strict";
  const ext = typeof browser !== "undefined" ? browser : chrome;
  if (document.getElementById("pedagolab-at-v04")) return;
  const root = document.createElement("aside");
  root.id = "pedagolab-at-v04";
  root.setAttribute("aria-label", "Atelier Alliage");
  const shadow = root.attachShadow({mode:"closed"});
  const style = document.createElement("style");
  style.textContent = `
    :host{all:initial} *,*::before,*::after{box-sizing:border-box}
    .box{font:13px/1.4 system-ui,sans-serif;color:#17212b;background:white;border:1px solid #7e8a94;
      border-radius:12px;box-shadow:0 8px 34px #0019;max-height:calc(100vh - 26px);overflow:auto}
    header{padding:12px 14px;border-bottom:1px solid #ddd;font-size:16px;font-weight:700}
    main{padding:12px 14px} label{display:block;font-weight:650;margin-top:11px}
    input,textarea{display:block;width:100%;font:inherit;border:1px solid #a0acb5;border-radius:6px;
      background:#fff;color:#13202d;padding:8px;margin-top:4px}
    textarea{resize:vertical;min-height:52px}
    button{cursor:pointer;font:inherit;border:1px solid #77828c;border-radius:6px;background:#eef2f5;
      color:#18222a;padding:7px 9px;margin:9px 7px 0 0}
    button:disabled{cursor:not-allowed;opacity:.5}
    blockquote{border-left:3px solid #617f99;margin:9px 0;padding:6px 9px;background:#f5f8fa;
      overflow-wrap:anywhere;font-size:14px}
    .note{color:#48535b;font-size:12px;margin-top:7px}
    .status{border-top:1px solid #ddd;padding:8px 14px;font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}
    .buttons{margin-top:7px} .selected{padding:8px;border:1px solid #d7dee2;margin-top:8px}
    a{color:#164f89;font-size:13px} .guard{font-size:11px;color:#43576a}
  `;
  const box = document.createElement("div");box.className="box";
  const heading=document.createElement("header");heading.textContent="Alliage · Atelier Quarto";
  const main=document.createElement("main");
  const blurb=document.createElement("div");blurb.className="note";
  blurb.textContent="Choisis un passage sur la page. Les propositions sont saisies manuellement dans cette v0.4 (pas encore d'IA).";
  const quoted=document.createElement("blockquote");quoted.textContent="Aucun passage sélectionné";
  const anchor=document.createElement("div");anchor.className="guard";
  const authLabel=document.createElement("label");authLabel.textContent="Jeton local temporaire";
  const token=document.createElement("input");token.type="password";token.autocomplete="off";token.placeholder="Coller le jeton affiché dans le terminal";
  authLabel.appendChild(token);
  const aLabel=document.createElement("label");aLabel.textContent="Proposition A (remplacement exact)";
  const a=document.createElement("input");a.type="text";a.maxLength=150;a.placeholder="Ex. cinq ressources";aLabel.appendChild(a);
  const bLabel=document.createElement("label");bLabel.textContent="Proposition B (remplacement exact)";
  const b=document.createElement("input");b.type="text";b.maxLength=150;b.placeholder="Ex. cinq fichiers proposés";bLabel.appendChild(b);
  const test=document.createElement("button");test.textContent="Créer et vérifier A/B";test.disabled=true;
  const open=document.createElement("button");open.textContent="Comparer dans Firefox";open.disabled=true;
  const decisions=document.createElement("div");decisions.className="selected";decisions.hidden=true;
  const chooseA=document.createElement("button");chooseA.textContent="Garder A";
  const chooseB=document.createElement("button");chooseB.textContent="Garder B";
  const reject=document.createElement("button");reject.textContent="Rejeter les deux";
  const context=document.createElement("button");context.textContent="Copier le contexte";context.disabled=true;
  const note=document.createElement("div");note.className="note";
  note.textContent="Choisir conserve une décision dans le dossier expérimental, sans modifier le dépôt et sans publier.";
  decisions.append(chooseA,chooseB,reject,note);
  const status=document.createElement("div");status.className="status";
  status.textContent="Étape 1 : sélectionner du texte dans la Mission 02.";
  main.append(blurb,quoted,anchor,authLabel,aLabel,bLabel,test,open,context,decisions);
  box.append(heading,main,status);shadow.append(style,box);root.style.cssText=`position:fixed;top:13px;right:13px;width:min(370px,calc(100vw - 26px));z-index:2147483647;`;
  document.documentElement.appendChild(root);
  let selection=null;let experiment=null;let selectedRange=null;
  let layers=[];
  function setStatus(s){status.textContent=s;}
  function getBlock(node){let el=node.nodeType===Node.ELEMENT_NODE?node:node.parentElement;
    while(el&&!el.matches("p,li,h1,h2,h3,h4,h5,h6,blockquote,td,th,pre"))el=el.parentElement;return el;}
  function cssPath(el){let parts=[];while(el&&el.nodeType===Node.ELEMENT_NODE){
    if(el.id){parts.unshift("#"+CSS.escape(el.id));break;}
    const tag=el.localName;if(!tag)break;
    const siblings=el.parentElement?Array.from(el.parentElement.children).filter(x=>x.localName===tag):[el];
    const n=siblings.indexOf(el)+1;parts.unshift(tag+(siblings.length>1?`:nth-of-type(${n})`:""));el=el.parentElement;
  }return parts.join(" > ");}
  function blockOffset(block,node,offset){let r=document.createRange();r.selectNodeContents(block);r.setEnd(node,offset);return r.toString().length;}
  function paint(){layers.forEach(x=>x.remove());layers=[];if(!selectedRange)return;
    for(let rect of selectedRange.getClientRects()){
      if(rect.width<1||rect.height<1)continue;
      let div=document.createElement("div");div.style.cssText=`position:fixed;z-index:2147483646;pointer-events:none;
        background:#ffc24748;outline:1px solid #ad7410;left:${rect.left}px;top:${rect.top}px;
        width:${rect.width}px;height:${rect.height}px`;
      document.documentElement.appendChild(div);layers.push(div);
    }}
  function capture(){const sel=window.getSelection();if(!sel||sel.isCollapsed||!sel.rangeCount||!sel.toString().trim())return;
    const range=sel.getRangeAt(0);if(root.contains(range.commonAncestorContainer))return;
    const start=getBlock(range.startContainer),end=getBlock(range.endContainer);
    const mainEl=document.querySelector("main")||document.body;
    if(!start||start!==end||!mainEl.contains(start))return setStatus("Sélection multi-bloc non prise en charge.");
    const a0=blockOffset(start,range.startContainer,range.startOffset);
    const b0=blockOffset(start,range.endContainer,range.endOffset);
    const full=start.textContent||"";const exact=range.toString();
    const consistent=full.slice(a0,b0)===exact;
    if(!consistent)return setStatus("Sélection imprécise, refusée.");
    selection={schema:"pedagolab.selection.v0",page:{url:location.href,title:document.title},
      dom:{cssPath:cssPath(start),startUtf16:a0,endUtf16:b0,blockText:full,exactMatchesBlockSlice:true},
      quote:{exact,prefix:full.slice(Math.max(0,a0-48),a0),suffix:full.slice(b0,b0+48)},
      source:{status:"UNRESOLVED",message:"Correspondance .qmd non établie"}};
    selectedRange=range.cloneRange();quoted.textContent=exact;
    anchor.textContent=selection.dom.cssPath+` · ${a0}–${b0}`;test.disabled=false;context.disabled=false;
    experiment=null;open.disabled=true;decisions.hidden=true;
    setStatus("Ancre capturée. Saisis deux propositions, puis lance la vérification Quarto.");paint();
  }
  document.addEventListener("mouseup",()=>setTimeout(capture,0));
  document.addEventListener("keyup",()=>setTimeout(capture,0));
  window.addEventListener("scroll",paint,{passive:true,capture:true});
  window.addEventListener("resize",paint);
  async function call(action,payload){return ext.runtime.sendMessage({action,token:token.value.trim(),payload});}
  test.addEventListener("click",async()=>{
    if(!selection||!token.value.trim()||!a.value.trim()||!b.value.trim())return setStatus("Sélection, jeton et deux propositions nécessaires.");
    test.disabled=true;setStatus("Rendu en cours dans les copies locales ; aucune publication…");
    try{const res=await call("experiment",{selection,optionA:a.value.trim(),optionB:b.value.trim()});
      if(res.status!=="RENDER_VERIFIED_LOCAL")return setStatus("Refus : "+(res.detail||res.status));
      experiment=res;open.disabled=false;decisions.hidden=false;
      setStatus("Rendu local vérifié. Compare A/B, puis reviens ici pour choisir. La provenance HTML publiée reste non vérifiée.");
    }catch(e){setStatus("Erreur du pont local : "+String(e));}
    finally{test.disabled=false;}
  });
  open.addEventListener("click",()=>{if(experiment)window.open(experiment.comparison_url,"_blank","noopener,noreferrer");});
  for(const [btn,choice] of [[chooseA,"A"],[chooseB,"B"],[reject,"REJETER"]]){
    btn.addEventListener("click",async()=>{
      if(!experiment)return;btn.disabled=true;
      try{const res=await call("decision",{id:experiment.id,choice});
        setStatus(res.status==="SELECTED_EXPERIMENTAL_ONLY"||res.status==="REJECTED_LOCAL"
          ?`Décision enregistrée : ${choice}. Aucun dépôt modifié, aucune publication.`
          :"Refus : "+(res.detail||res.status));
      }catch(e){setStatus("Décision non enregistrée : "+String(e));}finally{btn.disabled=false;}
    });
  }
  context.addEventListener("click",async()=>{
    if(!selection)return;
    const draft=`Activité Quarto : ${document.title}\nPassage sélectionné : « ${selection.quote.exact} »\nContexte : « ${selection.dom.blockText} »\nEmplacement : ${selection.dom.cssPath}\nDemande : propose deux reformulations pédagogiquement équivalentes, en conservant les consignes et le sens. Réponds avec exactement deux formulations de remplacement courtes : A et B.`;
    try{await navigator.clipboard.writeText(draft);setStatus("Contexte copié. Tu peux le soumettre à une IA séparée, puis coller A/B ici.");}
    catch(e){setStatus("Impossible de copier : "+String(e));}
  });
})();
