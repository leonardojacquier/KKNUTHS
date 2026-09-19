# Skills no repositório

As 14 skills abaixo vêm do pacote **superpowers** de Jesse Vincent
(github.com/obra/superpowers), versão 6.3.0, licença MIT — a licença está
em `LICENSE-superpowers` nesta pasta.

## Por que estão copiadas aqui, e não instaladas como plugin

`claude plugin install` grava a declaração em `~/.claude/settings.json` e
baixa os arquivos para `~/.claude/plugins/cache/`. Numa sessão remota isso
não sobrevive: o container nasce vazio, e a declaração sozinha aponta para
arquivos que não existem — a sessão nova abre sem as skills. Copiadas para
`.claude/skills/` do repositório, elas vêm no clone: sem rede, sem
marketplace, sem depender de instalação no arranque.

O custo dessa escolha: ficam congeladas na 6.3.0. Para atualizar:

```bash
claude plugin marketplace add obra/superpowers
cp -r ~/.claude/plugins/marketplaces/superpowers-dev/skills/* .claude/skills/
```

## Como chamar

Pelo nome, com a barra — por exemplo `/test-driven-development`. Sendo
skills do projeto (e não de plugin), elas NÃO levam mais o prefixo
`superpowers:`.

## O que ficou de fora

O hook de SessionStart do pacote original, que injeta um lembrete das
skills a cada início de sessão. Sem ele nada quebra: as skills continuam
chamáveis, e a sessão não paga o custo fixo do lembrete.

Catálogo em português das 42 skills disponíveis (estas 14 + as da conta +
as nativas do Claude Code): ver o artefato "Caixa de Ferramentas KKNuths".
