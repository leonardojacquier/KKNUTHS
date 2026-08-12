// Renderiza o informe HTML em PDF A4 vetorial.
// Sem rede: fontes e imagens já estão embutidas, e qualquer pedido externo
// travaria o render sem melhorar nada.
const { chromium } = require('/home/user/KKNUTHS/node_modules/playwright')
const path = require('path')

const HTML = path.join(__dirname, process.argv[2] || 'informe-cielo-azul.html')
const PDF = HTML.replace(/\.html$/, '.pdf')

;(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
  const page = await browser.newPage()
  await page.route('**/*', (r) => (/^https?:/.test(r.request().url()) ? r.abort() : r.continue()))
  await page.goto('file://' + HTML, { waitUntil: 'load' })
  await page.emulateMedia({ media: 'print' })
  await page.pdf({ path: PDF, format: 'A4', printBackground: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 } })
  await browser.close()
  console.log('PDF:', PDF)
})()
