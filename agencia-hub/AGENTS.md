# AGENTS.md — Hub da Agência (mesmo conteúdo do CLAUDE.md)

Instruções para o Claude (e qualquer agente) que trabalhe nesta pasta.

## O que é

Central da agência: sites, catálogos, fichas técnicas, campanhas e conteúdo para clientes.
O dono conversa em **português**. Os sites dos clientes do Paraguai são em **espanhol** (es),
com voseo paraguaio no texto comercial ("consultá", "pedí"), salvo indicação do briefing.

## Regras de trabalho (valem para todo cliente)

1. **Nunca inventar dado técnico.** Números de produto (capacidade, potência, medidas, preço)
   só saem de material do fabricante ou do cliente. Se falta, deixe fora e avise. Material de
   marketing (briefing de campanha) não é fonte técnica; manual/ficha do fabricante é.
2. **Não mexer no que já está publicado sem pedido.** Fotos, textos e layout que o cliente
   aprovou ficam como estão; mudança só quando pedida.
3. **Sem comparativos com concorrentes** nas páginas, salvo pedido explícito.
4. **Posicionamento é do cliente.** Leia `clientes/<cliente>/marca.md` antes de escrever copy.
   Ex.: GNH não é "una importadora", é *grupo empresarial de comercio internacional*.
5. **Catálogo grande = gerador, não página a mão.** Dados em arquivo (`dados.py`), texto em
   `contenido.py`, e um `gen_site.py` que escreve páginas, fichas HTML+PDF e sitemap.
   Modelo real: `../gen-minicargadoras/` e `../gen-britagem/`. Ver `playbooks/05`.
6. **Fotos de produto**: fundo branco ou transparente, 800×600, produto centrado. Receita em
   `playbooks/06` e script em `ferramentas/recortar-fundo.py`.
7. **Verificar antes de dizer que está pronto**: abrir no navegador (Playwright/Chromium),
   desktop 1280 px e celular 390 px, sem rolagem horizontal, sem erro de JavaScript.
8. **Registrar decisões** em `clientes/<cliente>/decisoes.md`: o que o cliente pediu, recusou
   e por quê. Evita repetir erro (ex.: cliente rejeitou borda dourada → cinza).
9. **Repositório público.** Nada de senha, token, contrato, preço negociado ou dado pessoal.

## Estrutura

- `clientes/_modelo/` — molde de cliente (copie com `ferramentas/novo-cliente.sh`).
- `clientes/<cliente>/` — briefing, marca, conteúdo, entregas, decisões.
- `playbooks/` — procedimentos numerados. Leia o do tipo de trabalho antes de começar.
- `propostas/` — proposta comercial e catálogo de serviços (sem preços fixos).
- `ferramentas/` — scripts Python/Bash reutilizáveis.

## Clientes com código neste repositório

- **GNH** — `gnhorizons.com`. Regras próprias no `CLAUDE.md` da raiz do repositório
  (leia antes de tocar em qualquer arquivo da GNH).
- **Kasteller** — `kasteller.com.py`, arquivos em `../assets/kasteller2/`, documentação em
  `../docs/vault-gnh/Kasteller - Sitio Web/`.
