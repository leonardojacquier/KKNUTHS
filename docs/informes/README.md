# Informes técnicos

PDF vetorial A4, gerado de dados — não de imagem colada.

```bash
cd docs/informes
python3 build-informe-cielo-azul.py   # gera o HTML (logos embutidas em base64)
node render-pdf.cjs                   # renderiza o PDF
```

O HTML intermediário não é versionado: pesa 2,6 MB por causa das logos em base64
e é reproduzível pelo script em um segundo.

## Por que os gráficos foram redesenhados

O registro original traz **dois eixos Y no mesmo plano** — resistência em MPa à
esquerda, água e assentamento à direita. É o erro de gráfico mais comum: o
alinhamento entre as duas escalas é arbitrário, então o desenho sugere uma
correlação que o ensaio não mediu. Aqui cada grandeza tem o seu próprio plano.

A dupla de cores das séries passou pelo validador da skill `dataviz` (banda de
luminosidade, piso de croma, separação sob daltonismo protan/deutan/tritan e
contraste contra o fundo). O laranja é o da marca, escurecido até passar no
contraste; o azul é o slot 1 da paleta de referência.

## O que foi calculado, e o que veio do registro

Do registro: as seis medições e os três percentuais de resistência (+12,0 %,
+17,8 %, +26,4 %) — conferidos, batem.

Calculado a partir dessas mesmas medições: a redução de água (−17 L/m³, −6,8 %) e
as perdas de assentamento (−20,0 % contra −12,8 %). Nenhum dado externo entrou.

> [!important] A perda de abatimento é desfavorável ao PN797 e está no documento
> O produto perde 40 mm em 15 min contra 25 mm da referência. Omitir isso faria o
> informe ruir na primeira pergunta de um engenheiro de planta. Está na página 4,
> com o contexto de que é parâmetro de ajuste, não defeito.

O gráfico de origem rotula o assentamento em **cm** com valores de 195 e 200 — que
em centímetros seria fisicamente impossível. Tratado como **mm**, com nota de rodapé
na página 2.
