#!/usr/bin/env python3
"""
Enriquece buscador/productos.json com AMBIENTES (faceta usos) e SINÔNIMOS (tags).

Idempotente: pode rodar quantas vezes quiser — só acrescenta o que falta.
Rodar depois de todo re-scrape:
    python3 enriquecer_ambientes.py ../../assets/kasteller2/buscador/productos.json

Regras de ambiente (conservadoras, derivadas dos atributos técnicos):
- exterior/terraza: acabado externo, tag hard/grip, ou uso externo declarado
- piscina: nome indica borda/atérmico/fulget, ou pedra Castelatto
- fachada: apto a exterior + pared
- cochera: piso + resistência (hard/externo)
- dormitorio: piso interno (acabado não-externo)
- cocina/baño/living: interiores de uso geral (pared sempre serve;
  para piso a triagem fina — ex. polido molhado — é conversa de showroom)
"""
import json, sys, unicodedata

RUTA = sys.argv[1] if len(sys.argv) > 1 else 'productos.json'

def sin_acentos(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()

# sinônimos por valor existente (ES ↔ PT ↔ EN) — entram nas tags, viram buscáveis
SINONIMOS = {
    # visual
    'mármol':   ['marmol', 'marmore', 'marble', 'calacatta'],
    'madera':   ['madeira', 'wood', 'amadeirado'],
    'piedra':   ['pedra', 'stone'],
    'cemento':  ['cimento', 'concreto', 'concrete', 'industrial'],
    'ladrillo': ['tijolo', 'tijolinho', 'brick'],
    'metal':    ['metalico', 'metalizado'],
    # acabado
    'polido':    ['pulido', 'brillante', 'brilhante', 'lustroso'],
    'mate':      ['fosco', 'opaco', 'matte'],
    'acetinado': ['satinado', 'soft', 'semibrilho'],
    'externo':   ['antideslizante', 'antiderrapante', 'grip', 'antislip'],
    # cores (tags que o tagger já gera)
    'gris':      ['cinza', 'grey', 'gray'],
    'negro':     ['preto', 'black'],
    'blanco':    ['branco', 'white'],
    'beige':     ['bege', 'arena'],
    'marron':    ['marrom', 'brown'],
    'crema':     ['creme', 'cream'],
    'terracota': ['terracotta', 'cotto'],
    'azul':      ['blue'],
    'verde':     ['green'],
    # tipo / uso base
    'porcelanato':  ['porcellanato', 'ceramica'],
    'piso':         ['suelo', 'chao', 'pavimento'],
    'pared':        ['parede', 'muro', 'revestimento'],
    'gran formato': ['formato grande', 'lastra', 'placa grande', 'big slab'],
}

# sinônimos dos ambientes novos
SIN_AMBIENTE = {
    'cocina':     ['cozinha', 'kitchen', 'mesada'],
    'baño':       ['banheiro', 'bano', 'banho', 'bathroom', 'lavabo', 'sanitario'],
    'living':     ['sala', 'estar', 'salon', 'comedor', 'sala de estar'],
    'dormitorio': ['quarto', 'habitacion', 'cuarto', 'bedroom', 'suite'],
    'terraza':    ['terraço', 'terraco', 'varanda', 'balcon', 'sacada', 'quincho',
                   'churrasquera', 'churrasqueira', 'area gourmet', 'patio'],
    'exterior':   ['externo', 'outdoor', 'area externa', 'jardin', 'vereda'],
    'piscina':    ['pileta', 'borda', 'borde de piscina', 'solarium'],
    'fachada':    ['frente', 'fachada ventilada', 'revestimiento exterior'],
    'cochera':    ['garaje', 'garagem', 'garage', 'alto transito'],
}

with open(RUTA, encoding='utf-8') as f:
    raw = json.load(f)
productos = raw['productos'] if isinstance(raw, dict) else raw

def agrega(lista, *valores):
    for v in valores:
        if v and v not in lista:
            lista.append(v)

for p in productos:
    usos, tags = p.setdefault('usos', []), p.setdefault('tags', [])
    idn = sin_acentos(p.get('id', '') + ' ' + p.get('nombre', '') + ' ' + p.get('linea', ''))
    acab, look = p.get('acabado', ''), p.get('look', '')
    piso, pared = 'piso' in usos, 'pared' in usos

    apto_ext = ('externo' in usos or acab == 'externo' or 'hard' in tags
                or any(k in idn for k in ('grip', ' ext', '-ext', 'out ')))
    es_piscina = (any(k in idn for k in ('borda', 'atermic', 'fulget', 'piscina', 'pool'))
                  or (p.get('marca') == 'Castelatto' and look == 'piedra'))

    # --- ambientes na faceta usos ---
    agrega(usos, 'cocina', 'baño')
    if piso:
        agrega(usos, 'living')
        if acab != 'externo':
            agrega(usos, 'dormitorio')
    if apto_ext:
        agrega(usos, 'exterior')
        if piso:
            agrega(usos, 'terraza', 'cochera')
        if pared:
            agrega(usos, 'fachada')
    if es_piscina:
        agrega(usos, 'piscina', 'exterior')

    # --- sinônimos nas tags (buscáveis, não viram chip) ---
    base = set(tags) | set(usos) | {acab, look, p.get('tipo', '')}
    for clave, sines in list(SINONIMOS.items()) + list(SIN_AMBIENTE.items()):
        if clave in base:
            agrega(tags, *sines)

with open(RUTA, 'w', encoding='utf-8') as f:
    json.dump(raw, f, ensure_ascii=False, separators=(',', ':'))

from collections import Counter
c = Counter(u for p in productos for u in p['usos'])
print('usos/ambientes:', dict(c))
print('produtos:', len(productos), '| tamanho:', len(json.dumps(raw, ensure_ascii=False)) // 1024, 'KB')
