# 09 — Vídeo de produto com IA

Ferramentas de imagem-para-vídeo: Kling (modo Pro), Runway Gen-4, Veo 3, Hailuo.

## O que funciona
1. **Imagem de partida simples:** o produto recortado sobre fundo **liso** (sem card, sem texto).
   Com fundo complexo o modelo reinventa a cena (trocou grua de esteira por grua de pneus e
   escreveu texto em coreano).
2. Confirmar que a imagem entra como **primeiro quadro** (start frame), não como "referência".
3. Prompt com "static camera", o movimento de **uma** parte só, e prompt negativo
   (background change, text, logo, camera movement, different machine).
4. 720p, 8 s, uma tentativa antes de gastar créditos em variações. Evitar modelos "Flash".
5. Texto, logo, card e botão **não** passam pela IA: entram depois na montagem (Playwright +
   ffmpeg), para nunca deformar.

## Montagem
Recorte do clipe quadro a quadro, composição sobre o fundo da marca, título/CTA, exportar
MP4 (H.264) e WebM (VP9) em 9:16 e 16:9.
