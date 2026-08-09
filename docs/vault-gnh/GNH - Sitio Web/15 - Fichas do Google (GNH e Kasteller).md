---
titulo: Fichas do Google Business — GNH e Kasteller
tags: [gnh, kasteller, google-business, seo-local, mapas]
atualizado: 2026-08-09
---

# Fichas do Google Business — GNH e Kasteller

[[06 - SEO e GEO]] · [[05 - Analytics e rastreamento]] · [[Kasteller - Sitio Web/03 - SEO, GEO e analytics]]

Conteúdo pronto para colar em `business.google.com`. **Os textos estão em espanhol**
porque é o idioma da ficha; os comentários em volta são para você.

> [!warning] O que eu não consigo conferir daqui
> O sandbox bloqueia todos os domínios do Google. Não sei se a ficha da GNH está
> **reivindicada** (com painel de dono) ou apenas existe como ponto no mapa, nem se
> já tem horário e fotos. Confira no painel antes de colar — se algum campo já
> estiver melhor do que o que está aqui, mantenha o seu.

---

## Antes de tudo: o link do site leva UTM

No campo **Sitio web** de cada ficha, use o endereço **com o parâmetro**:

```
https://gnhorizons.com/?utm_source=google-business
https://kasteller.com.py/?utm_source=google-business
```

Não é firula. O Google Maps e a Busca mandam **o mesmo referrer**
(`https://www.google.com/`) — sem o parâmetro, é impossível saber se a visita veio
da ficha ou de uma busca comum. Com ele, a origem aparece separada no analytics
(o `utm_source` sempre ganha do referrer). Veja *Como medir* no fim.

---

# 1 · GNH — Generando Nuevos Horizontes

## Dados básicos

| Campo | Valor |
|---|---|
| **Nombre** | `GNH — Generando Nuevos Horizontes` |
| **Dirección** | `Av. República del Perú km 7, Ciudad del Este 100101, Alto Paraná` |
| **Teléfono** | `+595 995 360060` |
| **Sitio web** | `https://gnhorizons.com/?utm_source=google-business` |
| **Área de servicio** | Paraguay (todo el país) e Brasil — região de fronteira |
| **Idiomas** | Español, Portugués |

> [!tip] A segunda loja é uma ficha separada
> Ñemby (`Acceso Sur, Ñemby 111210`) precisa da **própria** ficha, não é endereço
> secundário. Duas fichas na mesma conta, ligadas como grupo de localizações.
> O texto abaixo serve para as duas, trocando só o endereço.

## Categorias

O **nome da categoria é taxonomia do Google**, não é o nosso posicionamento — digite
as primeiras letras e escolha a mais próxima da lista, o texto exato varia por país.

- **Principal:** `Proveedor de equipos de construcción`
  *(é o que as pessoas procuram: plataforma, grúa, montacargas — puxa mais busca que "distribuidor")*
- **Secundárias:** `Distribuidor` · `Mayorista` · `Tienda de materiales de construcción` ·
  `Empresa de importación y exportación` · `Servicio de transporte de carga`

## Descripción (≤750 caracteres)

```
GNH — Generando Nuevos Horizontes es un grupo empresarial de comercio internacional con base en Ciudad del Este. Conectamos marcas globales con obras y empresas de Paraguay y Brasil en cinco frentes: equipos para construcción e industria, aditivos químicos, morteros y cemento, fletes y representación de marcas.

En nuestro show room encontrás plataformas de elevación, grúas araña, montacargas, mini excavadoras, bombas y centrales de concreto y grupos electrógenos, con ficha técnica y respaldo local. Somos distribuidores exclusivos de Camargo Química en Paraguay.

Atención en español y portugués. Cotizá por WhatsApp: +595 995 360060.
```

> [!important] "Importadora" não entra
> A regra de posicionamento vale aqui: GNH é **grupo empresarial de comercio
> internacional**, e importação é uma das cinco frentes — não o rótulo da empresa.
> A categoria do Google é campo técnico e pode conter a palavra; o texto, não.

## Productos y servicios

Cadastre como **Servicios** (aparecem na ficha e alimentam a busca):

```
Plataformas de elevación
Plataformas tijera autopropulsadas
Plataformas articuladas y telescópicas
Grúas araña (spider crane) de 1,5 a 16 t
Montacargas y apiladores
Mini excavadoras y movimiento de suelo
Bombas y centrales de concreto
Grupos electrógenos
Aditivos químicos para concreto — Camargo Química
Morteros industrializados Hormigomix
Revoque proyectado Intonaco
Cementos de alto desempeño
Fletes y logística — FletePar
Pisos y revestimientos — Kasteller
```

## Atributos para marcar

`Se identifica como empresa de propiedad latina` (se aplicar) · `Estacionamiento gratuito` ·
`Acceso para silla de ruedas` (se houver) · `Atención en el local` · `Pedidos por WhatsApp` ·
`Idiomas: español, portugués`

## Fotos (a ficha com foto recebe muito mais clique)

- [ ] **Logo** — quadrado, ≥720px: `assets/nuevo/img/logo-oficial.png`
- [ ] **Capa** — fachada ou show room, horizontal
- [ ] Fachada da loja (a que ajuda o cliente a reconhecer da rua)
- [ ] Interior / show room
- [ ] Equipe em atendimento
- [ ] 5 a 8 fotos de produto: plataforma, grúa araña, montacargas, gerador 38 kVA
- [ ] O vídeo do gerador (já está em `assets/nuevo/video/generador.mp4`)

---

# 2 · Kasteller Revestimientos

> [!danger] Leia antes de criar
> A Kasteller fica no **mesmo endereço** da GNH e da Transcamilo. O Google aceita
> mais de uma empresa no mesmo ponto quando são negócios realmente distintos —
> marca própria, telefone próprio, atendimento próprio — mas é o caso clássico em
> que a verificação é recusada ou as fichas se fundem.
>
> Para reduzir o risco: telefone **diferente** da GNH (o WhatsApp da Kasteller já é
> outro), site próprio (`kasteller.com.py`), categoria principal diferente, e no
> endereço identifique o local — algo como `Av. República del Perú km 7 — Showroom
> Kasteller`. Se possível, foto da fachada onde apareça a placa da Kasteller: é o
> que o revisor do Google procura.

## Dados básicos

| Campo | Valor |
|---|---|
| **Nombre** | `Kasteller Revestimientos` |
| **Dirección** | `Av. República del Perú km 7 — Showroom Kasteller, Ciudad del Este 100101` |
| **Coordenadas** | `-25.494533, -54.661564` *(ajuste o alfinete à mão se cair no vizinho)* |
| **Teléfono** | `+595 985 869600` |
| **Sitio web** | `https://kasteller.com.py/?utm_source=google-business` |
| **Área de servicio** | Alto Paraná e Paraguay; atendimento também em português (Foz do Iguaçu / oeste do Paraná) |

## Categorias

- **Principal:** `Tienda de azulejos` *(ou `Tienda de baldosas`, conforme aparecer)*
- **Secundárias:** `Tienda de materiales de construcción` · `Tienda de artículos para el hogar` ·
  `Proveedor de piedra natural` · `Sala de exposición`

## Descripción (≤750 caracteres)

```
Kasteller Revestimientos es el showroom de pisos y revestimientos de alto padrón de Ciudad del Este. Más de 1.000 productos de seis marcas brasileñas —Portinari, Ceusa, Castelli, Roca, Incepa y Castelatto—: porcelanatos de gran formato, mármoles, piedras naturales y revestimientos especiales.

Atendemos a arquitectos, constructoras y clientes finales, en español y portugués, con asesoramiento de especificación y cálculo de cantidades. Consultá disponibilidad y precios por WhatsApp: +595 985 869600.

Kasteller forma parte del grupo GNH — Generando Nuevos Horizontes.
```

## Productos y servicios

```
Porcelanato de gran formato
Porcelanato pulido, natural y satinado
Porcelanato símil madera
Porcelanato símil mármol
Piedras naturales y mármoles
Revestimientos especiales para fachada
Revestimientos 3D — Castelatto
Pisos para alto tránsito comercial
Asesoramiento de especificación para arquitectos
Cálculo de cantidades por ambiente
```

Marcas para o campo de marcas: `Portinari` · `Ceusa` · `Castelli` · `Roca` · `Incepa` · `Castelatto`

## Fotos

- [ ] **Logo:** `assets/kasteller2/img/kasteller-negro.png`
- [ ] **Capa:** show room, horizontal
- [ ] Fachada **com a placa Kasteller visível** (é a foto que sustenta a verificação)
- [ ] 6 a 10 fotos de ambientes prontos — as mesmas que já usamos no site
- [ ] Foto dos expositores por marca

---

# 3 · Horários — o campo que falta

**Não tenho os horários.** Tentei buscar da ficha da Transcamilo e o Google está
bloqueado aqui. Sem horário a ficha perde posição em "abierto ahora", que é filtro
que muita gente usa no celular.

Me passe os horários e eu registro no vault e no site (as duas fichas + o rodapé +
o JSON-LD `openingHours`, que hoje não existe em nenhum dos dois). Se forem os
mesmos da Transcamilo, é só confirmar — o palpite abaixo é do padrão do comércio
de CDE e **não deve ser usado sem checar**:

```
Lunes a viernes   07:30 – 17:30   (¿corte al mediodía?)
Sábado            07:30 – 12:00
Domingo           Cerrado
```

---

# 4 · Como medir se a ficha traz gente

A partir de agora todo evento carrega a coluna `ref` com a origem da sessão
([[14 - Acessibilidade e H1]] é sobre outra coisa; o rastreio de origem entrou junto
nesta leva). Valores normalizados: `google`, `google-maps`, `google-business`,
`instagram`, `facebook`, `whatsapp`, `chatgpt`, `perplexity`, `directo`, `interno`,
ou o domínio cru de quem não está na lista.

```sql
-- de onde vêm as visitas, e quais convertem
select coalesce(ref,'(antes do rastreio)') origem,
       count(distinct session_id) sesiones,
       count(*) filter (where type in ('whatsapp','lead','whatsapp-directo')) contactos
from events                     -- ou kasteller_events
where created_at > now() - interval '30 days'
group by 1 order by sesiones desc;
```

> [!note] Por que `google-business` e não `google-maps`
> O `google-maps` só aparece quando o referrer é literalmente `maps.google.com`.
> O clique no site **de dentro da ficha** chega como `google.com` comum — igual a
> uma busca. É o `?utm_source=google-business` no campo *Sitio web* que separa os
> dois. Sem ele, a resposta de "a ficha funciona?" continua sendo um chute.

---

**Ver também:** [[06 - SEO e GEO]] · [[05 - Analytics e rastreamento]] · [[10 - Pendencias e roadmap]]
