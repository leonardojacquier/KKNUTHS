import"./style-CuqOwscc.js";const r={instagram:"https://www.instagram.com/gnhimportacionespy/",facebook:"https://www.facebook.com/edzon.camilomazzonrtto",tiktok:"https://www.tiktok.com/@gnh",whatsapp:"https://wa.me/595985311031?text=Hola,%20quiero%20más%20información"},h=[{ciudad:"Ciudad del Este",dir:"Dirección — CDE",maps:"#"},{ciudad:"Asunción",dir:"Dirección — Asunción",maps:"#"}];function p(t="footer-slot"){const e=document.getElementById(t);if(!e)return;e.innerHTML=`
    <footer class="bg-ink text-white/70">
      <div class="mx-auto max-w-6xl px-6 py-14 grid gap-10 md:grid-cols-3">
        <div>
          <div class="flex items-center gap-3">
            <img src="/img/gnh-logo.svg" alt="GNH" class="h-10 w-auto"
                 onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'font-display text-2xl font-bold text-white',textContent:'GNH'}))">
          </div>
          <p class="mt-4 text-sm max-w-xs">Generando Nuevos Horizontes — comercio internacional, distribución y logística.</p>
          <div class="mt-5 flex gap-3">
            <a href="${r.instagram}" target="_blank" rel="noopener" aria-label="Instagram" class="foot-social">${v}</a>
            <a href="${r.facebook}" target="_blank" rel="noopener" aria-label="Facebook" class="foot-social">${g}</a>
            <a href="${r.tiktok}" target="_blank" rel="noopener" aria-label="TikTok" class="foot-social">${u}</a>
          </div>
        </div>

        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Tiendas</h4>
          <ul class="mt-4 space-y-4 text-sm">
            ${h.map(n=>`
              <li>
                <p class="font-semibold text-white">${n.ciudad}</p>
                <p>${n.dir}</p>
                <a href="${n.maps}" target="_blank" rel="noopener" class="text-orange hover:underline">Ver en el mapa →</a>
              </li>`).join("")}
          </ul>
        </div>

        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Contacto</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="tel:+595985311031" class="hover:text-orange">+595 985 311031</a></li>
            <li><a href="mailto:adm@gnhorizons.com" class="hover:text-orange">adm@gnhorizons.com</a></li>
            <li><a href="${r.whatsapp}" target="_blank" rel="noopener" class="hover:text-orange">WhatsApp</a></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10 py-6 text-center text-xs text-white/40">
        © {year} Grupo GNH — Reservados todos los derechos · Paraguay · Brasil
      </div>
    </footer>`;const o=e.querySelector(".border-t");o&&(o.innerHTML=o.innerHTML.replace("{year}",String(new Date().getFullYear())));const a=document.createElement("a");a.href=r.whatsapp,a.target="_blank",a.rel="noopener",a.setAttribute("aria-label","WhatsApp"),a.className="wa-float",a.innerHTML=f,document.body.appendChild(a)}const v='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s0 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.58 2.2 15.2 2.2 12s0-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.2 8.8 2.2 12 2.2m0 1.8c-3.15 0-3.5 0-4.7.07-.9.04-1.4.2-1.72.32-.43.17-.74.37-1.06.7-.32.32-.52.63-.7 1.06-.12.32-.28.82-.32 1.72C3.2 8.5 3.2 8.85 3.2 12s0 3.5.07 4.7c.04.9.2 1.4.32 1.72.17.43.37.74.7 1.06.32.32.63.52 1.06.7.32.12.82.28 1.72.32 1.2.06 1.55.07 4.7.07s3.5 0 4.7-.07c.9-.04 1.4-.2 1.72-.32.43-.17.74-.37 1.06-.7.32-.32.52-.63.7-1.06.12-.32.28-.82.32-1.72.06-1.2.07-1.55.07-4.7s0-3.5-.07-4.7c-.04-.9-.2-1.4-.32-1.72a2.9 2.9 0 0 0-.7-1.06 2.9 2.9 0 0 0-1.06-.7c-.32-.12-.82-.28-1.72-.32C15.5 4 15.15 4 12 4m0 3.06A4.94 4.94 0 1 1 12 16.94 4.94 4.94 0 0 1 12 7.06m0 1.8a3.14 3.14 0 1 0 0 6.28 3.14 3.14 0 0 0 0-6.28m5.14-.9a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3"/></svg>',g='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 8h3V4h-3a4.5 4.5 0 0 0-4.5 4.5V11H7v4h2.5v7h4v-7H17l.7-4h-4.2V8.8A.8.8 0 0 1 14 8z"/></svg>',u='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 3c.3 2 1.6 3.6 3.5 3.9v2.4c-1.3.1-2.6-.3-3.7-1v5.9a5.6 5.6 0 1 1-5.6-5.6c.3 0 .5 0 .8.05v2.5a3.1 3.1 0 1 0 2.2 3V3z"/></svg>',f='<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5 13.7c-.2.6-1.2 1.2-1.7 1.2-.4.1-1 .1-1.6-.1a13 13 0 0 1-5.9-5.2c-.7-1.1-1.1-2.4-.6-3.1.2-.4.6-.6 1-.6h.7c.2 0 .5-.1.7.5l1 2.3c.1.2 0 .4-.1.6l-.5.7c-.2.2-.3.4-.1.7a9.6 9.6 0 0 0 3.6 3.2c.3.1.5.1.7-.1l.8-1c.2-.3.4-.2.7-.1l2.2 1c.2.1.4.2.4.4 0 .1 0 .8-.3 1.6z"/></svg>',l="595985311031",b=t=>`https://wa.me/${l}?text=${encodeURIComponent(t)}`,c=[{id:"equipos",title:"Equipos",icon:"hook",docLabel:"Catálogo",docUrl:"",products:[{name:"Grúa araña",brand:"GNH",note:"Elevación de precisión"},{name:"Equipo — placeholder",note:"AJUSTAR"}]},{id:"aditivos",title:"Aditivos",icon:"flask",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Aditivo — placeholder",brand:"Camargo Química",note:"AJUSTAR"}]},{id:"fletes",title:"Fletes",icon:"truck",products:[{name:"Transporte de cargas",brand:"FletePar",note:"Cobertura regional"}]},{id:"cemento",title:"Cemento",icon:"layers",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Cemento — placeholder",brand:"Itambé",note:"AJUSTAR"}]},{id:"morteros",title:"Morteros",icon:"grid",docLabel:"Ficha técnica",docUrl:"",products:[{name:"Mortero — placeholder",brand:"Intonaco",note:"AJUSTAR"}]}],$={hook:'<path d="M5 21V5.5L11 3v18M5 21h6M11 7h8.5M19.5 7v4.5"/><path d="M21.5 14a2.2 2.2 0 1 1-4.4 0"/>',flask:'<path d="M10 3h4M11 3v5.2L5.6 17.5A2 2 0 0 0 7.4 21h9.2a2 2 0 0 0 1.8-3.5L13 8.2V3"/><path d="M8.2 15h7.6"/>',truck:'<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',layers:'<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13.5l9 5 9-5"/>',grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',arrow:'<path d="M4 12h15M13 6l6 6-6 6"/>',doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>'},s=(t,e="")=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${e}">${$[t]??""}</svg>`;function x(t){const e=`Hola, me interesa: ${t.name}${t.brand?" ("+t.brand+")":""}`;return`
    <article class="v-card">
      <div class="v-card-media">${t.img?`<img src="${t.img}" alt="${t.name}" loading="lazy">`:`<span class="ph">${t.name}</span>`}</div>
      <div class="v-card-body">
        ${t.brand?`<span class="v-brand">${t.brand}</span>`:""}
        <h3 class="v-name">${t.name}</h3>
        ${t.note?`<p class="v-note">${t.note}</p>`:""}
        <a class="v-cta" href="${b(e)}" target="_blank" rel="noopener" data-ev="product" data-detail="${t.name}">Consultar ${s("arrow","v-cta-i")}</a>
      </div>
    </article>`}function w(t){const e=t.docUrl?`<a class="v-doc" href="${t.docUrl}" target="_blank" rel="noopener" data-ev="doc" data-detail="${t.id}">${s("doc","v-doc-i")} ${t.docLabel}</a>`:t.docLabel?`<span class="v-doc v-doc-off">${s("doc","v-doc-i")} ${t.docLabel} — próximamente</span>`:"";return`
    <section class="v-cat" id="cat-${t.id}">
      <div class="v-cat-head">
        <div class="v-cat-ic">${s(t.icon)}</div>
        <h2 class="v-cat-title">${t.title}</h2>
        ${e}
      </div>
      <div class="v-rail">${t.products.map(x).join("")}</div>
    </section>`}function k(){const t=document.getElementById("catalog");t.innerHTML=c.map(w).join("");const e=document.getElementById("cat-chips");e.innerHTML=c.map(o=>`<a class="v-chip" href="#cat-${o.id}">${o.title}</a>`).join("")}const i=[];function y(){const t=document.getElementById("promos");if(!i.length){t.style.display="none";return}t.innerHTML=`
    <div class="v-promo-band">
      ${i.map(e=>`
        <div class="v-promo">
          <h3>${e.title}</h3><p>${e.text}</p>
          ${e.url?`<a href="${e.url}" target="_blank" rel="noopener">Ver más →</a>`:""}
        </div>`).join("")}
    </div>`}function M(){const t=document.getElementById("quote-form"),e=document.getElementById("quote-status");t.addEventListener("submit",o=>{o.preventDefault();const a=new FormData(t),n=String(a.get("nombre")??"").trim(),d=String(a.get("whatsapp")??"").trim();if(!n||!d){e.textContent="Completá nombre y WhatsApp.",e.className="text-sm text-red-600";return}const m=`Cotización GNH%0ANombre: ${n}%0AEmpresa: ${a.get("empresa")??""}%0AProducto: ${a.get("producto")??""}%0AMensaje: ${a.get("mensaje")??""}`;window.open(`https://wa.me/${l}?text=${m}`,"_blank"),e.textContent="¡Gracias! Te redirigimos a WhatsApp.",e.className="text-sm text-green-600",t.reset()})}k();y();M();p();
