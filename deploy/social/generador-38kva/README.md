# Lanzamiento Generador 38 kVA — material para postar

Vídeos com os selos queimados na imagem (não dependem de link nem de preview).
Fonte: `../../gnh-hero/public/video/generador.mp4` + overlay `_overlay-fonte.html`.

| Arquivo | Formato | Onde usar |
|---|---|---|
| `gnh-generador-vertical.mp4` | 1080×1920 (9:16) | Stories, Reels, TikTok, **status do WhatsApp** |
| `gnh-generador-cuadrado.mp4` | 1080×1080 (1:1) | Feed do Instagram e do Facebook |
| `gnh-generador-ancho.mp4` | 1920×1080 (16:9) | Facebook, LinkedIn, YouTube, enviar por WhatsApp no PC |

5 segundos, sem áudio (o original vinha com trilha, tirada — em feed roda mudo mesmo).

## Legenda pronta (copiar e colar)

> ⚡ **LANZAMIENTO — Generador 38 kVA con Motor Ricardo**
>
> Ya en stock, ¡pronta entrega! Grupo electrógeno diésel trifásico con cabina
> súper silenciosa y tablero ATS: cuando se corta la luz, arranca solo.
>
> 🔧 400 V / 50 Hz · Motor Ricardo · Súper silencioso · Arranque automático
> 📍 Vení a conocerlo en nuestro Show Room
> 💬 Consultas por WhatsApp: +595 995 360060
>
> 👉 gnhorizons.com/promo/generador-38kva/
>
> #GNH #Generador #GrupoElectrogeno #Paraguay #CiudadDelEste #EnergiaDeRespaldo

## O link para pôr no post

Trocar só o `utm_source` conforme a rede — é o que faz o painel dizer de onde veio
cada visita (ver `deploy/LINKS-UTM.md`):

```
Instagram  https://gnhorizons.com/promo/generador-38kva/?utm_source=instagram&utm_medium=social&utm_campaign=generador-38kva
Facebook   https://gnhorizons.com/promo/generador-38kva/?utm_source=facebook&utm_medium=social&utm_campaign=generador-38kva
WhatsApp   https://gnhorizons.com/promo/generador-38kva/?utm_source=whatsapp&utm_medium=chat&utm_campaign=generador-38kva
LinkedIn   https://gnhorizons.com/promo/generador-38kva/?utm_source=linkedin&utm_medium=social&utm_campaign=generador-38kva
```

> No Instagram o link não é clicável na legenda do feed — vai na bio ou no sticker
> de link do Stories. No Facebook e no WhatsApp cola direto.

## Refazer para outra campanha

1. Editar os textos e o `CFG` de cada formato em `_overlay-fonte.html`
2. Servir a pasta (`python3 -m http.server`) e capturar com o navegador em
   `?f=vertical|cuadrado|ancho`, **fundo transparente** (`omitBackground`)
3. Compor com ffmpeg: fundo desfocado do próprio vídeo + vídeo nítido centrado +
   overlay por cima (os comandos ficaram no histórico do commit desta pasta)

Esta pasta **não vai para o servidor** — `deploy/` fica fora do que o autodeploy copia.
