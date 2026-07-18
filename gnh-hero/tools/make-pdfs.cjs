// Genera los PDFs de las fichas: renderiza cada public/fichas/<slug>.html con
// Chromium (Playwright) y guarda public/fichas/pdf/<slug>.pdf  (A4, con marca).
// Uso: node tools/make-pdfs.js
const { chromium } = require('/home/user/KKNUTHS/node_modules/playwright-core')
const fs = require('fs')
const path = require('path')

const FICHAS = path.resolve(__dirname, '../public/fichas')
const PDF_DIR = path.join(FICHAS, 'pdf')
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

;(async () => {
  fs.mkdirSync(PDF_DIR, { recursive: true })
  const files = fs.readdirSync(FICHAS).filter((f) => f.endsWith('.html'))
  const browser = await chromium.launch({ executablePath: CHROME })
  const page = await browser.newPage()
  // sin red externa: bloquea fuentes/hotlinks para no colgar (el PDF usa fallback tipográfico)
  await page.route('**/*', (r) =>
    /fontshare|gnhorizons|gstatic/.test(r.request().url()) ? r.abort() : r.continue())
  let done = 0
  for (const f of files) {
    const slug = f.replace(/\.html$/, '')
    await page.goto('file://' + path.join(FICHAS, f), { waitUntil: 'load', timeout: 15000 })
    await page.pdf({
      path: path.join(PDF_DIR, slug + '.pdf'),
      format: 'A4',
      printBackground: true,
      margin: { top: '10mm', bottom: '16mm', left: '11mm', right: '11mm' },
      displayHeaderFooter: true,
      headerTemplate: '<span></span>',
      footerTemplate: `<div style="width:100%;font-size:8px;color:#8a93a3;padding:0 11mm;display:flex;justify-content:space-between;font-family:Arial,sans-serif">
        <span>GNH — Generando Nuevos Horizontes · gnhorizons.com · WhatsApp +595 995 360060</span>
        <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>`,
    })
    done++
    if (done % 20 === 0) console.log(`${done}/${files.length}`)
  }
  await browser.close()
  console.log(`PDFs generados: ${done}`)
  process.exit(0)
})()
