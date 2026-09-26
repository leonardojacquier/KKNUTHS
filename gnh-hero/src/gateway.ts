import { track } from './track'
import gsap from 'gsap'

/** Strings centralizadas — trocar ES→PT (Vendas/Institucional) é editar este objeto. */
const STRINGS = {
  es: {
    wordmark: 'Generando Nuevos Horizontes',
    ventas: 'Ventas',
    institucional: 'Institucional',
    footer: 'Paraguay · Brasil',
  },
}
const t = STRINGS.es

export function fillStrings(): void {
  document.querySelectorAll<HTMLElement>('[data-str]').forEach((el) => {
    const key = el.dataset.str as keyof typeof t
    el.textContent = t[key] ?? ''
  })
}

let sunFloat: gsap.core.Tween | null = null

/** Entrada do pórtico: logo suave (sem pancada) → horizonte → sol → wordmark → portas → rodapé. */
export function enterGateway(reduced: boolean): void {
  if (reduced) return // CSS já entrega o estado final estático
  const sun = document.querySelector<HTMLElement>('.gw-sun')!

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  tl.to('.gw-logo', {
      opacity: 1,
      scale: 1,
      filter: 'blur(0px)',
      duration: 1.2,
      ease: 'power2.out', // suave, sem overshoot
    }, 0)
    .to('.gw-line', { scaleX: 1, duration: 1.0 }, 0.35)
    .to(sun, { scale: 1, duration: 0.5 }, 0.85)
    .to('.gw-wordmark', { opacity: 1, letterSpacing: '0.42em', duration: 0.8 }, 1.0)
    .to('.gw-door', { opacity: 1, y: 0, duration: 0.55, stagger: 0.1 }, 1.2)
    .to('.gw-footer', { opacity: 1, duration: 0.6 }, 1.4)
    .call(() => {
      sunFloat = gsap.to(sun, { y: -3, duration: 1.8, ease: 'sine.inOut', yoyo: true, repeat: -1 })
    })
}

/** Interação das portas: sol desliza pro lado, e clique roteia com saída. */
export function initDoors(reduced: boolean): void {
  const sun = document.querySelector<HTMLElement>('.gw-sun')!
  const horizon = document.querySelector<HTMLElement>('.gw-horizon')!
  const gateway = document.getElementById('gateway')!

  const slideSun = (side: 'ventas' | 'institucional' | 'center') => {
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

    door.addEventListener('click', (e) => {
      e.preventDefault()
      track('porta', side)
      const go = () => location.assign(door.href)
      if (reduced) { go(); return }
      sunFloat?.kill()
      gateway.classList.add('gw-exit')
      setTimeout(go, 560)
    })
  })
}
