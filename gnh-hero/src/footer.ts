/** Rodapé comum às duas linhas: tiendas (CDE + Asunción) + redes + contacto. */

const SOCIAL = {
  // AJUSTAR: URLs reales de GNH
  instagram: 'https://www.instagram.com/gnhorizons',
  facebook: 'https://www.facebook.com/share/1BZWSKyvbK/',
  tiktok: 'https://www.tiktok.com/@gnhorizons',
  whatsapp: 'https://wa.me/595985311031?text=Hola,%20quiero%20más%20información',
}

const TIENDAS = [
  {
    ciudad: 'Ciudad del Este',
    dir: 'Av. República del Perú km 7, CDE 100101',
    tel: '0995 360060',
    share: 'https://share.google/OAtbh8akZyeNATtUM',
    q: 'Av. República del Perú km 7, Ciudad del Este, Paraguay',
  },
  {
    ciudad: 'Asunción · Ñemby',
    dir: 'Acceso Sur, Ñemby 111210',
    tel: '',
    share: 'https://share.google/DB7b1OL7m1ISorPhY',
    q: 'Acceso Sur, Ñemby, Paraguay',
  },
]

export function mountFooter(slotId = 'footer-slot'): void {
  const slot = document.getElementById(slotId)
  if (!slot) return
  slot.innerHTML = `
    <footer class="bg-ink text-white/70">
      <!-- tiendas con mapa -->
      <div class="mx-auto max-w-6xl px-6 pt-14">
        <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Nuestras tiendas</h4>
        <div class="mt-5 grid gap-6 md:grid-cols-2">
          ${TIENDAS.map((t) => `
            <div class="foot-store">
              <iframe class="foot-map" src="https://www.google.com/maps?q=${encodeURIComponent(t.q)}&output=embed"
                      loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Mapa ${t.ciudad}"></iframe>
              <div class="foot-store-info">
                <p class="font-semibold text-white">${t.ciudad}</p>
                <p class="text-sm">${t.dir}</p>
                ${t.tel ? `<p class="text-sm">Tel: <a href="tel:+595${t.tel.replace(/\D/g, '').replace(/^0/, '')}" class="hover:text-orange">${t.tel}</a></p>` : ''}
                <a href="${t.share}" target="_blank" rel="noopener" class="text-orange hover:underline text-sm">Ver en Google Maps →</a>
              </div>
            </div>`).join('')}
        </div>
      </div>

      <!-- marca + redes + contacto -->
      <div class="mx-auto max-w-6xl px-6 py-12 grid gap-10 md:grid-cols-2 border-t border-white/10 mt-12">
        <div>
          <img src="/img/gnh-logo.svg" alt="GNH" class="h-10 w-auto"
               onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'font-display text-2xl font-bold text-white',textContent:'GNH'}))">
          <p class="mt-4 text-sm max-w-xs">Generando Nuevos Horizontes — comercio internacional, distribución y logística.</p>
          <div class="mt-5 flex gap-3">
            <a href="${SOCIAL.instagram}" target="_blank" rel="noopener" aria-label="Instagram" class="foot-social">${IG}</a>
            <a href="${SOCIAL.facebook}" target="_blank" rel="noopener" aria-label="Facebook" class="foot-social">${FB}</a>
            <a href="${SOCIAL.tiktok}" target="_blank" rel="noopener" aria-label="TikTok" class="foot-social">${TT}</a>
          </div>
        </div>
        <div class="md:justify-self-end">
          <h4 class="font-display text-sm font-bold uppercase tracking-[0.2em] text-white">Contacto</h4>
          <ul class="mt-4 space-y-2 text-sm">
            <li><a href="tel:+595985311031" class="hover:text-orange">+595 985 311031</a></li>
            <li><a href="mailto:adm@gnhorizons.com" class="hover:text-orange">adm@gnhorizons.com</a></li>
            <li><a href="${SOCIAL.whatsapp}" target="_blank" rel="noopener" class="hover:text-orange">WhatsApp</a></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-white/10 py-6 text-center text-xs text-white/40">
        © ${'{'}year${'}'} Grupo GNH — Reservados todos los derechos · Paraguay · Brasil
      </div>
    </footer>`
  slot.innerHTML = slot.innerHTML.replace('{year}', String(new Date().getFullYear()))

  // WhatsApp flotante
  const wa = document.createElement('a')
  wa.href = SOCIAL.whatsapp
  wa.target = '_blank'
  wa.rel = 'noopener'
  wa.setAttribute('aria-label', 'WhatsApp')
  wa.className = 'wa-float'
  wa.innerHTML = WA
  document.body.appendChild(wa)
}

const IG = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s0 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.58 2.2 15.2 2.2 12s0-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.2 8.8 2.2 12 2.2m0 1.8c-3.15 0-3.5 0-4.7.07-.9.04-1.4.2-1.72.32-.43.17-.74.37-1.06.7-.32.32-.52.63-.7 1.06-.12.32-.28.82-.32 1.72C3.2 8.5 3.2 8.85 3.2 12s0 3.5.07 4.7c.04.9.2 1.4.32 1.72.17.43.37.74.7 1.06.32.32.63.52 1.06.7.32.12.82.28 1.72.32 1.2.06 1.55.07 4.7.07s3.5 0 4.7-.07c.9-.04 1.4-.2 1.72-.32.43-.17.74-.37 1.06-.7.32-.32.52-.63.7-1.06.12-.32.28-.82.32-1.72.06-1.2.07-1.55.07-4.7s0-3.5-.07-4.7c-.04-.9-.2-1.4-.32-1.72a2.9 2.9 0 0 0-.7-1.06 2.9 2.9 0 0 0-1.06-.7c-.32-.12-.82-.28-1.72-.32C15.5 4 15.15 4 12 4m0 3.06A4.94 4.94 0 1 1 12 16.94 4.94 4.94 0 0 1 12 7.06m0 1.8a3.14 3.14 0 1 0 0 6.28 3.14 3.14 0 0 0 0-6.28m5.14-.9a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3"/></svg>`
const FB = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 8h3V4h-3a4.5 4.5 0 0 0-4.5 4.5V11H7v4h2.5v7h4v-7H17l.7-4h-4.2V8.8A.8.8 0 0 1 14 8z"/></svg>`
const TT = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 3c.3 2 1.6 3.6 3.5 3.9v2.4c-1.3.1-2.6-.3-3.7-1v5.9a5.6 5.6 0 1 1-5.6-5.6c.3 0 .5 0 .8.05v2.5a3.1 3.1 0 1 0 2.2 3V3z"/></svg>`
const WA = `<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5 13.7c-.2.6-1.2 1.2-1.7 1.2-.4.1-1 .1-1.6-.1a13 13 0 0 1-5.9-5.2c-.7-1.1-1.1-2.4-.6-3.1.2-.4.6-.6 1-.6h.7c.2 0 .5-.1.7.5l1 2.3c.1.2 0 .4-.1.6l-.5.7c-.2.2-.3.4-.1.7a9.6 9.6 0 0 0 3.6 3.2c.3.1.5.1.7-.1l.8-1c.2-.3.4-.2.7-.1l2.2 1c.2.1.4.2.4.4 0 .1 0 .8-.3 1.6z"/></svg>`
