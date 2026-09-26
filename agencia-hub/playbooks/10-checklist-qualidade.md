# 10 — Checklist de qualidade (antes de dizer "pronto")

- [ ] Abriu no navegador: 1280 px e 390 px.
- [ ] Sem rolagem horizontal no celular (`document.documentElement.scrollWidth == innerWidth`).
- [ ] Sem erro de JavaScript no console.
- [ ] Todas as imagens carregam (role a página: `loading="lazy"` engana o print).
- [ ] Links de WhatsApp, telefone e e-mail funcionam; mensagem pré-preenchida certa.
- [ ] Nenhum `{{placeholder}}` sobrando.
- [ ] Nenhum número sem fonte.
- [ ] Título, descrição, OG, canonical e JSON-LD em cada página nova.
- [ ] Sitemap atualizado.
- [ ] Depois do deploy: conferir a URL pública (ou o check de CI) antes de avisar o cliente.
