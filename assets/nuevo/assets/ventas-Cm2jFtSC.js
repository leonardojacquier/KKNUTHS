import"./style-CzJdUt4s.js";import{m}from"./footer-CcsZwzv7.js";const d="595985311031",h=t=>`https://wa.me/${d}?text=${encodeURIComponent(t)}`,c=[{id:"equipos",title:"Equipos",icon:"hook",docLabel:"Catálogo",docUrl:"",products:[{name:"Grúa araña",brand:"GNH",note:"Elevación de precisión"},{name:"Equipo — placeholder",note:"AJUSTAR"}]},{id:"aditivos",title:"Aditivos",icon:"flask",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Aditivo — placeholder",brand:"Camargo Química",note:"AJUSTAR"}]},{id:"fletes",title:"Fletes",icon:"truck",products:[{name:"Transporte de cargas",brand:"FletePar",note:"Cobertura regional"}]},{id:"cemento",title:"Cemento",icon:"layers",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Cemento — placeholder",brand:"Itambé",note:"AJUSTAR"}]},{id:"morteros",title:"Morteros",icon:"grid",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Mortero — placeholder",brand:"Intonaco",note:"AJUSTAR"}]}],p={hook:'<path d="M5 21V5.5L11 3v18M5 21h6M11 7h8.5M19.5 7v4.5"/><path d="M21.5 14a2.2 2.2 0 1 1-4.4 0"/>',flask:'<path d="M10 3h4M11 3v5.2L5.6 17.5A2 2 0 0 0 7.4 21h9.2a2 2 0 0 0 1.8-3.5L13 8.2V3"/><path d="M8.2 15h7.6"/>',truck:'<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',layers:'<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13.5l9 5 9-5"/>',grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',arrow:'<path d="M4 12h15M13 6l6 6-6 6"/>',doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>'},n=(t,e="")=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${e}">${p[t]??""}</svg>`;function v(t){const e=`Hola, me interesa: ${t.name}${t.brand?" ("+t.brand+")":""}`;return`
    <article class="v-card">
      <div class="v-card-media">${t.img?`<img src="${t.img}" alt="${t.name}" loading="lazy">`:`<span class="ph">${t.name}</span>`}</div>
      <div class="v-card-body">
        ${t.brand?`<span class="v-brand">${t.brand}</span>`:""}
        <h3 class="v-name">${t.name}</h3>
        ${t.note?`<p class="v-note">${t.note}</p>`:""}
        <a class="v-cta" href="${h(e)}" target="_blank" rel="noopener" data-ev="product" data-detail="${t.name}">Consultar ${n("arrow","v-cta-i")}</a>
      </div>
    </article>`}function u(t){const e=t.docUrl?`<a class="v-doc" href="${t.docUrl}" target="_blank" rel="noopener" data-ev="doc" data-detail="${t.id}">${n("doc","v-doc-i")} ${t.docLabel}</a>`:t.docLabel?`<span class="v-doc v-doc-off">${n("doc","v-doc-i")} ${t.docLabel} — próximamente</span>`:"";return`
    <section class="v-cat" id="cat-${t.id}">
      <div class="v-cat-head">
        <div class="v-cat-ic">${n(t.icon)}</div>
        <h2 class="v-cat-title">${t.title}</h2>
        ${e}
      </div>
      <div class="v-rail">${t.products.map(v).join("")}</div>
    </section>`}function $(){const t=document.getElementById("catalog");t.innerHTML=c.map(u).join("");const e=document.getElementById("cat-chips");e.innerHTML=c.map(o=>`<a class="v-chip" href="#cat-${o.id}">${o.title}</a>`).join("")}const i=[];function g(){const t=document.getElementById("promos");if(!i.length){t.style.display="none";return}t.innerHTML=`
    <div class="v-promo-band">
      ${i.map(e=>`
        <div class="v-promo">
          <h3>${e.title}</h3><p>${e.text}</p>
          ${e.url?`<a href="${e.url}" target="_blank" rel="noopener">Ver más →</a>`:""}
        </div>`).join("")}
    </div>`}function b(){const t=document.getElementById("quote-form"),e=document.getElementById("quote-status");t.addEventListener("submit",o=>{o.preventDefault();const a=new FormData(t),r=String(a.get("nombre")??"").trim(),s=String(a.get("whatsapp")??"").trim();if(!r||!s){e.textContent="Completá nombre y WhatsApp.",e.className="text-sm text-red-600";return}const l=`Cotización GNH%0ANombre: ${r}%0AEmpresa: ${a.get("empresa")??""}%0AProducto: ${a.get("producto")??""}%0AMensaje: ${a.get("mensaje")??""}`;window.open(`https://wa.me/${d}?text=${l}`,"_blank"),e.textContent="¡Gracias! Te redirigimos a WhatsApp.",e.className="text-sm text-green-600",t.reset()})}$();g();b();m();
