import"./style-Cs5EtRwa.js";const c={instagram:"https://www.instagram.com/gnhimportacionespy/",facebook:"https://www.facebook.com/edzon.camilomazzonrtto",tiktok:"https://www.tiktok.com/@gnh",whatsapp:"https://wa.me/595985311031?text=Hola,%20quiero%20más%20información"},T=[{ciudad:"Ciudad del Este",dir:"Av. República del Perú km 7, CDE 100101",tel:"0995 360060",share:"https://share.google/OAtbh8akZyeNATtUM",q:"Av. República del Perú km 7, Ciudad del Este, Paraguay"},{ciudad:"Asunción · Ñemby",dir:"Acceso Sur, Ñemby 111210",tel:"",share:"https://share.google/DB7b1OL7m1ISorPhY",q:"Acceso Sur, Ñemby, Paraguay"}];function z(e="footer-slot"){const r=document.getElementById(e);if(!r)return;r.innerHTML=`
    <footer class="bg-ink text-white/70">
      <!-- tiendas con mapa -->
      <div class="mx-auto max-w-6xl px-6 pt-14">
        <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Nuestras tiendas</h4>
        <div class="mt-5 grid gap-6 md:grid-cols-2">
          ${T.map(o=>`
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
            <a href="${c.instagram}" target="_blank" rel="noopener" aria-label="Instagram" class="foot-social">${H}</a>
            <a href="${c.facebook}" target="_blank" rel="noopener" aria-label="Facebook" class="foot-social">${I}</a>
            <a href="${c.tiktok}" target="_blank" rel="noopener" aria-label="TikTok" class="foot-social">${B}</a>
          </div>
        </div>
        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Contacto</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="tel:+595985311031" class="hover:text-orange">+595 985 311031</a></li>
            <li><a href="mailto:adm@gnhorizons.com" class="hover:text-orange">adm@gnhorizons.com</a></li>
            <li><a href="${c.whatsapp}" target="_blank" rel="noopener" class="hover:text-orange">WhatsApp</a></li>
          </ul>
        </div>
        <div>
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Seguinos</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="${c.instagram}" target="_blank" rel="noopener" class="hover:text-orange">Instagram</a></li>
            <li><a href="${c.facebook}" target="_blank" rel="noopener" class="hover:text-orange">Facebook</a></li>
            <li><a href="${c.tiktok}" target="_blank" rel="noopener" class="hover:text-orange">TikTok</a></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10 py-6 text-center text-xs text-white/40">
        © {year} Grupo GNH — Reservados todos los derechos · Paraguay · Brasil
      </div>
    </footer>`,r.innerHTML=r.innerHTML.replace("{year}",String(new Date().getFullYear()));const t=document.createElement("a");t.href=c.whatsapp,t.target="_blank",t.rel="noopener",t.setAttribute("aria-label","WhatsApp"),t.className="wa-float",t.innerHTML=j,document.body.appendChild(t)}const H='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s0 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.58 2.2 15.2 2.2 12s0-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.2 8.8 2.2 12 2.2m0 1.8c-3.15 0-3.5 0-4.7.07-.9.04-1.4.2-1.72.32-.43.17-.74.37-1.06.7-.32.32-.52.63-.7 1.06-.12.32-.28.82-.32 1.72C3.2 8.5 3.2 8.85 3.2 12s0 3.5.07 4.7c.04.9.2 1.4.32 1.72.17.43.37.74.7 1.06.32.32.63.52 1.06.7.32.12.82.28 1.72.32 1.2.06 1.55.07 4.7.07s3.5 0 4.7-.07c.9-.04 1.4-.2 1.72-.32.43-.17.74-.37 1.06-.7.32-.32.52-.63.7-1.06.12-.32.28-.82.32-1.72.06-1.2.07-1.55.07-4.7s0-3.5-.07-4.7c-.04-.9-.2-1.4-.32-1.72a2.9 2.9 0 0 0-.7-1.06 2.9 2.9 0 0 0-1.06-.7c-.32-.12-.82-.28-1.72-.32C15.5 4 15.15 4 12 4m0 3.06A4.94 4.94 0 1 1 12 16.94 4.94 4.94 0 0 1 12 7.06m0 1.8a3.14 3.14 0 1 0 0 6.28 3.14 3.14 0 0 0 0-6.28m5.14-.9a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3"/></svg>',I='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 8h3V4h-3a4.5 4.5 0 0 0-4.5 4.5V11H7v4h2.5v7h4v-7H17l.7-4h-4.2V8.8A.8.8 0 0 1 14 8z"/></svg>',B='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 3c.3 2 1.6 3.6 3.5 3.9v2.4c-1.3.1-2.6-.3-3.7-1v5.9a5.6 5.6 0 1 1-5.6-5.6c.3 0 .5 0 .8.05v2.5a3.1 3.1 0 1 0 2.2 3V3z"/></svg>',j='<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5 13.7c-.2.6-1.2 1.2-1.7 1.2-.4.1-1 .1-1.6-.1a13 13 0 0 1-5.9-5.2c-.7-1.1-1.1-2.4-.6-3.1.2-.4.6-.6 1-.6h.7c.2 0 .5-.1.7.5l1 2.3c.1.2 0 .4-.1.6l-.5.7c-.2.2-.3.4-.1.7a9.6 9.6 0 0 0 3.6 3.2c.3.1.5.1.7-.1l.8-1c.2-.3.4-.2.7-.1l2.2 1c.2.1.4.2.4.4 0 .1 0 .8-.3 1.6z"/></svg>',q="595985311031",S=e=>`https://wa.me/${q}?text=${encodeURIComponent(e)}`,h=[{id:"equipos",title:"Equipos",icon:"gear",blurb:"Reglas láser, bombas de concreto, allanadoras, grúas, generadores y más.",groups:[{title:"Construcción",products:[{name:"Regla Láser Vibratoria WS940",img:"../img/prod/ws940.png",note:"Nivelación láser de pisos de concreto de alta precisión."},{name:"Bomba Transportadora de Concreto",img:"../img/prod/bomba-cemento.png",note:"Bombeo y transporte de concreto con caudal estable y operación continua."},{name:"Allanadora de Concreto 1 m",img:"../img/prod/allanadora.png",note:"Alisado y pulido de pisos de concreto. Ancho de trabajo de 1 metro."},{name:"Cortadora de Piso",img:"../img/prod/cortadora.png",note:"Corte de juntas en concreto y asfalto con disco diamantado."},{name:"Máquina de Marcado Vial",img:"../img/prod/marcado.png",note:"Marcación de pavimentos y viales con pintura de alto rendimiento."},{name:"Central de Concreto JBTS20",img:"../img/prod/central-concreto.png",note:"Mezcladora y bomba de concreto sobre remolque. Equipada con motor Cummins, para producción y bombeo continuo en obra."}]},{title:"Movimentación",products:[{name:"Grúa Araña",brand:"GNH",img:"../img/prod/grua-arana.png",note:"Grúas araña de orugas de 1,5 t a 70 t de capacidad. Control remoto e indicador de par incluidos. Brazo extensor y cesto opcionales."},{name:"Mini Excavadora HT15",img:"../img/prod/excavadora.png",note:"Miniexcavadora de orugas con motor Kubota. Balanceo lateral del brazo, cabina y aire acondicionado opcionales."},{name:"Camión Volquete de Orugas",img:"../img/prod/volquete.png",note:"Dumper de orugas para transporte de materiales en obra. Capacidades de 0,5 t y 1,2 t; versión giratoria con motor diésel."},{name:"Carretilla Elevadora Diésel 3,5 t",img:"../img/prod/carretilla.png",note:"Montacargas diésel, capacidad 3,5 t y elevación de 3 m. Dispositivo rotatorio opcional."},{name:"Montacargas Todoterreno 3,5 t",img:"../img/prod/montacargas.png",note:"Montacargas todoterreno 3,5 t para superficies difíciles."},{name:"Apilador Eléctrico",img:"../img/prod/apilador.png",note:"Apiladores eléctricos — capacidades de 1 a 2 t y alturas de 1,6 a 4,5 m."},{name:"Elevador de Dos Columnas",img:"../img/prod/elevador.png",note:"Plataforma de elevación de personal de dos mástiles, uso industrial."}]},{title:"Industria",products:[{name:"Ensayo a Compresión HST-YES2000",img:"../img/prod/compresion.png",note:"Prensa digital para ensayos de resistencia a la compresión. Control de calidad."},{name:"Motor Diésel 4HZD",img:"../img/prod/motor.png",note:"Motor diésel industrial de alto desempeño para generación y usos estacionarios."},{name:"Grupo Electrógeno Diésel 38 kVA",img:"../img/prod/generador.png",note:"Generador trifásico 400 V / 50 Hz, cabina súper silenciosa."}]}]},{id:"aditivos",title:"Aditivos",icon:"flask",blurb:"Aditivos y soluciones químicas para construcción.",products:[]},{id:"fletes",title:"Fletes",icon:"truck",blurb:"Transporte y fletes de carga con cobertura regional.",products:[{name:"Transporte de Cargas",brand:"FletePar",note:"Fletes con cobertura regional y trazabilidad total, del origen al destino."}]},{id:"morteros",title:"Morteros",icon:"grid",blurb:"Revoques y morteros industrializados.",products:[]},{id:"cementos",title:"Cementos",icon:"layers",blurb:"Cemento de alto desempeño para toda obra.",products:[]}],P={hook:'<path d="M5 21V5.5L11 3v18M5 21h6M11 7h8.5M19.5 7v4.5"/><path d="M21.5 14a2.2 2.2 0 1 1-4.4 0"/>',flask:'<path d="M10 3h4M11 3v5.2L5.6 17.5A2 2 0 0 0 7.4 21h9.2a2 2 0 0 0 1.8-3.5L13 8.2V3"/><path d="M8.2 15h7.6"/>',truck:'<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',layers:'<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13.5l9 5 9-5"/>',grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',arrow:'<path d="M4 12h15M13 6l6 6-6 6"/>',doc:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',gear:'<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2.1 2.1M16.9 16.9L19 19M19 5l-2.1 2.1M7.1 16.9L5 19"/>',chevL:'<path d="M15 5l-7 7 7 7"/>',chevR:'<path d="M9 5l7 7-7 7"/>'},l=(e,r="")=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${r}">${P[e]??""}</svg>`,p=[{name:"Plataformas",tag:"Plataforma electro-hidráulica de elevación de personal para trabajos en altura.",img:"../img/prod/plataformas.jpg",cat:"equipos",bleed:!0},{name:"Grúas Araña",tag:"Grúas araña de orugas de 1,5 t a 70 t. Compactas, potentes y de fácil acceso.",cat:"equipos",bleed:!0,videoWebm:"../video/grua.webm",videoMp4:"../video/grua.mp4",poster:"../img/prod/grua-poster.jpg"},{name:"Mini Central de Concreto",tag:"Mezcla y bombeo de concreto en un solo equipo, con motor Cummins.",img:"../img/prod/mini-central.jpg",cat:"equipos",bleed:!0},{name:"Minibomba Eléctrica",tag:"Bomba eléctrica compacta para el transporte de concreto en obra.",img:"../img/prod/minibomba.jpg",imgMobile:"../img/prod/minibomba-mobile.jpg",cat:"equipos",bleed:!0},{name:"Mezcladora de Mortero",tag:"Ideal para la aplicación de AC-I y AC-III.",img:"../img/prod/mezcladora-mortero.jpg",cat:"equipos",bleed:!0},{name:"BIO 360",tag:"Ácido bio 100% biodegradable para limpieza de concreto. Sin necesidad de EPP.",cat:"aditivos",bleed:!0,videoWebm:"../video/bio360.webm",videoMp4:"../video/bio360.mp4",poster:"../img/prod/bio360-poster.jpg"},{name:"Macro-fibras",tag:"Refuerzo estructural del concreto con macro-fibras sintéticas.",cat:"aditivos",bleed:!0,videoWebm:"../video/macrofibras.webm",videoMp4:"../video/macrofibras.mp4",poster:"../img/prod/macrofibras-poster.jpg"}],A='<svg viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="6" width="3.4" height="12" rx="1"/><rect x="13.6" y="6" width="3.4" height="12" rx="1"/></svg>',V='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg>';function N(){const e=document.getElementById("hero-carousel");if(!e||!p.length)return;const r=5200;e.className="v-showcase",e.style.setProperty("--vh-dur",r+"ms"),e.innerHTML=`
    <div class="vh-track">
      ${p.map((a,i)=>`
        <article class="vh-slide${i===0?" is-active":""}${a.bleed?" is-bleed":""}" data-i="${i}">
          <div class="vh-media">${a.videoMp4?`<video class="vh-el" muted loop playsinline preload="metadata" poster="${a.poster||""}"><source src="${a.videoWebm}" type="video/webm"><source src="${a.videoMp4}" type="video/mp4"></video>`:`<picture>${a.imgMobile?`<source media="(max-width: 760px)" srcset="${a.imgMobile}">`:""}<img class="vh-el" src="${a.img}" alt="${a.name}" ${i===0?"":'loading="lazy"'}></picture>`}</div>
          <div class="vh-inner">
            <div class="vh-copy">
              <span class="vh-eyebrow">Línea destacada</span>
              <h2 class="vh-title">${a.name}</h2>
              <p class="vh-desc">${a.tag}</p>
              <button class="vh-cta" data-cat="${a.cat}">Ver productos ${l("arrow","vh-cta-i")}</button>
            </div>
          </div>
        </article>`).join("")}
      <button class="vh-arrow vh-prev" aria-label="Anterior">${l("chevL")}</button>
      <button class="vh-arrow vh-next" aria-label="Siguiente">${l("chevR")}</button>
    </div>
    <div class="vh-controls">
      <div class="vh-segs">${p.map((a,i)=>`<button class="vh-seg" data-i="${i}" aria-label="Ver ${i+1}"><span class="vh-seg-fill"></span></button>`).join("")}</div>
      <button class="vh-pause" aria-label="Pausar o reanudar" aria-pressed="false">${A}</button>
    </div>`;const t=Array.from(e.querySelectorAll(".vh-slide")),o=Array.from(e.querySelectorAll(".vh-seg")),n=Array.from(e.querySelectorAll(".vh-seg-fill")),s=e.querySelector(".vh-pause"),g=window.matchMedia("(prefers-reduced-motion: reduce)").matches;let d=0,b=g;const x=()=>{t.forEach((i,$)=>{const C=$===d;i.classList.toggle("is-active",C);const v=i.querySelector("video");if(v)if(C){try{v.currentTime=0}catch{}v.play().catch(()=>{})}else v.pause()}),o.forEach((i,$)=>{i.classList.remove("is-active","is-done"),$<d&&i.classList.add("is-done")});const a=o[d];a.offsetWidth,a.classList.add("is-active")},f=a=>{d=(a+p.length)%p.length,x()},y=()=>f(d+1),M=()=>f(d-1);n.forEach(a=>a.addEventListener("animationend",()=>{!b&&o[d].classList.contains("is-active")&&y()}));const w=a=>{b=a,e.classList.toggle("is-paused",a),s.setAttribute("aria-pressed",String(a)),s.innerHTML=a?V:A};s.addEventListener("click",()=>w(!b)),e.querySelector(".vh-next").addEventListener("click",y),e.querySelector(".vh-prev").addEventListener("click",M),o.forEach(a=>a.addEventListener("click",()=>f(Number(a.dataset.i)))),e.querySelectorAll(".vh-cta").forEach(a=>a.addEventListener("click",()=>m(a.dataset.cat||"equipos",!0)));const k=e.querySelector(".vh-track");let u=null;k.addEventListener("touchstart",a=>{u=a.touches[0].clientX},{passive:!0}),k.addEventListener("touchend",a=>{if(u!==null){const i=a.changedTouches[0].clientX-u;Math.abs(i)>40&&(i<0?y():M())}u=null},{passive:!0}),x(),g&&w(!0)}function E(e){const r=`Hola, me interesa: ${e.name}${e.brand?" ("+e.brand+")":""}`;return`
    <article class="v-card">
      <div class="v-card-media">${e.img?`<img src="${e.img}" alt="${e.name}" loading="lazy">`:`<span class="ph">${e.name}</span>`}</div>
      <div class="v-card-body">
        ${e.brand?`<span class="v-brand">${e.brand}</span>`:""}
        <h3 class="v-name">${e.name}</h3>
        ${e.note?`<p class="v-note">${e.note}</p>`:""}
        <a class="v-cta" href="${S(r)}" target="_blank" rel="noopener" data-ev="product" data-detail="${e.name}">Consultar ${l("arrow","v-cta-i")}</a>
      </div>
    </article>`}function D(e){return`
    <article class="v-cat-panel" data-cat="${e.id}" tabindex="0" role="button" aria-label="Ver productos de ${e.title}">
      <div class="ghost">${l(e.icon)}</div>
      <div class="p-ic">${l(e.icon)}</div>
      <span class="t-vert">${e.title}</span>
      <div class="p-body">
        <h3>${e.title}</h3>
        <p>${e.blurb}</p>
        <span class="p-go">Ver productos ${l("arrow")}</span>
      </div>
    </article>`}function m(e,r=!1){const t=h.find(s=>s.id===e);if(!t)return;document.querySelectorAll(".v-cat-panel").forEach(s=>s.classList.toggle("is-active",s.dataset.cat===e)),document.querySelectorAll(".v-chip").forEach(s=>s.classList.toggle("is-active",s.dataset.cat===e));let o;t.groups&&t.groups.length?o=t.groups.map(s=>`
      <div class="v-subgroup">
        <h3 class="v-subtitle">${s.title}</h3>
        <div class="v-rail">${s.products.map(E).join("")}</div>
      </div>`).join(""):t.products&&t.products.length?o=`<div class="v-rail">${t.products.map(E).join("")}</div>`:o=`
      <div class="v-empty">
        <p>Pronto sumaremos productos de esta línea.</p>
        <a class="btn-empty" href="${S("Hola, quiero consultar sobre "+t.title)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      </div>`;const n=document.getElementById("v-products");n.innerHTML=`
    <div class="v-products-head"><div class="v-cat-ic">${l(t.icon)}</div><h2>${t.title}</h2></div>
    ${o}`,n.classList.remove("revealing"),n.offsetWidth,n.classList.add("revealing"),r&&n.scrollIntoView({behavior:"smooth",block:"start"})}function G(){const e=document.getElementById("catalog");e.innerHTML=`
    <div class="v-deck">${h.map(D).join("")}</div>
    <div class="v-products" id="v-products"></div>`,e.querySelectorAll(".v-cat-panel").forEach(t=>{const o=t.dataset.cat;t.addEventListener("click",()=>m(o,!0)),t.addEventListener("keydown",n=>{(n.key==="Enter"||n.key===" ")&&(n.preventDefault(),m(o,!0))})});const r=document.getElementById("cat-chips");r&&(r.innerHTML=h.map(t=>`<button class="v-chip" data-cat="${t.id}">${t.title}</button>`).join(""),r.querySelectorAll(".v-chip").forEach(t=>t.addEventListener("click",()=>m(t.dataset.cat,!0)))),m(h[0].id)}const L=[];function _(){const e=document.getElementById("promos");if(!L.length){e.style.display="none";return}e.innerHTML=`
    <div class="v-promo-band">
      ${L.map(r=>`
        <div class="v-promo">
          <h3>${r.title}</h3><p>${r.text}</p>
          ${r.url?`<a href="${r.url}" target="_blank" rel="noopener">Ver más →</a>`:""}
        </div>`).join("")}
    </div>`}function W(){const e=document.getElementById("quote-form"),r=document.getElementById("quote-status");e.addEventListener("submit",t=>{t.preventDefault();const o=new FormData(e),n=String(o.get("nombre")??"").trim(),s=String(o.get("whatsapp")??"").trim();if(!n||!s){r.textContent="Completá nombre y WhatsApp.",r.className="text-sm text-red-600";return}const g=`Cotización GNH%0ANombre: ${n}%0AEmpresa: ${o.get("empresa")??""}%0AProducto: ${o.get("producto")??""}%0AMensaje: ${o.get("mensaje")??""}`;window.open(`https://wa.me/${q}?text=${g}`,"_blank"),r.textContent="¡Gracias! Te redirigimos a WhatsApp.",r.className="text-sm text-green-600",e.reset()})}N();G();_();W();z();
