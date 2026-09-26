# Site inicial

`index.html` é um site de arquivo único (CSS dentro, sem build), responsivo, com SEO básico,
dados estruturados e WhatsApp. Troque todos os `{{...}}` — procure por `{{` antes de publicar:

```bash
grep -n "{{" index.html
```

Fotos de produto em `img/`, 800×600, fundo branco ou transparente (`../../../ferramentas/recortar-fundo.py`).
Cores: ajuste os tokens em `:root` com os valores de `../marca.md`.
