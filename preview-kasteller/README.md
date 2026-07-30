# Prévia — site Kasteller Revestimientos

`kasteller-preview.html` é uma **prévia de direção visual**, autocontida (imagens em
base64). Não é o site: serve para aprovar linguagem antes de montar o projeto real.

## Como regerar

```bash
python3 build-preview.py          # lê assets/ e escreve kasteller-preview.html
```

`assets/` traz o logo extraído do PDF de identidade (versões branca e preta, fundo
transparente) e a foto de ambiente que já existia no material da GNH.

## Decisões aplicadas

- Paleta oficial: `#000000` · `#FFFFFF` · areia `#E8E1D7` · taupe `#544F4B`
- Tema escuro = fundo preto; tema claro = fundo areia (ambos da marca)
- A geometria do **K (chevron)** vira linguagem: cortina de abertura e divisão do gateway
- Estrutura igual à da GNH: **Ventas** + **Institucional**
- Conteúdo legível sem JavaScript (só a animação depende dele)
- `prefers-reduced-motion` desliga a abertura

## Pendente

Fotos e vídeos reais, tipografia oficial embutida, textos definitivos e o domínio.
