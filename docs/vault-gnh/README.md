# Vault Obsidian — GNH Sitio Web

Documentação completa do site `gnhorizons.com`, em formato Obsidian
(wikilinks `[[...]]`, frontmatter YAML, callouts e diagramas Mermaid).

## Como instalar no seu vault

Copie a pasta **`GNH - Sitio Web/`** para dentro do seu vault no Dropbox:

```
~/Dropbox/<seu-vault>/GNH - Sitio Web/
```

Abra o Obsidian — as 13 notas aparecem já ligadas entre si. Comece por
**`00 - Indice`** (é o mapa).

Nada aqui depende de plugin: só Markdown, wikilinks e Mermaid (nativo no Obsidian).

## As notas

| Nota | Assunto |
|---|---|
| `00 - Indice` | Mapa geral + estado atual |
| `01 - Arquitetura do site` | Estrutura, build, fonte única de dados |
| `02 - Infraestrutura e DNS` | VPS, Caddy, Cloudflare, e-mails |
| `03 - Deploy` | Como o código vai pro ar |
| `04 - Catalogo e fichas tecnicas` | Produtos, specs, geradores, PDFs |
| `05 - Analytics e rastreamento` | Supabase, eventos, Telegram, anti-bot |
| `06 - SEO e GEO` | Sitemap, dados estruturados, o que falta |
| `07 - Promocoes e campanhas` | Landing, links UTM, preview nas redes |
| `08 - Marca e conteudo` | Posicionamento, paleta, tipografia |
| `09 - Operacao diaria` | Receitas prontas do dia a dia |
| `10 - Pendencias e roadmap` | O que falta, por impacto |
| `11 - Decisoes` | Decisões e o porquê |
| `12 - Glossario` | Termos usados na documentação |

## Manutenção

A documentação vive **no repositório** (`docs/vault-gnh/`) para versionar junto com o
código. Ao atualizar, edite aqui e copie de novo para o Dropbox — ou aponte o vault
direto para esta pasta, se preferir.

Cada nota tem `atualizado:` no frontmatter. Mantenha a data ao editar.

> **Segredos:** por convenção do projeto, a documentação registra *onde* cada
> token/senha mora, nunca o valor.
