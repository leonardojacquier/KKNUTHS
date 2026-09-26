# 06 — Fotos de produto

**Padrão:** PNG 800×600 com transparência (ou JPG com fundo branco), produto centrado com
~3,5 % de margem, sobre card branco com moldura cinza `#C5CBD5`.

## Receita
1. Foto de estúdio em fundo branco: limiar de branco (núcleo ≥ 253) + crescimento até ~240.
2. Foto em cena (pátio, galpão, céu): `ferramentas/recortar-fundo.py`, que usa o modelo
   **BiRefNet** (rembg). Foi o único que limpou o fundo entre as pernas da máquina sem cortar peças.
3. Imagem com duas máquinas ou selo "HOT/NEW": ficar com o maior bloco e apagar a faixa do selo.
4. Máquina branca sobre fundo branco: baixar o limiar só na parte de baixo (sombra).

## Regras
- **Não trocar foto já publicada** sem o cliente mandar a nova.
- Desenho técnico do manual não serve como foto de card (o dono recusou).
- Rodar o BiRefNet **uma imagem por processo**: na segunda inferência o Python pode morrer.

Instalar: `pip install rembg onnxruntime pillow numpy scipy`.
