# 07 — Fichas técnicas HTML e PDF

A ficha é o documento que o vendedor manda no WhatsApp. Cada produto tem:
- `fichas/<produto>.html` — página imprimível, com logo embutido (base64), botões de PDF e WhatsApp.
- `fichas/pdf/<produto>.pdf` — A4, gerado com Chromium (Playwright), rodapé com página e contato.

## Conteúdo
Cabeçalho (logo sem slogan, "Ficha técnica", família), título, frase-resumo, 3–4 números-chave,
foto, descrição, tabela de especificações por seção, rodapé com contato e aviso
"datos del fabricante, sujetos a confirmación".

## Técnica
- PDF: `page.pdf(format='A4', print_background=True, display_header_footer=True,
  margin={'top':'0mm','bottom':'16mm'})` e `@page{margin:0 0 16mm 0}` para o rodapé não
  cobrir a última linha da tabela.
- Logo e foto embutidos no HTML (base64): trocar o arquivo de imagem **não** atualiza a
  ficha — é preciso regenerar.
