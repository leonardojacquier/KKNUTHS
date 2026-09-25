# Voz do Coach — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a análise do coach soar como conversa — técnica, didática, sem repetir o que o placar já disse — sem afrouxar nenhuma garantia numérica existente.

**Architecture:** Três camadas, na ordem em que rodam. O **prompt** (`_SYSTEM["pt"]`) pede a voz nova; o **guarda** (`app/bot/guarda_voz.py`, função pura) mede o que dá para medir e conserta só o que é seguro consertar; o **juiz** (`scripts/output_judge.py`) conta os defeitos novos em contadores separados da nota, para a série de 7 dias não mudar de significado no meio.

**Tech Stack:** Python 3.11, pytest, Anthropic SDK, Supabase (postgrest client). Sem dependência nova.

**Spec:** `backend/docs/superpowers/specs/2026-08-15-voz-do-coach-design.md`

## Global Constraints

- **Diretório de trabalho é `backend/`.** Todos os caminhos deste plano são relativos a ele. No VPS o app mora em `/opt/poker-bot` — nunca `/app/backend`.
- **Todo teste é determinístico.** Teste que chama LLM já travou o deploy deste projeto uma vez. Nenhum teste novo pode fazer chamada de rede.
- **O portão do deploy são os 971 testes.** `PYTHONPATH=. pytest -q` tem que passar inteiro no fim de cada tarefa.
- **Não empurrar para produção antes da leitura do juiz de 16/08** (spec §6). Commitar na branch, sim; considerar entregue, não.
- **Selo (R1) e placar (R2) são intocáveis.** Nenhuma tarefa altera essas duas regras.
- **Teto do bloco pós-placar: `TETO_POS_PLACAR = 800`** (medido: média 740, 34% acima de 800).
- **Nada de `git add -f`.** O push protection já salvou este repo uma vez.
- **Correção à spec, obrigatória:** o alvo de bastidor é a **narração de busca** ("deixa eu conferir", "vou puxar") — 91/403 = 23%. A frase "anotei no caderno" (32/403 = 8%) **não é defeito** e não pode ser removida: é voz de coach e é a regra A2 funcionando. A spec §4 dizia o contrário; este plano prevalece.

---

### Task 1: `guarda_voz.py` — as medições puras

**Files:**
- Create: `app/bot/guarda_voz.py`
- Test: `tests/test_voz_do_coach.py`

**Interfaces:**
- Consumes: nada (função pura, sem I/O)
- Produces: `TETO_POS_PLACAR: int`, `bloco_pos_placar(texto: str) -> str`, `numeros_repetidos(texto: str) -> list[str]`, `problemas_de_voz(texto: str) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voz_do_coach.py
"""A análise soa como conversa ou como formulário?

Medido em 403 análises reais (45 dias): o bloco depois do placar é 58% do
texto (740 de 1662 chars, n=183); o título fixo "A conta que mais pesa"
aparece em 102 delas (25%); a narração de bastidor sobrevive em 91 (23%).
"""
from __future__ import annotations

from app.bot.guarda_voz import (TETO_POS_PLACAR, bloco_pos_placar,
                                numeros_repetidos, problemas_de_voz)

ANALISE_REAL = """\
❌ Jogada cara — abriu pequeno com stack de shove e depois desistiu do pote

🟡 *Pré* — abrir 2.8bb com K♦Q♦ (18.7bb) no BTN: jammar rende +1.49bb.
❌ *Turn* 5♦ — deu check behind: você tinha 35% e muita equity de barrel.

A conta que mais pesa: com 18.7bb o BTN é território de jam — empurrar
K♦Q♦ rende +1.49bb vs foldar.
"""


def test_bloco_pos_placar_comeca_depois_da_ultima_linha_de_selo():
    bloco = bloco_pos_placar(ANALISE_REAL)
    assert bloco.startswith("A conta que mais pesa")
    assert "check behind" not in bloco, "o placar vazou para dentro do bloco"


def test_sem_selo_nenhum_o_bloco_e_vazio():
    assert bloco_pos_placar("papo solto sobre range, sem análise") == ""


def test_numero_do_placar_repetido_na_prosa_e_detectado():
    assert "+1.49bb" in numeros_repetidos(ANALISE_REAL)


def test_numero_que_so_existe_no_placar_nao_conta_como_repetido():
    assert "35%" not in numeros_repetidos(ANALISE_REAL)


def test_titulo_fixo_e_apontado():
    assert any("título fixo" in p for p in problemas_de_voz(ANALISE_REAL))


def test_bloco_longo_e_apontado():
    longo = "✅ Você jogou bem — call fácil\n\n" + ("palavra " * 200)
    assert any("bloco pós-placar" in p for p in problemas_de_voz(longo))
    assert len(bloco_pos_placar(longo)) > TETO_POS_PLACAR


def test_narracao_de_bastidor_e_apontada():
    t = "✅ Você jogou bem — call fácil\n\nDeixa eu conferir o EV desse shove."
    assert any("bastidor" in p for p in problemas_de_voz(t))


def test_anotacao_no_caderno_NAO_e_defeito():
    """32 análises trazem isso e é voz de coach, não bastidor de sistema —
    é a regra A2 (record_student_note) aparecendo para o aluno. Apagar
    seria remover a frase mais humana da resposta."""
    t = "✅ Você jogou bem — call fácil\n\nAnotei no caderno pra próxima."
    assert problemas_de_voz(t) == []


def test_autocorrecao_e_apontada():
    t = "✅ Você jogou bem\n\nAbriu 6♦... digo, abriu 2bb com 66."
    assert any("autocorreção" in p for p in problemas_de_voz(t))


def test_analise_limpa_nao_tem_problema_nenhum():
    limpa = ("✅ Você jogou bem — set flopado\n\n"
             "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb: board conectado.\n\n"
             "Com set em board de draw, empacotar é obrigatório.")
    assert problemas_de_voz(limpa) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_voz_do_coach.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.bot.guarda_voz'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/bot/guarda_voz.py
"""GUARDA DA VOZ — a análise soa como conversa ou como formulário?

Por que existe: medido em 403 análises reais de 45 dias, o bloco depois do
placar é 58% do texto (740 de 1662 chars, n=183), e boa parte dele repete o
que o placar já disse. O título "A conta que mais pesa" aparece em 25% —
e a origem era NOSSA, escrita na instrução do coach em llm.py. A narração
de bastidor ("deixa eu conferir o EV...") sobrevive em 23%.

Regra é pedido; conferência é garantia. O R3/R7 do prompt pedem; isto mede
e, onde é seguro, conserta.

O que CORRIGE e o que só MEDE, e o porquê de cada escolha:
  corrige  título fixo         rótulo sai sem tocar na frase (Task 2)
  corrige  narração de busca   frase inteira de bastidor, sai limpa
  mede     bloco pós-placar    cortar prosa de LLM na marra estraga
  mede     autocorreção        n=4 em 403; conserto arrisca mais que resolve
  mede     número repetido     repetir a conta no fecho pode ser ÊNFASE

O que NÃO é defeito, apesar de parecer: "anotei no caderno" (32 análises).
É voz de coach e é a regra A2 funcionando. A primeira versão da spec mandava
apagar — teria removido a frase mais humana da resposta.
"""
from __future__ import annotations

import re

# medido: média de 740 chars depois do placar, 34% das análises acima de 800
TETO_POS_PLACAR = 800

_SELOS = ("✅", "🟡", "❌")

# "A conta que mais pesa:" com ou sem negrito markdown em volta
_TITULO_FIXO = re.compile(
    r"\*{0,2}\s*a\s+conta\s+que\s+mais\s+pesa\s*\*{0,2}\s*:\s*\*{0,2}\s*",
    re.I)

# bastidor de BUSCA — 91/403. NÃO inclui "anotei no caderno", que é voz de
# coach: o guarda que apaga isso piora exatamente o que viemos melhorar.
_NARRACAO = re.compile(
    r"\b(deixa\s+eu\s+(conferir|ver|puxar|checar|rodar|calcular)|"
    r"vou\s+(conferir|puxar|checar|rodar|calcular)|"
    r"me\s+deixa\s+(ver|conferir))\b", re.I)

_AUTOCORRECAO = re.compile(r"\.{2,3}\s*digo\b", re.I)

# números que contam: 12bb, 34%, +1.49bb, -0,6bb
_NUMERO = re.compile(r"[-+]?\d+[.,]?\d*\s*(?:bb|%)")


def bloco_pos_placar(texto: str) -> str:
    """Tudo que vem DEPOIS da última linha de placar.

    É o sinal principal. A primeira versão media 'número repetido', que dá
    para contar por regex mas mira o sintoma: repetir o +1.49bb no fecho é
    ênfase legítima. O defeito é o parágrafo INTEIRO não acrescentar nada,
    e o proxy medível disso é o comprimento.
    """
    linhas = (texto or "").split("\n")
    ultimo = -1
    for i, ln in enumerate(linhas):
        if ln.lstrip().startswith(_SELOS):
            ultimo = i
    if ultimo < 0:
        return ""
    return "\n".join(linhas[ultimo + 1:]).strip()


def numeros_repetidos(texto: str) -> list[str]:
    """Números que aparecem no placar E de novo na prosa do fechamento."""
    linhas = (texto or "").split("\n")
    do_placar = {m.group(0).replace(" ", "")
                 for ln in linhas if ln.lstrip().startswith(_SELOS)
                 for m in _NUMERO.finditer(ln)}
    na_prosa = {m.group(0).replace(" ", "")
                for m in _NUMERO.finditer(bloco_pos_placar(texto))}
    return sorted(do_placar & na_prosa)


def problemas_de_voz(texto: str) -> list[str]:
    """Defeitos de VOZ numa resposta do coach (lista vazia = passou).

    Função pura — é o contrato que o R3/R7 do prompt promete ao aluno.
    """
    t = (texto or "").strip()
    if not t:
        return []
    probs: list[str] = []

    bloco = bloco_pos_placar(t)
    if len(bloco) > TETO_POS_PLACAR:
        probs.append(f"bloco pós-placar longo ({len(bloco)} chars; "
                     f"teto {TETO_POS_PLACAR})")
    if _TITULO_FIXO.search(t):
        probs.append("título fixo 'A conta que mais pesa'")
    if _NARRACAO.search(t):
        probs.append("bastidor de busca narrado ao aluno")
    if _AUTOCORRECAO.search(t):
        probs.append("autocorreção dentro do texto entregue")
    repetidos = numeros_repetidos(t)
    if repetidos:
        probs.append(f"número do placar repetido na prosa: "
                     f"{', '.join(repetidos[:4])}")
    return probs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_voz_do_coach.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Run the full suite (nothing may break)**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS — os 971 anteriores + 10 novos

- [ ] **Step 6: Commit**

```bash
git add app/bot/guarda_voz.py tests/test_voz_do_coach.py
git commit -m "Guarda da voz: as medições puras

Bloco pós-placar (58% do texto em 403 análises), título fixo (25%),
narração de bastidor (23%), autocorreção (1%), número repetido.

'Anotei no caderno' NÃO entra: é voz de coach, não bastidor."
```

---

### Task 2: `guarda_voz.py` — a limpeza que não estraga português

**Files:**
- Modify: `app/bot/guarda_voz.py` (acrescenta `limpar`)
- Test: `tests/test_voz_do_coach.py` (acrescenta a classe de testes de limpeza)

**Interfaces:**
- Consumes: `_TITULO_FIXO`, `_NARRACAO` da Task 1
- Produces: `limpar(texto: str) -> tuple[str, list[str]]` — devolve (texto novo, lista do que foi corrigido)

- [ ] **Step 1: Write the failing test**

```python
# acrescentar ao fim de tests/test_voz_do_coach.py
from app.bot.guarda_voz import limpar


def test_titulo_fixo_sai_e_a_frase_vira_maiuscula():
    t = ("✅ Você jogou bem — call fácil\n\n"
         "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.")
    novo, feitos = limpar(t)
    assert "conta que mais pesa" not in novo
    assert "Com 12bb, AK em HJ é jam pré-flop." in novo
    assert any("título fixo" in f for f in feitos)


def test_titulo_nao_sai_quando_a_frase_nao_sobrevive_sozinha():
    """'A conta que mais pesa: que você paga sempre' — tirar o rótulo deixa
    um fragmento. Este repositório já tem test_corretor_nao_estraga_portugues
    para esta classe exata de bug; o guarda novo não pode reintroduzi-la."""
    t = ("✅ Você jogou bem\n\n"
         "A conta que mais pesa: que você paga sempre sem pensar.")
    novo, feitos = limpar(t)
    assert novo == t, "o guarda partiu a frase ao meio"
    assert feitos == []


def test_narracao_de_bastidor_sai_a_frase_inteira():
    t = ("✅ Você jogou bem — call fácil\n\n"
         "Deixa eu conferir o EV desse shove. Com 12bb o jam é claro.")
    novo, feitos = limpar(t)
    assert "Deixa eu conferir" not in novo
    assert "Com 12bb o jam é claro." in novo
    assert any("bastidor" in f for f in feitos)


def test_anotacao_no_caderno_sobrevive_a_limpeza():
    t = "✅ Você jogou bem\n\nAnotei no caderno pra puxarmos na próxima."
    novo, feitos = limpar(t)
    assert novo == t
    assert feitos == []


def test_autocorrecao_NAO_e_corrigida_so_medida():
    """n=4 em 403. Frequência baixa demais e falso positivo plausível na
    fala natural ('não é fold... digo, não sempre')."""
    t = "✅ Você jogou bem\n\nAbriu 6♦... digo, abriu 2bb com 66."
    novo, _ = limpar(t)
    assert novo == t


def test_analise_limpa_passa_intacta():
    limpa = ("✅ Você jogou bem — set flopado\n\n"
             "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb.\n\n"
             "Com set em board de draw, empacotar é obrigatório.")
    novo, feitos = limpar(limpa)
    assert novo == limpa
    assert feitos == []


def test_limpar_nunca_devolve_vazio():
    """Degradar para nada é pior do que entregar com defeito."""
    t = "Deixa eu conferir o EV desse shove."
    novo, _ = limpar(t)
    assert novo.strip(), "o guarda comeu a resposta inteira"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_voz_do_coach.py -k limpar -v`
Expected: FAIL — `ImportError: cannot import name 'limpar'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar ao fim de app/bot/guarda_voz.py

# palavras que, logo depois do rótulo, denunciam que a frase DEPENDIA dele:
# tirar o rótulo deixaria um fragmento sem sujeito.
_FRAGMENTO = re.compile(r"^(que|porque|por\s+que|e|mas|ou|então|pois|se)\b",
                        re.I)


def _sem_titulo_fixo(texto: str) -> tuple[str, bool]:
    """Tira o rótulo e promove a frase a início de parágrafo.

    Só quando ela sobrevive sozinha: 'A conta que mais pesa: que você paga
    sempre' vira fragmento se o rótulo sair, e frase partida é o defeito que
    test_corretor_nao_estraga_portugues existe para impedir.
    """
    saida: list[str] = []
    pos = 0
    mexeu = False
    for m in _TITULO_FIXO.finditer(texto):
        resto = texto[m.end():]
        cabeca = resto.lstrip()
        if not cabeca or _FRAGMENTO.match(cabeca):
            continue
        salto = len(resto) - len(cabeca)
        saida.append(texto[pos:m.start()])
        saida.append(texto[m.end():m.end() + salto])
        saida.append(cabeca[0].upper())
        pos = m.end() + salto + 1
        mexeu = True
    saida.append(texto[pos:])
    return "".join(saida), mexeu


def _sem_narracao(texto: str) -> tuple[str, bool]:
    """Remove a FRASE inteira de bastidor, não só a expressão.

    Cortar só 'deixa eu conferir' deixaria 'o EV desse shove.' solto, que é
    pior do que a frase original.
    """
    mexeu = False
    saidas: list[str] = []
    for paragrafo in texto.split("\n"):
        # divide preservando o pontuador final de cada frase
        frases = re.findall(r"[^.!?]+[.!?]*", paragrafo)
        mantidas = [f for f in frases if not _NARRACAO.search(f)]
        if len(mantidas) != len(frases):
            mexeu = True
            paragrafo = "".join(mantidas).strip()
        saidas.append(paragrafo)
    return "\n".join(saidas), mexeu


def limpar(texto: str) -> tuple[str, list[str]]:
    """Corrige o que é seguro corrigir. Devolve (texto, o que foi feito).

    Nunca degrada abaixo do que já ia sair: se a limpeza esvaziar o texto,
    a original volta. Mesma disciplina do _conferir_numeros em llm.py.
    """
    t = texto or ""
    if not t.strip():
        return texto, []
    feitos: list[str] = []

    novo, mexeu = _sem_titulo_fixo(t)
    if mexeu:
        feitos.append("título fixo removido")
    novo, mexeu = _sem_narracao(novo)
    if mexeu:
        feitos.append("bastidor de busca removido")

    if not novo.strip():
        return texto, []
    return novo, feitos
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_voz_do_coach.py -v`
Expected: PASS — 17 passed

- [ ] **Step 5: Mutation test (obrigatório — METODO §7)**

Quebre a guarda do fragmento: em `_sem_titulo_fixo`, troque
`if not cabeca or _FRAGMENTO.match(cabeca):` por `if not cabeca:`.

Run: `PYTHONPATH=. pytest tests/test_voz_do_coach.py -k sobrevive -v`
Expected: **FAIL** em `test_titulo_nao_sai_quando_a_frase_nao_sobrevive_sozinha`.

Se passar, o teste é decorativo — conserte o teste antes de seguir. **Desfaça a mutação** e rode de novo (Expected: PASS).

- [ ] **Step 6: Commit**

```bash
git add app/bot/guarda_voz.py tests/test_voz_do_coach.py
git commit -m "Guarda da voz: limpeza que não estraga português

Rótulo só sai quando a frase sobrevive sozinha; bastidor sai como frase
inteira; autocorreção é medida e nunca corrigida. Teste de mutação na
guarda do fragmento."
```

---

### Task 3: Ligar o guarda nos dois caminhos

**Files:**
- Modify: `app/bot/processing.py` — caminho da ANÁLISE (depois do `guarda_fatos`, ~linha 530) e caminho da CONVERSA (depois do `guarda_saida`, ~linha 1215)
- Test: `tests/test_voz_do_encanamento.py`

**Interfaces:**
- Consumes: `problemas_de_voz`, `limpar` (Tasks 1-2)
- Produces: eventos `voz_corrigida` e `voz_medida` em `bot_events`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voz_do_encanamento.py
"""O guarda da voz está LIGADO nos dois caminhos que falam com o aluno.

Teste por AST, não por substring do código-fonte. O METODO §8 documenta o
caso: um teste que comparava texto do fonte protegia um portão que podia
já nem existir, e invertendo a condição em produção os 971 testes passavam.
"""
from __future__ import annotations

import ast
import pathlib


def _fonte() -> ast.Module:
    p = pathlib.Path(__file__).resolve().parents[1] / "app/bot/processing.py"
    return ast.parse(p.read_text(encoding="utf-8"))


def _nomes_importados(arvore: ast.Module) -> set[str]:
    achados = set()
    for node in ast.walk(arvore):
        if isinstance(node, ast.ImportFrom) and node.module == "app.bot.guarda_voz":
            achados.update(a.name for a in node.names)
    return achados


def test_o_guarda_da_voz_e_importado_no_processing():
    assert {"limpar", "problemas_de_voz"} <= _nomes_importados(_fonte()), \
        "guarda_voz não é usado em processing.py — o guarda existe e não roda"


def test_limpar_e_chamado_pelo_menos_duas_vezes():
    """Um caminho é a análise, o outro é a conversa. Ligar só num deles
    deixa metade do produto falando do jeito antigo."""
    chamadas = [n for n in ast.walk(_fonte())
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "limpar"]
    assert len(chamadas) >= 2, f"limpar() chamado {len(chamadas)}x, esperado 2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_voz_do_encanamento.py -v`
Expected: FAIL — `guarda_voz não é usado em processing.py`

- [ ] **Step 3: Write minimal implementation**

No caminho da **análise**, logo depois do bloco do `guarda_fatos` (após a
linha que registra `fato_corrigido`, ~530), acrescente:

```python
    # GUARDA DA VOZ: a análise soa como conversa ou como formulário? Mede o
    # bloco pós-placar (58% do texto, medido) e tira o que é seguro tirar.
    if coaching:
        try:
            from app.bot.guarda_voz import limpar, problemas_de_voz

            problemas = problemas_de_voz(coaching)
            coaching, feitos = limpar(coaching)
            if repo.enabled and (feitos or problemas):
                repo.log_event(
                    telegram_id, username,
                    "voz_corrigida" if feitos else "voz_medida",
                    {"feitos": feitos, "problemas": problemas[:6]})
        except Exception as exc:
            log.warning("guarda da voz falhou: %s", exc)
```

No caminho da **conversa**, logo depois do bloco do `guarda_saida`
(~1215), acrescente:

```python
    # GUARDA DA VOZ também na conversa: é metade do que o aluno percebe
    # como "o coach falando".
    try:
        from app.bot.guarda_voz import limpar, problemas_de_voz

        problemas = problemas_de_voz(answer)
        answer, feitos = limpar(answer)
        if feitos or problemas:
            repo.log_event(telegram_id, None,
                           "voz_corrigida" if feitos else "voz_medida",
                           {"onde": "conversa", "feitos": feitos,
                            "problemas": problemas[:6]})
    except Exception as exc:
        log.warning("guarda da voz na conversa falhou: %s", exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_voz_do_encanamento.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Run the full suite**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/bot/processing.py tests/test_voz_do_encanamento.py
git commit -m "Guarda da voz ligado na análise e na conversa

Teste por AST, não por substring do fonte — o METODO §8 documenta o
teste decorativo que protegia um portão que podia já nem existir."
```

---

### Task 4: O prompt — R3, R7, V4 e a instrução que plantava o título

**Files:**
- Modify: `app/agent/llm.py` — `_SYSTEM["pt"]` (R3 ~linha 696, R7 ~744, V4 ~902), `instruction` do `coach()` (~1854), bloco do `followup()` (~2294)
- Test: `tests/test_prompt_da_voz.py`

**Interfaces:**
- Consumes: nada
- Produces: nada em código; o contrato de texto que o guarda da Task 1 mede

**Esta é a tarefa de maior risco do plano.** O texto aqui fala com todos os
alunos, e o prompt deste projeto já se contradisse duas vezes
(`test_prompt_nao_briga_consigo.py`, `test_prompt_nao_ensina_o_que_proibe.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_da_voz.py
"""O prompt pede a voz nova — e não briga com o que já pedia."""
from __future__ import annotations

import inspect

from app.agent import llm

PROMPT = llm._SYSTEM["pt"]


def test_a_instrucao_nao_planta_mais_o_titulo_fixo():
    """llm.py:1854 mandava 'Feche com A conta que mais pesa.' — o formulário
    que apareceu em 25% das análises era pedido nosso, por escrito."""
    fonte = inspect.getsource(llm.coach)
    assert "conta que mais pesa" not in fonte.lower(), \
        "a instrução do coach ainda planta o título fixo"


def test_o_prompt_proibe_o_titulo_fixo():
    assert "conta que mais pesa" in PROMPT.lower(), \
        "o prompt precisa NOMEAR o título para proibi-lo"


def test_o_prompt_proibe_repetir_numero_do_placar_no_fechamento():
    baixo = PROMPT.lower()
    assert "já apareceu no placar" in baixo or "repet" in baixo


def test_o_prompt_manda_explicar_o_conceito():
    assert "por que" in PROMPT.lower() or "porquê" in PROMPT.lower()


def test_o_prompt_permite_parentese_didatico_na_primeira_aparicao():
    """O V4 antigo PROIBIA parêntese didático na análise. O dono pediu
    conceito + termo explicados, então a proibição vira exceção regrada."""
    baixo = PROMPT.lower()
    assert "primeira aparição" in baixo or "primeira vez" in baixo


def test_o_selo_e_o_placar_continuam_obrigatorios():
    """Regra de ouro. Nenhuma mudança de voz pode afrouxá-la."""
    assert "R1 SELO NA 1ª LINHA" in PROMPT
    assert "R2 PLACAR STREET A STREET" in PROMPT


def test_o_prompt_nao_pede_e_proibe_a_mesma_coisa():
    """O V4 novo manda explicar; o R7 proíbe parágrafo longo. A saída é a
    explicação morar DENTRO do porquê curto do placar — se o prompt não
    disser onde, ele briga consigo."""
    assert "dentro do porquê" in PROMPT.lower() or \
           "no porquê da linha" in PROMPT.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_prompt_da_voz.py -v`
Expected: FAIL — 6 de 7 falham (o `test_o_selo_e_o_placar_continuam_obrigatorios` já passa)

- [ ] **Step 3: Write minimal implementation**

**3a.** Em `coach()` (~1854), a instrução perde a frase do título:

```python
        instruction = (
            "Analise esta mão. Comece pelo SELO de veredito na 1ª linha "
            "(✅ Você jogou bem / 🟡 Dava pra jogar melhor / ❌ Jogada cara). "
            "Se o herói agiu em mais de uma street, traga o PLACAR street a "
            "street logo abaixo (uma linha por street, cada uma com selo, "
            "ancorada em linha_da_mao/hand_by_street). Feche em no máximo 2 "
            "parágrafos curtos, sem título fixo e sem repetir número que já "
            "está no placar. Siga a regra de CLAREZA à risca. Dados "
            "estruturados (números já calculados, use-os; tools só para "
            "cálculos adicionais):\n\n"
        )
```

**3b.** R3 (~696) passa a ser:

```python
        "R3 FECHAMENTO: depois do placar, no MÁXIMO 2 parágrafos curtos, e "
        "cada um tem que dizer algo que o placar NÃO disse. PROIBIDO título "
        "fixo ('A conta que mais pesa:', 'Resumo:', 'O que treinar:') — o "
        "parágrafo entra sem rótulo. PROIBIDO repetir número que já apareceu "
        "no placar: lá está a conta, aqui está o PORQUÊ. Medido: hoje esse "
        "bloco é 58% do texto e boa parte só reescreve o placar com outras "
        "palavras. 'O que treinar' só aparece se houver algo novo a dizer — "
        "não é seção obrigatória. Em análise de SESSÃO/torneio (vários "
        "spots), o fechamento vira plano de 2-3 ações.\n"
```

**3c.** R7 (~744) ganha, ao fim da lista de proibições:

```python
        "; autocorreção dentro do texto ('abriu 6♦... digo, abriu 2bb') — "
        "escreva a versão certa e só ela; narrar bastidor de busca ('deixa "
        "eu conferir o EV', 'vou puxar o histórico') — a conta aparece "
        "pronta, o aluno não acompanha o processo.\n"
```

**3d.** V4 (~902) reescrito por inteiro:

```python
        "V4 TÉCNICO E DIDÁTICO AO MESMO TEMPO: o jargão fica cru, e a frase "
        "diz POR QUE aquilo decide o spot — não basta nomear. 'Deu check "
        "behind no turn' é rótulo; 'deu check behind no turn e abriu mão de "
        "uma rodada de valor contra um range que paga' é coaching. Essa "
        "explicação mora DENTRO do porquê curto da linha do placar, nunca "
        "como parágrafo novo: explicar em prosa extra infla justamente o "
        "bloco que o R3 corta. O TERMO ganha parêntese curto (até ~6 "
        "palavras) na PRIMEIRA APARIÇÃO e só nela — 'fold equity (a chance "
        "de ele largar)'. Máximo 2 parênteses desses por resposta; acima "
        "disso vira glossário e o texto volta a ser formulário. EXCEÇÃO "
        "SEPARADA: se o aluno disser 'não entendi', 'como assim' ou 'muito "
        "complicado', reexplique a MESMA ideia pra um iniciante total — uma "
        "analogia do dia a dia, zero jargão, no máximo 1 número explicado, "
        "sem introduzir conceito novo.\n"
```

**3e.** No `followup()` (~2294), acrescente ao bloco de sistema:

```python
            "\nVOZ: vale o V4 — o jargão fica cru e a frase diz por que "
            "aquilo decide o spot; termo novo ganha parêntese curto na "
            "primeira aparição. Sem título fixo, sem repetir número que já "
            "está na análise, e sem narrar bastidor de busca. "
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. pytest tests/test_prompt_da_voz.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Run the prompt-coherence tests that already exist**

Run: `PYTHONPATH=. pytest tests/test_prompt_nao_briga_consigo.py tests/test_prompt_nao_ensina_o_que_proibe.py -v`
Expected: PASS. **Se falhar, o prompt novo se contradiz — conserte o prompt, nunca o teste.**

- [ ] **Step 6: Run the full suite**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/agent/llm.py tests/test_prompt_da_voz.py
git commit -m "Prompt: fechamento sem formulário, técnico e didático

R3 limita o pós-placar a 2 parágrafos que acrescentem algo; R7 proíbe
autocorreção e narração de bastidor; V4 manda explicar o conceito DENTRO
do porquê do placar e abre parêntese de termo na primeira aparição.

A instrução do coach() perde 'Feche com A conta que mais pesa' — o
formulário de 25% das análises era pedido nosso, por escrito."
```

---

### Task 5: O juiz conta o defeito novo sem mudar de régua

**Files:**
- Modify: `scripts/output_judge.py` — `main()`, no bloco que monta `achados`
- Test: `tests/test_juiz_nao_muda_de_regua.py`

**Interfaces:**
- Consumes: `problemas_de_voz` (Task 1)
- Produces: seção "voz (contadores novos)" no relatório do juiz

**A nota 0-10 e `judge_answer` NÃO mudam.** Trocar a régua no mesmo dia em
que o texto muda faz a média móvel de 7 dias mudar de significado no meio
da série, e nenhuma comparação antes/depois vale.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_juiz_nao_muda_de_regua.py
"""O juiz ganha contadores novos, e a NOTA continua a mesma régua."""
from __future__ import annotations

import inspect

import scripts.output_judge as juiz


def test_a_nota_nao_passou_a_considerar_voz():
    """Se problemas_de_voz entrar em _nota_uma ou judge_answer, a série de
    7 dias muda de significado no meio e o antes/depois perde o sentido."""
    for fn in (juiz.judge_answer, juiz._nota_uma):
        assert "problemas_de_voz" not in inspect.getsource(fn), \
            f"{fn.__name__} passou a medir voz — a régua da nota mudou"


def test_o_juiz_conta_voz_em_algum_lugar():
    assert "problemas_de_voz" in inspect.getsource(juiz.main), \
        "o juiz não conta os defeitos de voz"


def test_contadores_de_voz_e_funcao_pura_testavel():
    linha = juiz.resumo_de_voz([
        "✅ Você jogou bem\n\nA conta que mais pesa: com 12bb é jam.",
        "✅ Você jogou bem\n\nCom 12bb é jam.",
    ])
    assert linha["analisadas"] == 2
    assert linha["com_titulo_fixo"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_juiz_nao_muda_de_regua.py -v`
Expected: FAIL — `AttributeError: module 'scripts.output_judge' has no attribute 'resumo_de_voz'`

- [ ] **Step 3: Write minimal implementation**

Acrescente a `scripts/output_judge.py`, antes de `main()`:

```python
def resumo_de_voz(textos: list[str]) -> dict:
    """Contadores de VOZ — separados da nota, de propósito.

    A nota 0-10 e seus critérios ficam intocados: mudar o texto e a régua
    no mesmo dia faz a média móvel de 7 dias mudar de significado no meio
    da série. Função pura para dar teste sem rede.
    """
    from app.bot.guarda_voz import bloco_pos_placar, problemas_de_voz

    com = {"titulo_fixo": 0, "bastidor": 0, "bloco_longo": 0,
           "autocorrecao": 0, "numero_repetido": 0}
    blocos: list[int] = []
    for t in textos:
        blocos.append(len(bloco_pos_placar(t)))
        for p in problemas_de_voz(t):
            if "título fixo" in p:
                com["titulo_fixo"] += 1
            elif "bastidor" in p:
                com["bastidor"] += 1
            elif "bloco pós-placar" in p:
                com["bloco_longo"] += 1
            elif "autocorreção" in p:
                com["autocorrecao"] += 1
            elif "repetido" in p:
                com["numero_repetido"] += 1
    medios = round(sum(blocos) / len(blocos)) if blocos else 0
    return {"analisadas": len(textos),
            "com_titulo_fixo": com["titulo_fixo"],
            "com_bastidor": com["bastidor"],
            "com_bloco_longo": com["bloco_longo"],
            "com_autocorrecao": com["autocorrecao"],
            "com_numero_repetido": com["numero_repetido"],
            "chars_pos_placar_medio": medios}
```

Em `main()`, depois do laço que monta `achados` e ANTES do envio ao admin:

```python
    # VOZ: contadores novos, fora da nota. Linha de base de 15/08 (403
    # análises): título fixo 25%, bastidor 23%, bloco pós-placar médio 740.
    voz = resumo_de_voz([str(p.get("a") or "") for p in pares
                         if not p.get("conversa")])
    repo.log_event(0, "output_judge", "voz_do_dia", voz)
    linha_voz = (
        f"\n🗣 VOZ (contadores, fora da nota) — {voz['analisadas']} análises: "
        f"título fixo {voz['com_titulo_fixo']} · bastidor {voz['com_bastidor']} "
        f"· bloco longo {voz['com_bloco_longo']} · pós-placar médio "
        f"{voz['chars_pos_placar_medio']} chars (base 15/08: 740)")
```

A lista `l` é montada logo abaixo; acrescente `linha_voz` a ela na linha
imediatamente anterior ao `notify_admin(settings.telegram_bot_token,
"\n".join(l))` (hoje `scripts/output_judge.py:302`):

```python
        l.append(linha_voz)
        notify_admin(settings.telegram_bot_token, "\n".join(l))
```

Cuidado com a ordem: `voz` e `linha_voz` são calculados **antes** do bloco
`if settings.telegram_bot_token:` que monta `l`, porque o
`repo.log_event("voz_do_dia", ...)` tem que acontecer mesmo quando não há
token para avisar o admin — o contador é o dado, o aviso é conveniência.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_juiz_nao_muda_de_regua.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Run the full suite**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/output_judge.py tests/test_juiz_nao_muda_de_regua.py
git commit -m "Juiz: contadores de voz, separados da nota

A régua da nota 0-10 não muda — trocar texto e régua no mesmo dia faz a
média móvel de 7 dias mudar de significado no meio da série."
```

---

### Task 6: `comparar_voz.py` — o lado a lado que mede "natural"

**Files:**
- Create: `scripts/comparar_voz.py`
- Test: `tests/test_comparar_voz.py`

**Interfaces:**
- Consumes: `coach()` de `app.agent.llm`, repositório Supabase
- Produces: arquivo markdown com pares ANTES/DEPOIS

**Este é o único mecanismo do plano que mede o que o dono pediu.** Todo o
resto detecta ausência de defeito; uma resposta pode passar em tudo e ainda
ler como robô.

O "antes" é de graça: já está gravado em `hand_analysis.summary`. O script
re-roda **a mesma mão, no mesmo modelo** (coluna `modelo`) com o código
atual, isolando o prompt como única variável.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_comparar_voz.py
"""O comparador isola o PROMPT como variável — nada mais."""
from __future__ import annotations

from scripts.comparar_voz import montar_markdown


def test_o_markdown_traz_os_dois_lados_e_o_modelo():
    md = montar_markdown([{
        "hand_id": "abc", "modelo": "claude-opus-4-8",
        "antes": "✅ Você jogou bem\n\nA conta que mais pesa: era jam.",
        "depois": "✅ Você jogou bem\n\nCom 12bb, jam é a única linha.",
    }])
    assert "ANTES" in md and "DEPOIS" in md
    assert "claude-opus-4-8" in md
    assert "A conta que mais pesa" in md


def test_par_sem_depois_e_marcado_e_nao_some():
    """Falha de geração tem que aparecer; sumir com o par faria a
    comparação parecer melhor do que é."""
    md = montar_markdown([{"hand_id": "x", "modelo": "m",
                           "antes": "texto", "depois": None}])
    assert "falhou" in md.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_comparar_voz.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.comparar_voz'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/comparar_voz.py
"""Compara a voz ANTES e DEPOIS da mudança de prompt, na mesma mão.

Todo guarda deste plano detecta AUSÊNCIA de defeito. Nenhum mede se o texto
soa como conversa — e foi isso que o dono pediu. Este script existe para a
leitura humana, que é a única que responde a pergunta.

O "antes" sai de graça de hand_analysis.summary. O "depois" re-roda a MESMA
mão no MESMO modelo (coluna `modelo`), então a única variável é o prompt.

Uso:  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python \\
        scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
"""
from __future__ import annotations

import argparse
import json


def montar_markdown(pares: list[dict]) -> str:
    linhas = ["# Voz do coach — antes × depois", ""]
    for i, p in enumerate(pares, 1):
        linhas += [f"## {i}. mão `{p['hand_id']}` · modelo `{p['modelo']}`",
                   "", "### ANTES", "", p["antes"] or "_(vazio)_", ""]
        if p.get("depois"):
            linhas += ["### DEPOIS", "", p["depois"], ""]
        else:
            linhas += ["### DEPOIS", "", "_(a geração falhou)_", ""]
        linhas.append("---")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--saida", default="/tmp/voz.md")
    args = ap.parse_args()

    from app.agent.llm import coach
    from app.db import get_repository

    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 1

    rows = (repo.client.table("hand_analysis")
            .select("hand_id,summary,modelo")
            .not_.is_("summary", "null")
            .order("created_at", desc=True).limit(args.n * 3)
            .execute().data) or []

    pares: list[dict] = []
    for r in rows:
        if len(pares) >= args.n:
            break
        if not r.get("hand_id") or str(r.get("summary", "")).startswith("[Follow-up]"):
            continue
        mao = (repo.client.table("hands").select("canonical")
               .eq("id", r["hand_id"]).limit(1).execute().data) or []
        if not mao:
            continue
        structured = {"spots": [], "canonical": mao[0]["canonical"]}
        try:
            novo = coach(structured, None, lang="pt", model=r.get("modelo"))
        except Exception as exc:
            print(f"falhou em {r['hand_id']}: {exc}")
            novo = None
        pares.append({"hand_id": r["hand_id"], "modelo": r.get("modelo") or "?",
                      "antes": r["summary"], "depois": novo})

    with open(args.saida, "w", encoding="utf-8") as fh:
        fh.write(montar_markdown(pares))
    print(f"{len(pares)} pares em {args.saida}")
    print(json.dumps({"pares": len(pares)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_comparar_voz.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Run the full suite**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/comparar_voz.py tests/test_comparar_voz.py
git commit -m "comparar_voz: o lado a lado que mede 'natural'

O antes sai de graça do banco; o depois re-roda a mesma mão no mesmo
modelo, isolando o prompt como única variável."
```

---

### Task 7: Linha de base e verificação final

**Files:**
- Modify: `backend/docs/superpowers/specs/2026-08-15-voz-do-coach-design.md` (seção de resultado)
- Modify: `OPERATIONS.md` (raiz do repo) — "Onde paramos"

**Interfaces:**
- Consumes: tudo das Tasks 1-6
- Produces: os números do "antes" e a instrução de deploy

- [ ] **Step 1: Rodar o guarda sobre o histórico (linha de base)**

```bash
cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python - <<'PY'
from app.db import get_repository
from scripts.output_judge import resumo_de_voz
repo = get_repository()
rows = (repo.client.table("hand_analysis").select("summary")
        .not_.is_("summary","null").order("created_at", desc=True)
        .limit(400).execute().data)
print(resumo_de_voz([r["summary"] for r in rows]))
PY
```

Anote o resultado. Os números esperados, do levantamento de 15/08:
título fixo ~25%, bastidor ~23%, pós-placar médio ~740 chars.

- [ ] **Step 2: Rodar o comparador**

```bash
cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python \
  scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
```

- [ ] **Step 3: Entregar o lado a lado ao dono**

O arquivo `/tmp/voz.md` vai para o Leo. **A decisão de mergear é dele, com
o texto na frente.** Nenhum contador substitui essa leitura.

- [ ] **Step 4: Rodar a suíte inteira uma última vez**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS — 971 anteriores + ~34 novos

- [ ] **Step 5: Atualizar a documentação**

Na spec, acrescente uma seção "Resultado" com os números do Step 1 (antes)
e o que o comparador mostrou. No `OPERATIONS.md`, em "Onde paramos",
acrescente o item:

```markdown
5. **Voz do coach**: implementada e testada, NÃO deployada. O merge espera
   a leitura do juiz de 16/08 (item 3) para não misturar troca de modelo
   com troca de prompt na mesma nota. Lado a lado em `/tmp/voz.md`.
```

- [ ] **Step 6: Commit**

```bash
git add backend/docs/superpowers/specs/2026-08-15-voz-do-coach-design.md OPERATIONS.md
git commit -m "Voz do coach: linha de base medida e handoff atualizado"
```

---

## Orquestração de modelos e custo

Pedido explícito do dono. A régua: **julgamento pede modelo forte; trabalho
determinístico com spec fechada pede modelo barato.** O custo de errar é
assimétrico — o prompt fala com todos os alunos, o guarda tem teste que
cobra.

| Task | Modelo do implementador | Modelo do revisor | Por quê |
|---|---|---|---|
| 1 — medições puras | `sonnet` | `sonnet` | regex e contagem, spec fechada, teste cobra |
| 2 — limpeza | `sonnet` | `opus` | sutil: estragar português é o risco, e revisar é mais barato que consertar em produção |
| 3 — integração | `sonnet` | `sonnet` | dois blocos try/except em ponto conhecido |
| 4 — prompt | **`opus`** | **`opus`** | redação com julgamento; erro aqui fala com todos os alunos de uma vez |
| 5 — juiz | `haiku` | `sonnet` | função pura de contagem + duas linhas de string |
| 6 — comparador | `sonnet` | `sonnet` | script one-shot, testes cobrem o formato |
| 7 — verificação | `sonnet` | dono | a leitura final é humana, por definição |

**Custo estimado:** as Tasks 1-3, 5 e 6 somam ~600 linhas de código e teste
em modelo médio/barato. A Task 4 é o gasto concentrado, e é a que justifica
`opus`. A execução do `comparar_voz.py` custa 8 análises reais (~US$0,10-0,40
conforme o modelo gravado na coluna `modelo`).

---

## Ordem e paralelismo

Tasks **1 → 2 → 3** são sequenciais (2 usa constantes de 1; 3 usa as duas).

Tasks **4, 5 e 6** dependem só da Task 1 e são independentes entre si —
podem rodar em paralelo depois que 1 fechar. A Task 5 importa
`problemas_de_voz` e a 6 não importa nada do guarda.

Task **7** é a última, sempre.

---

## Riscos e o que fazer

| risco | sinal | o que fazer |
|---|---|---|
| prompt novo se contradiz | `test_prompt_nao_briga_consigo` falha | conserte o prompt, nunca o teste |
| guarda estraga português | `test_titulo_nao_sai_quando...` falha | a guarda `_FRAGMENTO` está frouxa |
| resposta fica seca | o dono lê `/tmp/voz.md` e não gosta | calibrar os tetos (800 chars, 2 parênteses) antes de mergear |
| deploy antes da hora | cron pega o commit em 2 min | **não empurrar para a branch antes da liberação** — o auto_update roda a cada 2 min |

**Atenção operacional:** o `deploy/auto_update.sh` roda a cada 2 minutos na
branch `claude/poker-analysis-telegram-bot-mfuyhf` e deploya todo commit
novo que passe nos testes. "Commitar mas não deployar" **exige** trabalhar
em branch separada ou segurar o push. Este é o único jeito de honrar a §6
da spec.
