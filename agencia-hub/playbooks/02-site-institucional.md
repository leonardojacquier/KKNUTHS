# 02 — Site institucional

**Ponto de partida:** `clientes/_modelo/site/index.html` (arquivo único, sem build).

1. Copie o molde para `clientes/<cliente>/site/` (o `novo-cliente.sh` já faz isso).
2. Ajuste os tokens de cor em `:root` com `marca.md`.
3. Troque todos os `{{...}}`. Confirme com `grep -n "{{" index.html` (tem de voltar vazio).
4. A ação principal é **WhatsApp** (Paraguai compra por WhatsApp): botão no topo, no hero,
   em cada produto e o botão flutuante. Mensagem pré-preenchida com o produto.
5. Estrutura que funciona: hero com promessa → produtos → números/confiança → contato.
6. Fotos: `playbooks/06`. Textos: frases curtas, dado real, sem superlativo vazio.
7. Qualidade: `playbooks/10`.

**Lições da GNH**
- Separar o comercial (vender) do institucional (confiar). O institucional não tem catálogo.
- O dono aprova o visual: não "corrija" um layout que ele escolheu.
- Uma pessoa no Paraguai pode escrever em português: inclua termos em português nas buscas
  e no `llms.txt` (ex.: "minicarregadeira", "argamassadeira").
