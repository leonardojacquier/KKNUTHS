import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

/** Timeline de entrada + scrub do hero (spec seção 3). */
export function initHero(reduced: boolean): void {
  if (reduced) return // CSS já entrega o estado final estático

  // ---- Entrada (ao carregar) ----
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  tl.to('.eyebrow', { y: 0, opacity: 1, duration: 0.6, startAt: { y: 20 } }, 0)
    .to('.hero-title', {
      clipPath: 'inset(0% 0 0 0)',
      filter: 'blur(0px)',
      y: 0,
      duration: 1.0,
      startAt: { y: 40 },
    }, 0.2)
    .to('.hero-sub', { y: 0, opacity: 1, duration: 0.6, startAt: { y: 16 } }, 0.8)
    .to('.hero-cta', { y: 0, opacity: 1, duration: 0.5, startAt: { y: 12 } }, 1.0)
    .to('.scroll-cue', { opacity: 1, duration: 0.5 }, 1.2)

  // ---- Scrub do fundo (efeito-assinatura) ----
  gsap.to('.hero-bg', {
    scale: 1.12,
    yPercent: 12,
    ease: 'none',
    scrollTrigger: {
      trigger: '#hero',
      start: 'top top',
      end: 'bottom top',
      scrub: true,
    },
  })

  // conteúdo sobe e some antes da vinheta
  gsap.to('.hero-content', {
    yPercent: -8,
    opacity: 0,
    ease: 'none',
    scrollTrigger: {
      trigger: '#hero',
      start: 'top top',
      end: 'bottom top',
      scrub: true,
    },
  })

  ScrollTrigger.refresh()
}
