/** Curtain — preloader branco que fecha pro centro e revela o gateway das bordas. */

const MIN_MS = 1200 // piso: evita "piscar"
const MAX_MS = 3000 // teto de segurança
const OPEN_MS = 1000 // deve casar com a transition do CSS (.gw-curtain-panel)

function preloadImage(src: string): Promise<void> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve()
    img.onerror = () => resolve() // nunca trava a abertura por causa de asset
    img.src = src
  })
}

function windowLoaded(): Promise<void> {
  if (document.readyState === 'complete') return Promise.resolve()
  return new Promise((r) => window.addEventListener('load', () => r(), { once: true }))
}

/** Site pronto = fontes + load + logo, com piso MIN e teto MAX. */
function siteReady(): Promise<void> {
  const fontsReady =
    (document as unknown as { fonts?: { ready: Promise<unknown> } }).fonts?.ready ??
    Promise.resolve()

  const ready = Promise.all([
    fontsReady,
    windowLoaded(),
    preloadImage('/img/gnh-logo.svg'),
  ]).then(() => undefined)

  const floor = new Promise<void>((r) => setTimeout(r, MIN_MS))
  const ceiling = new Promise<void>((r) => setTimeout(r, MAX_MS))

  // espera (pronto E piso), mas nunca além do teto
  return Promise.race([
    Promise.all([ready, floor]).then(() => undefined),
    ceiling,
  ])
}

/** Abre a cortina; resolve quando os painéis terminam de recolher. */
export async function runCurtain(el: HTMLElement): Promise<void> {
  await siteReady()
  el.classList.add('is-open')
  await new Promise<void>((r) => setTimeout(r, OPEN_MS))
  el.style.display = 'none'
}
