import '@fontsource/space-grotesk/700.css'
import '@fontsource/inter/400.css'
import './style.css'
import './gateway.css'

import gsap from 'gsap'

/** Strings centralizadas — trocar para PT depois é substituir este objeto. */
const STRINGS = {
  es: {
    wordmark: 'Generando Nuevos Horizontes',
    ventas: 'Ventas',
    institucional: 'Institucional',
  },
}
const t = STRINGS.es

document.querySelectorAll<HTMLElement>('[data-str]').forEach((el) => {
  const key = el.dataset.str as keyof typeof t
  el.textContent = t[key] ?? ''
})

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
const gateway = document.getElementById('gateway')!
const sun = document.querySelector<HTMLElement>('.gw-sun')!
const horizon = document.querySelector<HTMLElement>('.gw-horizon')!

/* ---------- entrada ---------- */
let sunFloat: gsap.core.Tween | null = null

if (!reduced) {
  // ---------- cortina: preto → sol acende → painéis se abrem ----------
  const curtain = gsap.timeline({ defaults: { ease: 'power4.inOut' } })
  curtain
    .to('.gw-curtain-dot', { scale: 1, duration: 0.45, ease: 'back.out(2)' }, 0.25)
    .to('.gw-curtain-dot', { opacity: 0, duration: 0.35, ease: 'power2.out' }, 0.95)
    .to('.gw-cp-left',  { xPercent: -101, duration: 1.05 }, 0.9)
    .to('.gw-cp-right', { xPercent: 101,  duration: 1.05 }, 0.9)
    .set('.gw-curtain', { display: 'none' })

  // ---------- entrada do pórtico (começa quando a cortina abre) ----------
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' }, delay: 1.15 })

  // 1. horizonte desenha do centro pra fora — primeiro movimento
  tl.to('.gw-line', { scaleX: 1, duration: 1.0 }, 0)
    // 2. logo entra por cima
    .to('.gw-logo', { opacity: 1, y: 0, duration: 0.7 }, 0.45)
    // 3. sol nasce…
    .to(sun, { scale: 1, duration: 0.5, ease: 'back.out(2)' }, 0.75)
    // 4. wordmark revela com contração do tracking
    .to('.gw-wordmark', { opacity: 1, letterSpacing: '0.42em', duration: 0.8 }, 0.95)
    // 5. portas sobem em stagger
    .to('.gw-door', { opacity: 1, y: 0, duration: 0.55, stagger: 0.1 }, 1.15)
    // …e depois flutua em loop
    .call(() => {
      sunFloat = gsap.to(sun, {
        y: -3,
        duration: 1.8,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
      })
    })
}

/* ---------- interação: sol desliza pro lado da porta ---------- */
function slideSun(side: 'ventas' | 'institucional' | 'center'): void {
  if (reduced) return
  const w = horizon.clientWidth
  const x = side === 'center' ? 0 : (side === 'ventas' ? -0.32 : 0.32) * w // 50% → 18% / 82%
  gsap.to(sun, { x, duration: 0.55, ease: 'power3.out', overwrite: 'auto' })
}

document.querySelectorAll<HTMLAnchorElement>('.gw-door').forEach((door) => {
  const side = door.dataset.side as 'ventas' | 'institucional'
  door.addEventListener('mouseenter', () => slideSun(side))
  door.addEventListener('focus', () => slideSun(side))
  door.addEventListener('mouseleave', () => slideSun('center'))
  door.addEventListener('blur', () => slideSun('center'))

  /* ---------- saída + roteamento ---------- */
  door.addEventListener('click', (e) => {
    e.preventDefault()
    const go = () => location.assign(door.href)
    if (reduced) { go(); return }
    sunFloat?.kill()
    gateway.classList.add('gw-exit')
    setTimeout(go, 560)
  })
})
