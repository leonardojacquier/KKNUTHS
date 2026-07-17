import '@fontsource/space-grotesk/700.css'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import './style.css'

import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import { initHero } from './hero'
import { initSections } from './sections'
import { mountFooter } from './footer'

gsap.registerPlugin(ScrollTrigger)

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches

// ---- Lenis + GSAP glue (spec seção 4) ----
if (!reduced) {
  const lenis = new Lenis({ duration: 1.1, smoothWheel: true })
  lenis.on('scroll', ScrollTrigger.update)
  gsap.ticker.add((t) => lenis.raf(t * 1000))
  gsap.ticker.lagSmoothing(0)
}

mountFooter()
initHero(reduced)
initSections(reduced)

const year = document.getElementById('year')
if (year) year.textContent = String(new Date().getFullYear())
