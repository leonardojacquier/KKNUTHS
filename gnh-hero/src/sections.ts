import gsap from 'gsap'

/** Counters + reveal dos cards (spec seção 6). */
export function initSections(reduced: boolean): void {
  // ---- Counters: contam 0 → valor ao entrar na viewport ----
  document.querySelectorAll<HTMLElement>('.counter').forEach((el) => {
    const target = Number(el.dataset.count ?? 0)
    if (reduced) { el.textContent = String(target); return }
    gsap.to(el, {
      textContent: target,
      duration: 1.6,
      ease: 'power2.out',
      snap: { textContent: 1 },
      scrollTrigger: { trigger: el, start: 'top 85%', once: true },
    })
  })

  // ---- Cards: reveal em stagger ----
  if (reduced) return // CSS estático cobre
  gsap.to('.company-card', {
    y: 0,
    opacity: 1,
    duration: 0.7,
    ease: 'power3.out',
    stagger: 0.08,
    scrollTrigger: { trigger: '#grupo', start: 'top 80%', once: true },
  })
}
