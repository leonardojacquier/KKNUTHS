import"./style-CsVGQoPs.js";const n={instagram:"https://www.instagram.com/gnhimportacionespy/",facebook:"https://www.facebook.com/edzon.camilomazzonrtto",tiktok:"https://www.tiktok.com/@gnh",whatsapp:"https://wa.me/595985311031?text=Hola,%20quiero%20más%20información"},u=[{ciudad:"Ciudad del Este",dir:"Av. República del Perú km 7, CDE 100101",tel:"0995 360060",share:"https://share.google/OAtbh8akZyeNATtUM",q:"Av. República del Perú km 7, Ciudad del Este, Paraguay"},{ciudad:"Asunción · Ñemby",dir:"Acceso Sur, Ñemby 111210",tel:"",share:"https://share.google/DB7b1OL7m1ISorPhY",q:"Acceso Sur, Ñemby, Paraguay"}];function v(e="footer-slot"){const a=document.getElementById(e);if(!a)return;a.innerHTML=`
    <footer class="bg-ink text-white/70">
      <!-- tiendas con mapa -->
      <div class="mx-auto max-w-6xl px-6 pt-14">
        <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Nuestras tiendas</h4>
        <div class="mt-5 grid gap-6 md:grid-cols-2">
          ${u.map(o=>`
            <div class="foot-store">
              <iframe class="foot-map" src="https://www.google.com/maps?q=${encodeURIComponent(o.q)}&output=embed"
                      loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Mapa ${o.ciudad}"></iframe>
              <div class="foot-store-info">
                <p class="font-semibold text-white">${o.ciudad}</p>
                <p class="text-sm">${o.dir}</p>
                ${o.tel?`<p class="text-sm">Tel: <a href="tel:+595${o.tel.replace(/\D/g,"").replace(/^0/,"")}" class="hover:text-orange">${o.tel}</a></p>`:""}
                <a href="${o.share}" target="_blank" rel="noopener" class="text-orange hover:underline text-sm">Ver en Google Maps →</a>
              </div>
            </div>`).join("")}
        </div>
      </div>

      <!-- marca + redes + contacto -->
      <div class="mx-auto max-w-6xl px-6 py-12 grid gap-10 md:grid-cols-3 border-t border-white/10 mt-12">
        <div>
          <img src="/img/gnh-logo.svg" alt="GNH" class="h-10 w-auto"
               onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'font-display text-2xl font-bold text-white',textContent:'GNH'}))">
          <p class="mt-4 text-sm max-w-xs">Generando Nuevos Horizontes — comercio internacional, distribución y logística.</p>
          <div class="mt-5 flex gap-3">
            <a href="${n.instagram}" target="_blank" rel="noopener" aria-label="Instagram" class="foot-social">${b}</a>
            <a href="${n.facebook}" target="_blank" rel="noopener" aria-label="Facebook" class="foot-social">${f}</a>
            <a href="${n.tiktok}" target="_blank" rel="noopener" aria-label="TikTok" class="foot-social">${x}</a>
          </div>
        </div>
        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Contacto</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="tel:+595985311031" class="hover:text-orange">+595 985 311031</a></li>
            <li><a href="mailto:adm@gnhorizons.com" class="hover:text-orange">adm@gnhorizons.com</a></li>
            <li><a href="${n.whatsapp}" target="_blank" rel="noopener" class="hover:text-orange">WhatsApp</a></li>
          </ul>
        </div>
        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Seguinos</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="${n.instagram}" target="_blank" rel="noopener" class="hover:text-orange">Instagram</a></li>
            <li><a href="${n.facebook}" target="_blank" rel="noopener" class="hover:text-orange">Facebook</a></li>
            <li><a href="${n.tiktok}" target="_blank" rel="noopener" class="hover:text-orange">TikTok</a></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10 py-6 text-center text-xs text-white/40">
        © {year} Grupo GNH — Reservados todos los derechos · Paraguay · Brasil
      </div>
    </footer>`,a.innerHTML=a.innerHTML.replace("{year}",String(new Date().getFullYear()));const t=document.createElement("a");t.href=n.whatsapp,t.target="_blank",t.rel="noopener",t.setAttribute("aria-label","WhatsApp"),t.className="wa-float",t.innerHTML=$,document.body.appendChild(t)}const b='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s0 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.58 2.2 15.2 2.2 12s0-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.2 8.8 2.2 12 2.2m0 1.8c-3.15 0-3.5 0-4.7.07-.9.04-1.4.2-1.72.32-.43.17-.74.37-1.06.7-.32.32-.52.63-.7 1.06-.12.32-.28.82-.32 1.72C3.2 8.5 3.2 8.85 3.2 12s0 3.5.07 4.7c.04.9.2 1.4.32 1.72.17.43.37.74.7 1.06.32.32.63.52 1.06.7.32.12.82.28 1.72.32 1.2.06 1.55.07 4.7.07s3.5 0 4.7-.07c.9-.04 1.4-.2 1.72-.32.43-.17.74-.37 1.06-.7.32-.32.52-.63.7-1.06.12-.32.28-.82.32-1.72.06-1.2.07-1.55.07-4.7s0-3.5-.07-4.7c-.04-.9-.2-1.4-.32-1.72a2.9 2.9 0 0 0-.7-1.06 2.9 2.9 0 0 0-1.06-.7c-.32-.12-.82-.28-1.72-.32C15.5 4 15.15 4 12 4m0 3.06A4.94 4.94 0 1 1 12 16.94 4.94 4.94 0 0 1 12 7.06m0 1.8a3.14 3.14 0 1 0 0 6.28 3.14 3.14 0 0 0 0-6.28m5.14-.9a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3"/></svg>',f='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 8h3V4h-3a4.5 4.5 0 0 0-4.5 4.5V11H7v4h2.5v7h4v-7H17l.7-4h-4.2V8.8A.8.8 0 0 1 14 8z"/></svg>',x='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 3c.3 2 1.6 3.6 3.5 3.9v2.4c-1.3.1-2.6-.3-3.7-1v5.9a5.6 5.6 0 1 1-5.6-5.6c.3 0 .5 0 .8.05v2.5a3.1 3.1 0 1 0 2.2 3V3z"/></svg>',$='<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5 13.7c-.2.6-1.2 1.2-1.7 1.2-.4.1-1 .1-1.6-.1a13 13 0 0 1-5.9-5.2c-.7-1.1-1.1-2.4-.6-3.1.2-.4.6-.6 1-.6h.7c.2 0 .5-.1.7.5l1 2.3c.1.2 0 .4-.1.6l-.5.7c-.2.2-.3.4-.1.7a9.6 9.6 0 0 0 3.6 3.2c.3.1.5.1.7-.1l.8-1c.2-.3.4-.2.7-.1l2.2 1c.2.1.4.2.4.4 0 .1 0 .8-.3 1.6z"/></svg>',m="595985311031",g=e=>`https://wa.me/${m}?text=${encodeURIComponent(e)}`,c=[{id:"equipos",title:"Equipos",icon:"gear",blurb:"Reglas láser, bombas de concreto, allanadoras, grúas, generadores y más.",groups:[{title:"Construcción",products:[{name:"Regla Láser Vibratoria WS940",img:"../img/prod/ws940.png",note:"Nivelación láser de pisos de concreto de alta precisión."},{name:"Bomba Transportadora de Concreto",img:"../img/prod/bomba-cemento.png",note:"Bombeo y transporte de concreto con caudal estable y operación continua."},{name:"Allanadora de Concreto 1 m",img:"../img/prod/allanadora.png",note:"Alisado y pulido de pisos de concreto. Ancho de trabajo de 1 metro."},{name:"Cortadora de Piso",img:"../img/prod/cortadora.png",note:"Corte de juntas en concreto y asfalto con disco diamantado."}]},{title:"Movimentación",products:[{name:"Grúa Araña",brand:"GNH",img:"../img/prod/grua-arana.png",note:"Grúa compacta de orugas para elevación de precisión en espacios reducidos."},{name:"Elevador de Dos Columnas",img:"../img/prod/elevador.png",note:"Plataforma de elevación de personal de dos mástiles, uso industrial."}]},{title:"Industria",products:[{name:"Ensayo a Compresión HST-YES2000",img:"../img/prod/compresion.png",note:"Prensa digital para ensayos de resistencia a la compresión. Control de calidad."},{name:"Motor Diésel 4HZD",img:"../img/prod/motor.png",note:"Motor diésel industrial de alto desempeño para generación y usos estacionarios."},{name:"Grupo Electrógeno Diésel 38 kVA",img:"../img/prod/generador.png",note:"Generador trifásico 400 V / 50 Hz, cabina súper silenciosa."}]}]},{id:"aditivos",title:"Aditivos",icon:"flask",blurb:"Aditivos y soluciones químicas para construcción.",products:[]},{id:"fletes",title:"Fletes",icon:"truck",blurb:"Transporte y fletes de carga con cobertura regional.",products:[{name:"Transporte de Cargas",brand:"FletePar",note:"Fletes con cobertura regional y trazabilidad total, del origen al destino."}]},{id:"morteros",title:"Morteros",icon:"grid",blurb:"Revoques y morteros industrializados.",products:[]},{id:"cementos",title:"Cementos",icon:"layers",blurb:"Cemento de alto desempeño para toda obra.",products:[]}],y={hook:'<path d="M5 21V5.5L11 3v18M5 21h6M11 7h8.5M19.5 7v4.5"/><path d="M21.5 14a2.2 2.2 0 1 1-4.4 0"/>',flask:'<path d="M10 3h4M11 3v5.2L5.6 17.5A2 2 0 0 0 7.4 21h9.2a2 2 0 0 0 1.8-3.5L13 8.2V3"/><path d="M8.2 15h7.6"/>',truck:'<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',layers:'<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13.5l9 5 9-5"/>',grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',arrow:'<path d="M4 12h15M13 6l6 6-6 6"/>',doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',gear:'<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2.1 2.1M16.9 16.9L19 19M19 5l-2.1 2.1M7.1 16.9L5 19"/>'},i=(e,a="")=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${a}">${y[e]??""}</svg>`;function d(e){const a=`Hola, me interesa: ${e.name}${e.brand?" ("+e.brand+")":""}`;return`
    <article class="v-card">
      <div class="v-card-media">${e.img?`<img src="${e.img}" alt="${e.name}" loading="lazy">`:`<span class="ph">${e.name}</span>`}</div>
      <div class="v-card-body">
        ${e.brand?`<span class="v-brand">${e.brand}</span>`:""}
        <h3 class="v-name">${e.name}</h3>
        ${e.note?`<p class="v-note">${e.note}</p>`:""}
        <a class="v-cta" href="${g(a)}" target="_blank" rel="noopener" data-ev="product" data-detail="${e.name}">Consultar ${i("arrow","v-cta-i")}</a>
      </div>
    </article>`}function w(e){return`
    <article class="v-cat-panel" data-cat="${e.id}" tabindex="0" role="button" aria-label="Ver productos de ${e.title}">
      <div class="ghost">${i(e.icon)}</div>
      <div class="p-ic">${i(e.icon)}</div>
      <span class="t-vert">${e.title}</span>
      <div class="p-body">
        <h3>${e.title}</h3>
        <p>${e.blurb}</p>
        <span class="p-go">Ver productos ${i("arrow")}</span>
      </div>
    </article>`}function l(e,a=!1){const t=c.find(s=>s.id===e);if(!t)return;document.querySelectorAll(".v-cat-panel").forEach(s=>s.classList.toggle("is-active",s.dataset.cat===e)),document.querySelectorAll(".v-chip").forEach(s=>s.classList.toggle("is-active",s.dataset.cat===e));let o;t.groups&&t.groups.length?o=t.groups.map(s=>`
      <div class="v-subgroup">
        <h3 class="v-subtitle">${s.title}</h3>
        <div class="v-rail">${s.products.map(d).join("")}</div>
      </div>`).join(""):t.products&&t.products.length?o=`<div class="v-rail">${t.products.map(d).join("")}</div>`:o=`
      <div class="v-empty">
        <p>Pronto sumaremos productos de esta línea.</p>
        <a class="btn-empty" href="${g("Hola, quiero consultar sobre "+t.title)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      </div>`;const r=document.getElementById("v-products");r.innerHTML=`
    <div class="v-products-head"><div class="v-cat-ic">${i(t.icon)}</div><h2>${t.title}</h2></div>
    ${o}`,r.classList.remove("revealing"),r.offsetWidth,r.classList.add("revealing"),a&&r.scrollIntoView({behavior:"smooth",block:"start"})}function k(){const e=document.getElementById("catalog");e.innerHTML=`
    <div class="v-deck">${c.map(w).join("")}</div>
    <div class="v-products" id="v-products"></div>`,e.querySelectorAll(".v-cat-panel").forEach(t=>{const o=t.dataset.cat;t.addEventListener("click",()=>l(o,!0)),t.addEventListener("keydown",r=>{(r.key==="Enter"||r.key===" ")&&(r.preventDefault(),l(o,!0))})});const a=document.getElementById("cat-chips");a.innerHTML=c.map(t=>`<button class="v-chip" data-cat="${t.id}">${t.title}</button>`).join(""),a.querySelectorAll(".v-chip").forEach(t=>t.addEventListener("click",()=>l(t.dataset.cat,!0))),l(c[0].id)}const p=[];function M(){const e=document.getElementById("promos");if(!p.length){e.style.display="none";return}e.innerHTML=`
    <div class="v-promo-band">
      ${p.map(a=>`
        <div class="v-promo">
          <h3>${a.title}</h3><p>${a.text}</p>
          ${a.url?`<a href="${a.url}" target="_blank" rel="noopener">Ver más →</a>`:""}
        </div>`).join("")}
    </div>`}function C(){const e=document.getElementById("quote-form"),a=document.getElementById("quote-status");e.addEventListener("submit",t=>{t.preventDefault();const o=new FormData(e),r=String(o.get("nombre")??"").trim(),s=String(o.get("whatsapp")??"").trim();if(!r||!s){a.textContent="Completá nombre y WhatsApp.",a.className="text-sm text-red-600";return}const h=`Cotización GNH%0ANombre: ${r}%0AEmpresa: ${o.get("empresa")??""}%0AProducto: ${o.get("producto")??""}%0AMensaje: ${o.get("mensaje")??""}`;window.open(`https://wa.me/${m}?text=${h}`,"_blank"),a.textContent="¡Gracias! Te redirigimos a WhatsApp.",a.className="text-sm text-green-600",e.reset()})}k();M();C();v();
