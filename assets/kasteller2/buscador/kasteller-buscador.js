/* =====================================================================
   KASTELLER — Buscador inteligente de productos
   - filtro instantâneo enquanto digita (sem páginas, sem recarga)
   - insensível a acentos/maiúsculas; múltiplos termos = E (AND)
   - sugestões de tags agrupadas por faceta; clique vira chip de filtro
   - integra com o analytics do site (KT) se existir, em silêncio se não
   Dados: <script type="application/json" id="kb-data"> OU buscador/productos.json
   ===================================================================== */
(function () {
  'use strict';

  var root = document.getElementById('buscador');
  if (!root) return;

  var FACETAS = [
    ['marca',   'Marca'],
    ['tipo',    'Tipo'],
    ['look',    'Visual'],
    ['acabado', 'Acabado'],
    ['formato', 'Formato'],
    ['usos',    'Uso / Ambiente']
  ];
  var WA = root.dataset.whatsapp || 'https://wa.me/595985869600';
  var LOTE = 24; // resultados por leva (botão "ver más")

  /* ---------- utilidades ---------- */
  function norm(s) {
    return String(s || '').toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9x ]+/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function track(tipo, detalle) {
    try { if (typeof window.KT === 'function') window.KT(tipo, detalle); } catch (e) {}
  }

  /* ---------- carga de dados ---------- */
  function carga(cb) {
    var inline = document.getElementById('kb-data');
    if (inline) { try { return cb(JSON.parse(inline.textContent)); } catch (e) {} }
    fetch('buscador/productos.json')
      .then(function (r) { return r.json(); })
      .then(cb)
      .catch(function () { cb({ productos: [] }); });
  }

  /* o catálogo pesa ~1 MB: só baixa quando a seção se aproxima (600px antes)
     ou no primeiro toque no campo — o que vier primeiro. Sem isso ele entrava
     na carga inicial da página inteira, mesmo pra quem nunca rola até aqui. */
  function cuandoHagaFalta(cb) {
    var hecho = false;
    var go = function () { if (!hecho) { hecho = true; carga(cb); } };
    if (!('IntersectionObserver' in window)) return go();
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { io.disconnect(); go(); } });
    }, { rootMargin: '600px 0px' });
    io.observe(root);
    root.addEventListener('focusin', go, { once: true });
    if (location.hash === '#buscador') go();
  }

  cuandoHagaFalta(function (data) {
    var productos = (data.productos || []).map(function (pr, i) {
      var hay = [pr.nombre, pr.marca, pr.linea, pr.tipo, pr.look, pr.acabado, pr.formato]
        .concat(pr.tags || [], pr.usos || []).map(norm).join(' ');
      return { d: pr, hay: hay, i: i };
    });

    /* índice de valores por faceta (para as sugestões) */
    var facetVals = {};
    FACETAS.forEach(function (f) { facetVals[f[0]] = {}; });
    productos.forEach(function (pz) {
      FACETAS.forEach(function (f) {
        var v = pz.d[f[0]];
        (Array.isArray(v) ? v : [v]).forEach(function (val) {
          if (val) facetVals[f[0]][val] = (facetVals[f[0]][val] || 0) + 1;
        });
      });
    });

    /* ---------- estado ---------- */
    var chips = [];        // [{facet, valor}]
    var query = '';
    var visibles = LOTE;

    /* ---------- DOM ---------- */
    var $in    = root.querySelector('.kb__input');
    var $sugs  = root.querySelector('.kb__sugs');
    var $chips = root.querySelector('.kb__chips');
    var $grid  = root.querySelector('.kb__grid');
    var $count = root.querySelector('.kb__count');
    var $empty = root.querySelector('.kb__empty');
    var $more  = root.querySelector('.kb__more');

    /* ---------- filtro ---------- */
    function filtra() {
      var termos = norm(query).split(' ').filter(Boolean);
      return productos.filter(function (pz) {
        for (var c = 0; c < chips.length; c++) {
          var v = pz.d[chips[c].facet];
          var lista = Array.isArray(v) ? v : [v];
          if (lista.map(norm).indexOf(norm(chips[c].valor)) === -1) return false;
        }
        for (var t = 0; t < termos.length; t++) {
          if (pz.hay.indexOf(termos[t]) === -1) return false;
        }
        return true;
      }).sort(function (a, b) {
        /* ranking simples: nome que começa com o termo primeiro */
        if (termos.length) {
          var na = norm(a.d.nombre).indexOf(termos[0]) === 0 ? 0 : 1;
          var nb = norm(b.d.nombre).indexOf(termos[0]) === 0 ? 0 : 1;
          if (na !== nb) return na - nb;
        }
        return a.i - b.i;
      });
    }

    /* ---------- render ---------- */
    function cardHTML(pr) {
      var ph = pr.img
        ? '<div class="kb__ph"><img loading="lazy" src="' + pr.img + '" alt="" ' +
          'onload="this.classList.add(\'ok\')" onerror="this.parentNode.className=\'kb__ph kb__ph--txt\';this.outerHTML=\'<span>' + pr.nombre + '</span>\'">' +
          '<span class="kb__marca">' + pr.marca + '</span></div>'
        : '<div class="kb__ph kb__ph--txt"><span>' + pr.nombre + '</span>' +
          '<span class="kb__marca">' + pr.marca + '</span></div>';
      var meta = [pr.tipo, pr.formato !== 'VARIOS' ? pr.formato : null, pr.acabado]
        .filter(Boolean).join(' · ');
      return '<a class="kb__card" href="' + (pr.url || '#') + '" target="_blank" rel="noopener" data-id="' + pr.id + '">' +
        ph + '<div class="kb__info"><div class="kb__nombre">' + pr.nombre + '</div>' +
        '<div class="kb__meta">' + meta + '</div></div></a>';
    }

    function render() {
      var res = filtra();
      $grid.innerHTML = res.slice(0, visibles).map(function (pz, k) {
        return cardHTML(pz.d).replace('class="kb__card"',
          'class="kb__card" style="animation-delay:' + Math.min(k * 35, 400) + 'ms"');
      }).join('');
      $count.textContent = res.length + ' producto' + (res.length === 1 ? '' : 's');
      $empty.classList.toggle('show', res.length === 0);
      $more.hidden = res.length <= visibles;
      if (res.length === 0 && (query || chips.length)) {
        track('busqueda-vacia', query || chips.map(function (c) { return c.valor; }).join(','));
      }
      renderChips();
    }

    function renderChips() {
      var html = chips.map(function (c, i) {
        var label = FACETAS.filter(function (f) { return f[0] === c.facet; })[0][1];
        return '<button class="kb__chip" data-i="' + i + '"><small>' + label + '</small>' + c.valor + '</button>';
      }).join('');
      if (chips.length) html += '<button class="kb__clear">limpiar</button>';
      $chips.innerHTML = html;
    }

    /* ---------- sugestões enquanto digita ---------- */
    function sugiere() {
      var q = norm(query);
      if (!q) { $sugs.classList.remove('open'); return; }
      var html = '';
      FACETAS.forEach(function (f) {
        var vals = Object.keys(facetVals[f[0]]).filter(function (v) {
          return norm(v).indexOf(q) !== -1 &&
            !chips.some(function (c) { return c.facet === f[0] && c.valor === v; });
        }).slice(0, 6);
        if (vals.length) {
          html += '<div class="kb__sug-group">' + f[1] + '</div>' +
            vals.map(function (v) {
              return '<span class="kb__sug" data-facet="' + f[0] + '" data-valor="' + v + '">' +
                '<b>' + v + '</b> (' + facetVals[f[0]][v] + ')</span>';
            }).join('');
        }
      });
      $sugs.innerHTML = html;
      $sugs.classList.toggle('open', !!html);
    }

    /* ---------- eventos ---------- */
    var deb, trackDeb;
    $in.addEventListener('input', function () {
      query = $in.value; visibles = LOTE;
      clearTimeout(deb);
      deb = setTimeout(function () { render(); sugiere(); }, 90);
      clearTimeout(trackDeb);
      trackDeb = setTimeout(function () { if (norm(query)) track('busqueda', query); }, 1200);
    });
    $sugs.addEventListener('click', function (e) {
      var s = e.target.closest('.kb__sug');
      if (!s) return;
      chips.push({ facet: s.dataset.facet, valor: s.dataset.valor });
      query = ''; $in.value = ''; visibles = LOTE;
      $sugs.classList.remove('open');
      track('filtro', s.dataset.facet + ':' + s.dataset.valor);
      render(); $in.focus();
    });
    $chips.addEventListener('click', function (e) {
      var chip = e.target.closest('.kb__chip');
      if (chip) { chips.splice(+chip.dataset.i, 1); visibles = LOTE; render(); return; }
      if (e.target.closest('.kb__clear')) { chips = []; visibles = LOTE; render(); }
    });
    $more.addEventListener('click', function () { visibles += LOTE; render(); });
    $grid.addEventListener('click', function (e) {
      var card = e.target.closest('.kb__card');
      if (card) track('producto', card.dataset.id);
    });
    document.addEventListener('click', function (e) {
      if (!root.querySelector('.kb__barwrap').contains(e.target)) $sugs.classList.remove('open');
    });

    /* WhatsApp do estado vazio */
    var wa = $empty.querySelector('a');
    if (wa) wa.href = WA + '?text=' + encodeURIComponent('Hola Kasteller, busco: ');

    render();
  });
})();
