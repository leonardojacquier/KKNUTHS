# Hub da Agência

Central de trabalho da agência de marketing: **sites, catálogos de produtos, fichas técnicas,
campanhas e conteúdo** para clientes. Tudo em Markdown e arquivos simples, pensado para
trabalhar junto com **Claude** (Claude Code) e o **Cursor**.

## Como abrir no Cursor

O hub vive na pasta `agencia-hub/` do repositório `leonardojacquier/KKNUTHS`.

**1. Clonar o repositório (uma vez só)**

No Cursor: `Ctrl+Shift+P` (no Mac `Cmd+Shift+P`) → **Git: Clone** → cole:

```
https://github.com/leonardojacquier/KKNUTHS.git
```

Escolha uma pasta no seu computador (ex.: `Documentos/`). Pelo terminal é o mesmo:

```bash
git clone https://github.com/leonardojacquier/KKNUTHS.git
cd KKNUTHS
git checkout claude/professional-website-design-qqgnfg
```

**2. Abrir o hub**

No Cursor: **File → Open Folder** → escolha:

```
<onde-você-clonou>/KKNUTHS/agencia-hub
```

Exemplo no Windows: `C:\Users\Leonardo\Documentos\KKNUTHS\agencia-hub`
Exemplo no Mac: `/Users/leonardo/Documentos/KKNUTHS/agencia-hub`

O Cursor lê sozinho as regras em `.cursor/rules/` e o `AGENTS.md`: o chat do Cursor já
entra sabendo como a agência trabalha.

**3. Atualizar antes de trabalhar**

Na barra de baixo do Cursor, clique no ícone de sincronizar, ou no terminal:

```bash
git pull
```

## Como usar com Claude

- **No navegador ou no celular** (claude.ai/code): abra uma sessão no repositório `KKNUTHS` e
  diga "trabalhe no agencia-hub". O Claude lê o `CLAUDE.md` desta pasta.
- **Dentro do Cursor**: instale a extensão **Claude Code** (Extensions → "Claude Code") ou
  rode `claude` no terminal integrado, já dentro de `agencia-hub/`.

## Mapa

| Pasta | Para quê |
|---|---|
| `clientes/` | Uma pasta por cliente: briefing, marca, conteúdo, entregas. `_modelo/` é o molde. |
| `playbooks/` | Como fazemos cada tipo de trabalho, passo a passo, com o que já aprendemos. |
| `propostas/` | Modelo de proposta comercial e catálogo de serviços. |
| `ferramentas/` | Scripts prontos: criar cliente, recortar fundo de foto, extrair imagens de PDF. |

## Começar um cliente novo

```bash
bash ferramentas/novo-cliente.sh "Nome do Cliente"
```

Cria `clientes/nome-do-cliente/` a partir do molde. Depois, preencha `briefing.md` com o
cliente e siga `playbooks/01-onboarding.md`.

## Clientes atuais

| Cliente | Site | Onde está o código |
|---|---|---|
| GNH (Grupo GNH) | gnhorizons.com | raiz do repositório KKNUTHS (`assets/nuevo/`, `gnh-redesign.html`) |
| Kasteller Revestimientos | kasteller.com.py | `assets/kasteller2/` |

## ⚠️ Repositório público

O KKNUTHS é **público**. Aqui só entram modelos, playbooks e material que já está publicado.
**Não coloque** senhas, contratos, preços negociados, dados pessoais de clientes nem
briefings confidenciais. Para isso, crie um repositório **privado** só da agência e rode
`bash mover-para-repo-proprio.sh` (instruções no próprio script).
