#!/usr/bin/env node
/* Gera sitemap.xml a partir do que realmente existe em assets/nuevo/.
   Fonte única: o filesystem do build — nada de lista manual que envelhece.
   Rodar SEMPRE depois de sincronizar assets/nuevo (é o último passo do build). */
const fs = require('fs')
const path = require('path')

const REPO = path.resolve(__dirname, '..', '..')
const OUT_DIRS = [path.join(REPO, 'assets', 'nuevo'), path.join(REPO, 'gnh-hero', 'dist')]
const BASE = 'https://gnhorizons.com'

/** páginas principais com prioridade explícita */
const MAIN = [
  { loc: '/', freq: 'weekly', pri: '1.0' },
  { loc: '/ventas/', freq: 'weekly', pri: '0.9' },
  { loc: '/institucional/', freq: 'monthly', pri: '0.8' },
]

function collect(root) {
  const urls = MAIN.map((m) => ({ ...m }))

  // fichas técnicas (HTML estático, uma por produto químico)
  const fichasDir = path.join(root, 'fichas')
  if (fs.existsSync(fichasDir)) {
    for (const f of fs.readdirSync(fichasDir).filter((f) => f.endsWith('.html')).sort()) {
      urls.push({ loc: `/fichas/${f}`, freq: 'monthly', pri: '0.7' })
    }
  }

  // páginas de produto estáticas (geradas por build-productos.cjs)
  const prodDir = path.join(root, 'ventas')
  if (fs.existsSync(prodDir)) {
    for (const d of fs.readdirSync(prodDir, { withFileTypes: true })) {
      if (d.isDirectory() && fs.existsSync(path.join(prodDir, d.name, 'index.html'))) {
        urls.push({ loc: `/ventas/${d.name}/`, freq: 'monthly', pri: '0.8' })
      }
    }
  }
  // landings de promoción (una carpeta por campaña, escritas a mano)
  const promoDir = path.join(root, 'promo')
  if (fs.existsSync(promoDir)) {
    for (const d of fs.readdirSync(promoDir, { withFileTypes: true })) {
      if (d.isDirectory() && fs.existsSync(path.join(promoDir, d.name, 'index.html'))) {
        urls.push({ loc: `/promo/${d.name}/`, freq: 'weekly', pri: '0.9' })
      }
    }
  }
  return urls
}

function xml(urls) {
  const body = urls.map((u) =>
    `  <url><loc>${BASE}${u.loc}</loc><changefreq>${u.freq}</changefreq><priority>${u.pri}</priority></url>`
  ).join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`
}

const primary = OUT_DIRS.find((d) => fs.existsSync(d))
if (!primary) { console.error('nada em assets/nuevo nem dist — rode o build antes'); process.exit(1) }
const urls = collect(primary)
const out = xml(urls)
for (const d of OUT_DIRS) {
  if (fs.existsSync(d)) fs.writeFileSync(path.join(d, 'sitemap.xml'), out)
}
// mantém a cópia versionada em public/ igual (é a que entra no próximo build)
fs.writeFileSync(path.join(REPO, 'gnh-hero', 'public', 'sitemap.xml'), out)

const fichas = urls.filter((u) => u.loc.startsWith('/fichas/')).length
const prods = urls.filter((u) => /^\/ventas\/.+\//.test(u.loc)).length
console.log(`sitemap OK — ${urls.length} URLs (${MAIN.length} principais, ${fichas} fichas, ${prods} produtos)`)
