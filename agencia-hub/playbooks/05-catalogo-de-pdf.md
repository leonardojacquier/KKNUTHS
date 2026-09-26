# 05 — Catálogo a partir de PDF do fabricante

Quando o cliente manda um catálogo com muitos produtos (10, 20, 100), **não se escreve página
a mão**. Monta-se um gerador. Exemplos reais: `../gen-minicargadoras/` (20 modelos + 89
implementos) e `../gen-britagem/` (13 linhas de trituração).

## Passos
1. **Ler o PDF página por página.** Extraia texto (`ferramentas/pdf-para-texto.py`). Se as
   tabelas forem imagem, renderize a página e transcreva olhando (não confie em OCR para números).
2. **Transcrever para `dados.py`**, um dicionário por modelo, com a página de origem.
   Valor duvidoso no catálogo (unidade trocada, sem rótulo) → omitir e anotar o motivo.
3. **Texto em `contenido.py`**: nome, frase do card, parágrafo "para que serve". Sem inventar
   número: o texto só usa o que está em `dados.py`.
4. **Fotos:** `ferramentas/extrair-imagens-pdf.py` tira as fotos originais do PDF (muitas já vêm
   com transparência). Depois `playbooks/06`.
5. **`gen_site.py`** escreve: página por modelo, página da linha, categoria, fichas HTML+PDF
   (`playbooks/07`), entradas no catálogo/busca e sitemap. Tem de ser **idempotente**: rodar
   duas vezes dá o mesmo resultado.
6. **Verificar** (`playbooks/10`) e registrar as decisões de transcrição no vault do cliente.

## O que o dono já cobrou
- Número inventado é o pior erro. Na dúvida, fora.
- Manual/ficha do fabricante vence folder de marketing quando divergem (ex.: peso da N50).
- Nome do produto como o cliente fala (ex.: "cortadora de juntas").
