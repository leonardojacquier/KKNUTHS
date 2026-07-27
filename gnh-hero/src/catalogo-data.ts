/* ============================================================
   CATÁLOGO — fonte única de verdade (site + gerador de páginas estáticas).
   Extraído de ventas.ts para que o build possa emitir uma página HTML por
   produto sem duplicar dados. Editar produto/spec = editar SÓ este arquivo.
   ============================================================ */

export interface Product { name: string; brand?: string; img?: string; note?: string; tags?: string[]; specs?: { h: string[]; r: string[][] } }
export interface SubGroup { title: string; products: Product[] }
export interface Category {
  id: string
  title: string
  icon: string
  blurb: string                 // texto curto no painel do deck
  products?: Product[]          // categoria simples
  groups?: SubGroup[]           // categoria com subcategorias (ex.: Equipos)
}

export const CATALOG: Category[] = [
  {
    id: 'equipos', title: 'Equipos', icon: 'gear',
    blurb: 'Reglas láser, bombas de concreto, allanadoras, grúas, generadores y más.',
    groups: [
      {
        title: 'Construcción',
        products: [
          { name: 'Regla Láser Vibratoria WS940', img: '../img/prod/ws940.png', note: 'Nivelación láser de pisos de concreto de alta precisión.',
            tags: ['nivelacion', 'nivelar', 'piso', 'pavimento', 'contrapiso', 'laser', 'hormigon', 'llana', 'acabado', 'losa', 'galpon'] },
          { name: 'Bomba Transportadora de Concreto', img: '../img/prod/bomba-cemento.png', note: 'Bombeo y transporte de concreto con caudal estable y operación continua.',
            tags: ['bombeo', 'bombear', 'hormigon', 'transporte', 'distancia', 'altura', 'losa', 'llenado', 'colado', 'hormigonado'] },
          { name: 'Allanadora de Concreto 1 m', img: '../img/prod/allanadora.png', note: 'Alisado y pulido de pisos de concreto. Ancho de trabajo de 1 metro.',
            tags: ['alisado', 'alisar', 'pulido', 'pulir', 'acabado', 'piso', 'helicoptero', 'flotadora', 'fratasadora', 'terminacion', 'losa'] },
          { name: 'Cortadora de Piso', img: '../img/prod/cortadora.png', note: 'Corte de juntas en concreto y asfalto con disco diamantado.',
            tags: ['corte', 'cortar', 'junta', 'juntas', 'disco', 'diamantado', 'asfalto', 'pavimento', 'sierra', 'aserrado'] },
          { name: 'Máquina de Marcado Vial', img: '../img/prod/marcado.png', note: 'Marcación de pavimentos y viales con pintura de alto rendimiento.',
            tags: ['pintura', 'senalizacion', 'demarcacion', 'carretera', 'vial', 'estacionamiento', 'lineas', 'pintar calle'] },
          { name: 'Central de Concreto JBTS20', img: '../img/prod/central-concreto.png', note: 'Mezcladora y bomba de concreto sobre remolque. Equipada con motor Cummins, para producción y bombeo continuo en obra.',
            tags: ['planta', 'mezcla', 'mezcladora', 'bombeo', 'produccion', 'hormigon', 'obra', 'cummins', 'hormigonera', 'betonera'] },
          { name: 'Proyectora de Revoque', brand: 'GNH', img: '../img/prod/gnh-proyectora.png', note: 'Máquina de proyección de revoque — nuevo lanzamiento GNH. Proyecta mortero directamente sobre la pared con caudal continuo: el complemento ideal del Mortero de Proyección Hormigomix.',
            tags: ['proyectora', 'proyeccion', 'revoque', 'revocar', 'revoco', 'mortero', 'pared', 'maquina', 'enlucido', 'yeso', 'salpicado'] },
        ],
      },
      {
        title: 'Movimentación',
        products: [
          { name: 'Grúa Araña', brand: 'GNH', img: '../img/prod/grua-arana.png', note: 'Grúas araña de orugas de 1,5 t a 70 t de capacidad. Control remoto e indicador de par incluidos. Brazo extensor y cesto opcionales.',
            tags: ['izaje', 'izar', 'elevacion', 'elevar', 'carga', 'altura', 'vidrio', 'montaje', 'compacta', 'acceso dificil', 'tonelada', 'levantar', 'gruas'] },
          { name: 'Mini Excavadora HT15', img: '../img/prod/excavadora.png', note: 'Miniexcavadora de orugas con motor Kubota. Balanceo lateral del brazo, cabina y aire acondicionado opcionales.',
            tags: ['excavacion', 'excavar', 'zanja', 'zanjeo', 'movimiento de tierra', 'kubota', 'demolicion', 'jardin', 'pala', 'retro', 'cimiento'] },
          { name: 'Camión Volquete de Orugas', img: '../img/prod/volquete.png', note: 'Dumper de orugas para transporte de materiales en obra. Capacidades de 0,5 t y 1,2 t; versión giratoria con motor diésel.',
            tags: ['transporte', 'carga', 'materiales', 'dumper', 'orugas', 'volteo', 'escombro', 'arena', 'tierra', 'carretilla motorizada'] },
          { name: 'Montacargas Diésel 2 a 5 t', brand: 'ZS', img: '../img/prod/carretilla.png', note: 'Montacargas diésel serie CPC de 2 a 5 t con torre de 3 m. Opcionales: altura de torre, motor, horquillas y desplazador lateral.',
            tags: ['montacargas', 'pallet', 'pallets', 'deposito', 'almacen', 'carga', 'elevacion', 'diesel', 'horquilla', 'autoelevador'] },
          { name: 'Montacargas Todoterreno 3,5 t', img: '../img/prod/montacargas.png', note: 'Montacargas todoterreno 3,5 t para superficies difíciles.',
            tags: ['pallet', 'pallets', 'terreno dificil', 'obra', 'carga', 'barro', 'autoelevador', 'todoterreno', 'horquilla'] },
          { name: 'Apilador Eléctrico', img: '../img/prod/apilador.png', note: 'Apiladores eléctricos — capacidades de 1 a 2 t y alturas de 1,6 a 4,5 m.',
            tags: ['pallet', 'pallets', 'deposito', 'almacen', 'estanteria', 'elevacion', 'altura', 'electrico', 'apilar', 'zorra electrica'] },
          { name: 'Plataforma de Mástil de Aluminio', brand: 'ZS', img: '../img/prod/zs-mastil.png', note: 'Plataformas de elevación de personal con mástil de aluminio simple o doble (series SJY/SJYL): alturas de 4 a 16 m y capacidad de 100 a 240 kg.',
            tags: ['plataforma', 'mastil', 'elevador', 'dos columnas', 'altura', 'personal', 'trabajo en altura', 'mantenimiento', 'elevacion', 'andamio', 'techo', 'iluminacion', 'electricista', 'aluminio'] },
          { name: 'Transpaleta Eléctrica', brand: 'ZS', img: '../img/prod/zs-transpaleta.png', note: 'Transpaletas eléctricas de 2 a 12 t (serie CBD) y manuales de 2 a 5 t (serie HPT) para movimiento de pallets a nivel de piso.',
            tags: ['transpaleta', 'pallet', 'pallets', 'zorra', 'deposito', 'almacen', 'carga', 'electrica', 'manual', 'patin'] },
          { name: 'Carretilla Retráctil (Reach Truck)', brand: 'ZS', img: '../img/prod/zs-reach.png', note: 'Carretillas retráctiles de 1,5 a 2,5 t con elevación de hasta 7,5 m. Ideales para pasillos estrechos y estanterías altas.',
            tags: ['reach', 'retractil', 'pallet', 'estanteria', 'racks', 'deposito', 'almacen', 'pasillo', 'altura', 'apilar'] },
          { name: 'Montacargas Trilateral', brand: 'ZS', img: '../img/prod/zs-trilateral.png', note: 'Montacargas de tres vías de 1 a 3 t con elevación de hasta 15 m. Máxima densidad de almacenamiento en pasillos angostos.',
            tags: ['trilateral', 'tres vias', 'vna', 'pasillo angosto', 'estanteria', 'racks', 'deposito', 'almacen', 'altura', 'pallet'] },
          { name: 'Manipulador Telescópico', brand: 'ZS', img: '../img/prod/zs-telescopico.png', note: 'Manipuladores telescópicos de 2,5 a 4 t con alcance de hasta 17,6 m y gran variedad de implementos: horquillas, cucharas, plataforma y gancho.',
            tags: ['telescopico', 'telehandler', 'manipulador', 'alcance', 'altura', 'obra', 'agro', 'fardos', 'horquilla', 'pluma'] },
          { name: 'Montacargas Eléctrico', brand: 'ZS', img: '../img/prod/zs-mont-electrico.png', note: 'Montacargas eléctricos de 1 a 4 t (serie CPD) con elevación de 3 a 4 m. Operación silenciosa y sin emisiones, ideal para interiores.',
            tags: ['montacargas', 'electrico', 'bateria', 'pallet', 'deposito', 'almacen', 'interior', 'sin emisiones', 'autoelevador', 'horquilla'] },
          { name: 'Grúa sobre Camión', brand: 'ZS', img: '../img/prod/zs-grua-camion.png', note: 'Grúas para montar sobre camión: pluma recta de 3 a 12 t y pluma articulada de hasta 16 t, con rotación continua de 360°.',
            tags: ['grua', 'camion', 'pluma', 'articulada', 'hidraulica', 'izaje', 'carga', 'municion', 'montaje', 'transporte'] },
          { name: 'Camión Grúa (Grúa Móvil)', brand: 'ZS', img: '../img/prod/zs-camion-grua.png', note: 'Grúas móviles completas sobre camión con pluma telescópica, para izajes pesados y montajes. Capacidades a consultar.',
            tags: ['grua movil', 'camion grua', 'pluma telescopica', 'izaje', 'montaje', 'carga pesada', 'construccion', 'grua'] },
        ],
      },
      {
        title: 'Plataformas de Elevación',
        products: [
          { name: 'Plataforma Tijera Autopropulsada', brand: 'ZS', img: '../img/prod/zs-tijera.png', note: 'Plataformas tijera eléctricas autopropulsadas (serie GTJZ) con altura de trabajo de hasta 18 m y capacidad de 320 kg.',
            tags: ['tijera', 'plataforma', 'elevacion', 'altura', 'trabajo en altura', 'autopropulsada', 'electrica', 'mantenimiento', 'pintura', 'techo'] },
          { name: 'Plataforma Tijera de Orugas', brand: 'ZS', img: '../img/prod/zs-tijera-orugas.png', note: 'Plataformas tijera sobre orugas para terreno irregular, con altura de trabajo de hasta 18 m y estabilizadores.',
            tags: ['tijera', 'orugas', 'plataforma', 'terreno dificil', 'exterior', 'altura', 'trabajo en altura', 'obra', 'todo terreno'] },
          { name: 'Plataforma Articulada y Telescópica', brand: 'ZS', img: '../img/prod/zs-articulada.png', note: 'Plataformas de brazo articulado (hasta 22 m) y telescópico (hasta 34 m de altura de trabajo), con capacidad de hasta 460 kg.',
            tags: ['articulada', 'brazo', 'boom', 'plataforma', 'altura', 'trabajo en altura', 'fachada', 'mantenimiento', 'telescopica', 'cesta'] },
          { name: 'Plataforma Tijera con Estabilizadores', brand: 'ZS', img: '../img/prod/zs-tijera-estab.png', note: 'Plataformas tijera remolcables con estabilizadores extraíbles (serie KYPT): 300 a 2000 kg y alturas de plataforma de 4 a 20 m.',
            tags: ['tijera', 'estabilizadores', 'remolcable', 'plataforma', 'altura', 'trabajo en altura', 'galpon', 'mantenimiento', 'economica'] },
          { name: 'Plataforma sobre Triciclo Eléctrico', brand: 'ZS', img: '../img/prod/zs-triciclo.png', note: 'Plataforma tijera montada sobre triciclo eléctrico (serie SJYC): 300 a 500 kg y alturas de 6 a 12 m. Se desplaza sola entre puntos de trabajo.',
            tags: ['triciclo', 'tijera', 'plataforma', 'movil', 'electrica', 'alumbrado', 'mantenimiento vial', 'altura', 'poda'] },
        ],
      },
      {
        title: 'Movimiento de Suelo',
        products: [
          { name: 'Minicargadora (Skid Steer)', brand: 'ZS', img: '../img/prod/zs-minicargadora.png', note: 'Minicargadoras sobre ruedas u orugas de 13,5 a 138 HP, con implementos: balde, martillo, hoyadora, zanjadora, trituradora y más.',
            tags: ['minicargadora', 'skid steer', 'cargadora', 'balde', 'obra', 'compacta', 'orugas', 'implementos', 'bobcat', 'pala'] },
          { name: 'Retroexcavadora', brand: 'ZS', img: '../img/prod/zs-retro.png', note: 'Retroexcavadoras con cuchara cargadora de hasta 1 m³ y profundidad de excavación de hasta 3,8 m. Motores de 37 a 92 kW.',
            tags: ['retroexcavadora', 'retro', 'excavar', 'zanja', 'cargadora', 'obra', 'movimiento de tierra', 'cimiento', 'pala', 'balde'] },
          { name: 'Hincadora de Pilotes', brand: 'ZS', img: '../img/prod/zs-hincadora.png', note: 'Hincadoras de pilotes sobre orugas con motores Yuchai, para fundaciones, paneles solares y defensas viales.',
            tags: ['pilote', 'pilotes', 'hincadora', 'fundacion', 'solar', 'fotovoltaico', 'perforacion', 'orugas', 'defensa', 'poste'] },
          { name: 'Perforadora para Taludes', brand: 'ZS', img: '../img/prod/zs-taludes.png', note: 'Perforadoras sobre orugas para protección de taludes (serie SH): diámetro de perforación de 300 mm y brazos de hasta 16,5 m.',
            tags: ['talud', 'taludes', 'perforadora', 'anclaje', 'contencion', 'orugas', 'perforacion', 'ladera', 'estabilizacion'] },
          { name: 'Rodillo Compactador', brand: 'ZS', img: '../img/prod/zs-rodillo.png', note: 'Rodillos compactadores vibratorios con asiento, para compactación de suelos, bases y asfalto en obras viales.',
            tags: ['rodillo', 'compactador', 'compactacion', 'vibratorio', 'asfalto', 'suelo', 'vial', 'aplanadora', 'pison'] },
          { name: 'Bulldozer', brand: 'ZS', img: '../img/prod/zs-bulldozer.png', note: 'Bulldozers sobre orugas con hoja topadora para empuje, nivelación y desmonte de terrenos.',
            tags: ['bulldozer', 'topadora', 'orugas', 'nivelacion', 'desmonte', 'empuje', 'movimiento de tierra', 'explanacion'] },
        ],
      },
      {
        title: 'Industria',
        products: [
          { name: 'Ensayo a Compresión HST-YES2000', img: '../img/prod/compresion.png', note: 'Prensa digital para ensayos de resistencia a la compresión. Control de calidad.',
            tags: ['laboratorio', 'calidad', 'ensayo', 'probeta', 'resistencia', 'control', 'prensa', 'rotura', 'certificacion'] },
          { name: 'Motor Diésel 4HZD', img: '../img/prod/motor.png', note: 'Motor diésel industrial de alto desempeño para generación y usos estacionarios.',
            tags: ['motor', 'estacionario', 'bomba de agua', 'generacion', 'diesel', 'repuesto', 'maquinaria'] },
          { name: 'Grupo Electrógeno Diésel 38 kVA', img: '../img/prod/generador.png', note: 'Generador trifásico 400 V / 50 Hz, cabina súper silenciosa.',
            tags: ['energia', 'electricidad', 'luz', 'corte de luz', 'trifasico', 'silencioso', 'emergencia', 'generador', 'kva', 'respaldo', 'evento'] },
          { name: 'Cortacésped a Control Remoto', brand: 'ZS', img: '../img/prod/zs-cortacesped.png', note: 'Cortacésped sobre orugas a control remoto, ancho de corte de 800 a 1200 mm. Versiones a gasolina, diésel y 100% eléctricas — ideal para taludes.',
            tags: ['cortacesped', 'pasto', 'cesped', 'control remoto', 'talud', 'banquina', 'orugas', 'jardin', 'desmalezadora', 'mantenimiento vial'] },
        ],
      },
    ],
  },
  {
    id: 'aditivos', title: 'Aditivos', icon: 'flask',
    blurb: 'Más de 70 soluciones químicas para el concreto: plastificantes, impermeabilizantes, curadores, fibras y más — con ficha técnica y PDF.',
    products: [], // renderizado desde ADITIVOS (ver selectCategory)
  },
  {
    id: 'fletes', title: 'Fletes', icon: 'truck',
    blurb: 'FletePar: la plataforma de fletes #1 de Paraguay. Conectamos cargas con transportistas verificados, en tiempo real.',
    products: [], // la categoría se renderiza con el panel FletePar (ver selectCategory)
  },
  {
    id: 'morteros', title: 'Morteros', icon: 'grid',
    blurb: 'Morteros industrializados Hormigomix: estructural, de proyección y adhesivos AC-1 / AC-3.',
    products: [
      { name: 'Mortero Estructural 30 kg', brand: 'Hormigomix', img: '../img/prod/mortero-estructural.png',
        note: 'Asentamiento estructural de albañilería. Mortero industrializado de alta calidad — solo agregar agua.',
        tags: ['mortero', 'morteros', 'argamassa', 'hormigomix', 'asentamiento', 'ladrillo', 'ladrillos', 'bloque', 'bloques', 'mamposteria', 'albanileria', 'muro', 'pared', 'estructural', 'levantar pared'] },
      { name: 'Mortero de Proyección 30 kg', brand: 'Hormigomix', img: '../img/prod/mortero-proyeccion.png',
        note: 'Revoque de paredes de mampostería en áreas internas y externas. Aplicable con equipos de proyección.',
        tags: ['mortero', 'morteros', 'argamassa', 'hormigomix', 'revoque', 'revoco', 'proyeccion', 'proyectado', 'pared', 'muro', 'interior', 'exterior', 'maquina', 'revestir'] },
      { name: 'Mortero Adhesivo AC-1 20 kg', brand: 'Hormigomix', img: '../img/prod/mortero-ac1.png',
        note: 'Colocación de revestimientos y pisos cerámicos en interiores. Aplicación rápida.',
        tags: ['mortero', 'morteros', 'argamassa', 'hormigomix', 'adhesivo', 'pegamento', 'cola', 'ceramica', 'ceramico', 'azulejo', 'piso', 'pared', 'interior', 'ac1', 'pegar'] },
      { name: 'Mortero Adhesivo AC-3 20 kg', brand: 'Hormigomix', img: '../img/prod/mortero-ac3.png',
        note: 'Revestimientos, cerámicos y gres porcelánico en interiores y exteriores. Apto para placas de más de 60×60 cm.',
        tags: ['mortero', 'morteros', 'argamassa', 'hormigomix', 'adhesivo', 'pegamento', 'cola', 'porcelanato', 'gres', 'ceramica', 'ceramico', 'placa', 'exterior', 'interior', 'ac3', 'fachada', 'pegar'] },
    ],
  },
  {
    id: 'intonaco', title: 'Intonaco', icon: 'spray',
    blurb: 'Revoque proyectado con método: hasta 5× más productividad y plazo confiable. Sistemas constructivos Intonaco.',
    products: [], // la categoría se renderiza con el panel Intonaco (ver selectCategory)
  },
  {
    id: 'cementos', title: 'Cementos', icon: 'layers',
    blurb: 'Cemento de alto desempeño para toda obra.',
    products: [],
  },
  {
    id: 'pisos', title: 'Pisos', icon: 'floor',
    blurb: 'Kasteller Revestimientos: pisos y revestimientos de alta gama que definen espacios.',
    products: [], // la categoría se renderiza con el panel Kasteller (ver selectCategory)
  },
]

/* ============================================================
   TABLAS DE MODELOS — transcriptas del catálogo Jinan Zhishen (ZS)
   ============================================================ */
export const SPECS: Record<string, { h: string[]; r: string[][] }> = {
  'Transpaleta Eléctrica': { h: ['Modelo', 'Carga', 'Elevación', 'Peso'], r: [
    ['CBD20','2000 kg','205 mm','600 kg'],['CBD25','2500 kg','205 mm','600 kg'],['CBD30','3000 kg','205 mm','600 kg'],
    ['CBD50','5000 kg','215 mm','945 kg'],['CBD60','6000 kg','215 mm','945 kg'],['CBD80','8000 kg','220 mm','1980 kg'],
    ['CBD100','10000 kg','235 mm','1880 kg'],['CBD120','12000 kg','240 mm','1980 kg'],['CBD20B','2000 kg','205 mm','640 kg'],
    ['CBD25B','2500 kg','205 mm','640 kg'],['CBD30B','3000 kg','205 mm','640 kg'],['HPT20 (manual)','2000 kg','200 mm','65 kg'],
    ['HPT25 (manual)','2500 kg','200 mm','72 kg'],['HPT30 (manual)','3000 kg','200 mm','75 kg'],['HPT50 (manual)','5000 kg','200 mm','118–128 kg'] ] },
  'Carretilla Retráctil (Reach Truck)': { h: ['Modelo', 'Carga', 'Elevación', 'Peso'], r: [
    ['CQD15A','1500 kg','2500 mm','2050 kg'],['CQD15A','1500 kg','4500 mm','2240 kg'],['CQD20A','2000 kg','2500 mm','2150 kg'],
    ['CQD20A','2000 kg','4500 mm','2360 kg'],['CQD15B','1500 kg','6000 mm','2600 kg'],['CQD20B','2000 kg','6000 mm','2720 kg'],
    ['CQD20B','2000 kg','3000 mm','2375 kg'],['CQD16','1600 kg','6000 mm','3150 kg'],['CQD16','1600 kg','7500 mm','3320 kg'],
    ['CQD20','2000 kg','6000 mm','3350 kg'],['CQD20','2000 kg','7500 mm','3500 kg'],['CQD25','2500 kg','6000 mm','3430 kg'],
    ['CQD25','2500 kg','7500 mm','3600 kg'],['CQD16J','1600 kg','6000 mm','4050 kg'],['CQD20J','2000 kg','6000 mm','4000 kg'],
    ['CQD15AJ','1500 kg','5000 mm','2730 kg'],['CQD20AJ','2000 kg','5000 mm','2850 kg'] ] },
  'Montacargas Trilateral': { h: ['Modelo', 'Carga', 'Elevación', 'Peso'], r: [
    ['CSD10','1000 kg','6000 mm','5150 kg'],['CSD15','1500 kg','6000 mm','6150 kg'],
    ['CSD15','1500 kg','9000 mm','7300 kg'],['CSD30-150','3000 kg','15000 mm','—'] ] },
  'Manipulador Telescópico': { h: ['Modelo', 'Capacidad', 'Altura', 'Alcance', 'Potencia', 'Peso'], r: [
    ['ZSC1840','4000 kg','17,6 m','13,1 m','81 kW','12600 kg'],['ZSC1440','4000 kg','13,5 m','9,5 m','81 kW','10800 kg'],
    ['ZSC735','3500 kg','7 m','3,9 m','81 kW','7600 kg'],['ZSC625','2500 kg','5,95 m','2,19 m','55,4 kW','4900 kg'] ] },
  'Montacargas Diésel 2 a 5 t': { h: ['Modelo', 'Carga', 'Elevación', 'Potencia', 'Peso'], r: [
    ['CPC20','2000 kg','3000 mm','39 kW','3260 kg'],['CPC25','2500 kg','3000 mm','39 kW','3510 kg'],
    ['CPC30','3000 kg','3000 mm','39 kW','4100 kg'],['CPC35','3500 kg','3000 mm','39 kW','4390 kg'],
    ['CPC38','3500 kg','3000 mm','39 kW','4550 kg'],['CPC40','4000 kg','3000 mm','48 kW','6290 kg'],
    ['CPC45','4500 kg','3000 mm','48 kW','6490 kg'],['CPC50','5000 kg','3000 mm','48 kW','6660 kg'] ] },
  'Montacargas Eléctrico': { h: ['Modelo', 'Carga', 'Elevación', 'Peso'], r: [
    ['CPD10','1000 kg','3000 mm','1500 kg'],['CPD15','1500 kg','3000 mm','2500 kg'],['CPD20','2000 kg','3000 mm','3000 kg'],
    ['CPD25','2500 kg','3000 mm','3600 kg'],['CPD30','3000 kg','3000 mm','4000 kg'],['CPD35','3500 kg','3000 mm','4400 kg'],
    ['CPD40','4000 kg','4000 mm','4800 kg'] ] },
  'Grúa sobre Camión': { h: ['Modelo', 'Tipo', 'Capacidad', 'Brazo / Altura'], r: [
    ['ZS-30','Recta','3 t','3 m · 3 secciones'],['ZS-60','Recta','6 t','3,5 m · 4 secciones'],
    ['ZS-80','Recta','8 t','4 m · 4 secciones'],['ZS-100','Recta','10 t','4,5–5 m · 5 secciones'],
    ['ZS-120','Recta','12 t','5 m · 4 secciones'],['ZS-320','Articulada','3200 kg','9,6 m · radio 7,2 m'],
    ['ZS-630','Articulada','6300 kg','10,6 m · radio 8,2 m'],['ZS-800','Articulada','8000 kg','15 m · radio 12,6 m'],
    ['ZS-1000','Articulada','10000 kg','15 m · radio 12,3 m'],['ZS-1200','Articulada','12000 kg','14,7 m · radio 12,6 m'],
    ['ZS-1600','Articulada','16000 kg','19 m · radio 16,5 m'] ] },
  'Mini Excavadora HT15': { h: ['Modelo', 'Potencia', 'Prof. excavación', 'Cuchara', 'Peso'], r: [
    ['SE08','8,6 kW','1375 mm','0,02 m³','800 kg'],['SE09','8,6 kW','1200 mm','0,02 m³','900 kg'],
    ['SE10','8,6 kW','1650 mm','0,025 m³','1000 kg'],['SE12','8,6 kW','1650 mm','0,03 m³','1200 kg'],
    ['SE15','14,1 kW','1800 mm','0,03 m³','1500 kg'],['SE16','19 kW','1800 mm','0,035 m³','1600 kg'],
    ['SE17','19 kW','1900 mm','0,035 m³','1700 kg'],['SE18','18,1 kW','2000 mm','0,035 m³','1800 kg'],
    ['ST20-1','19 kW','2060 mm','0,04 m³','2000 kg'],['ST25-2','18,4 kW','2500 mm','0,06 m³','2500 kg'],
    ['ST26-2','20 kW','2550 mm','0,075 m³','2600 kg'],['ST30','14,2 kW','2450 mm','0,1 m³','3000 kg'],
    ['ST35','18,5 kW','3106 mm','0,12 m³','3500 kg'],['ST40','18,5 kW','3208 mm','0,12 m³','4000 kg'],
    ['ST60','37,4 kW','3820 mm','0,3 m³','6000 kg'] ] },
  'Plataforma Tijera Autopropulsada': { h: ['Modelo', 'Capacidad', 'Alt. plataforma', 'Alt. trabajo', 'Peso'], r: [
    ['GTJZ03','300 kg','3000 mm','5000 mm','700 kg'],['GTJZ04','300 kg','4000 mm','6000 mm','750 kg'],
    ['GTJZ06-M','320 kg','6000 mm','8000 mm','1400 kg'],['GTJZ08-M','320 kg','8000 mm','10000 mm','2100 kg'],
    ['GTJZ06','320 kg','6000 mm','8000 mm','1900 kg'],['GTJZ08','320 kg','8000 mm','10000 mm','2400 kg'],
    ['GTJZ10','320 kg','10000 mm','12000 mm','2700 kg'],['GTJZ12','320 kg','12000 mm','14000 mm','2800 kg'],
    ['GTJZ14','320 kg','14000 mm','16000 mm','3400 kg'],['GTJZ16','320 kg','16000 mm','18000 mm','4200 kg'] ] },
  'Plataforma Tijera de Orugas': { h: ['Modelo', 'Capacidad', 'Alt. plataforma', 'Alt. trabajo', 'Peso'], r: [
    ['GTJZ06','300 kg','6000 mm','8000 mm','3200 kg'],['GTJZ08','320 kg','8000 mm','10000 mm','3300 kg'],
    ['GTJZ10','300 kg','10000 mm','12000 mm','3540 kg'],['GTJZ12','300 kg','12000 mm','14000 mm','3700 kg'],
    ['GTJZ14','300 kg','14000 mm','16000 mm','4500 kg'],['GTJZ14-M','300 kg','14000 mm','18000 mm','4000 kg'] ] },
  'Plataforma Articulada y Telescópica': { h: ['Modelo', 'Tipo', 'Capacidad', 'Alt. trabajo', 'Peso'], r: [
    ['SQ16D','Articulada','230 kg','16 m','7600 kg'],['SQ16','Articulada','230 kg','16 m','8110 kg'],
    ['SQ22D','Articulada','250 kg','22 m','9200 kg'],['SZ20D','Telescópica','460 kg','20,5 m','9800 kg'],
    ['SZ23D','Telescópica','460 kg','24,1 m','10500 kg'],['SZ23','Telescópica','460 kg','24,1 m','11230 kg'],
    ['SZ26D','Telescópica','460 kg','26 m','12000 kg'],['SZ28D','Telescópica','460 kg','28,7 m','16600 kg'],
    ['SZ30D','Telescópica','460 kg','30,6 m','17500 kg'],['SZ34D','Telescópica','460 kg','34 m','18600 kg'] ] },
  'Plataforma Tijera con Estabilizadores': { h: ['Modelo', 'Capacidad', 'Alt. plataforma', 'Peso'], r: [
    ['KYPT0.5-4','500 kg','4 m','800 kg'],['KYPT0.5-6','500 kg','6 m','880 kg'],['KYPT0.5-7','500 kg','6,8 m','970 kg'],
    ['KYPT0.5-8','500 kg','8 m','1050 kg'],['KYPT0.5-9','500 kg','9 m','1165 kg'],['KYPT0.5-10','500 kg','10 m','1360 kg'],
    ['KYPT0.3-11','300 kg','11 m','1400 kg'],['KYPT0.5-11','500 kg','11 m','1450 kg'],['KYPT0.5-12','500 kg','12 m','2260 kg'],
    ['KYPT0.5-14','500 kg','14 m','2486 kg'],['KYPT0.3-16','300 kg','16 m','3063 kg'],['KYPT0.5-16','500 kg','16 m','3100 kg'],
    ['KYPT0.3-18','300 kg','18 m','3900 kg'],['KYPT0.5-18','500 kg','18 m','4500 kg'],['KYPT0.5-20','500 kg','20 m','5600 kg'],
    ['KYPT1.0-4','1000 kg','4 m','1250 kg'],['KYPT1.0-6','1000 kg','6 m','1400 kg'],['KYPT1.0-8','1000 kg','8 m','1585 kg'],
    ['KYPT1.0-10','1000 kg','10 m','1700 kg'],['KYPT1.0-12','1000 kg','12 m','2560 kg'],['KYPT1.0-14','1000 kg','14 m','3230 kg'],
    ['KYPT1.5-6','1500 kg','6 m','1780 kg'],['KYPT1.5-8','1500 kg','8 m','2070 kg'],['KYPT1.5-10','1500 kg','10 m','2250 kg'],
    ['KYPT2.0-6','2000 kg','6 m','1780 kg'],['KYPT2.0-8','2000 kg','8 m','2070 kg'],['KYPT2.0-10','2000 kg','10 m','2250 kg'] ] },
  'Plataforma sobre Triciclo Eléctrico': { h: ['Modelo', 'Capacidad', 'Alt. plataforma', 'Peso'], r: [
    ['SJYC06','300 kg','6 m','1500 kg'],['SJYC08','300 kg','8 m','1600 kg'],['SJYC10','300 kg','10 m','1800 kg'],
    ['SJYC11.8','300 kg','11,8 m','1900 kg'],['SJYC0.5-12','500 kg','12 m','2230 kg'] ] },
  'Plataforma de Mástil de Aluminio': { h: ['Modelo', 'Mástil', 'Capacidad', 'Altura', 'Peso'], r: [
    ['SJY0.15-4','Simple','150 kg','4 m','230 kg'],['SJY0.15-6','Simple','150 kg','6 m','270 kg'],
    ['SJY0.12-8','Simple','120 kg','8 m','290 kg'],['SJY0.1-9','Simple','100 kg','9 m','320 kg'],
    ['SJY0.1-10','Simple','100 kg','10 m','330 kg'],['SJYL0.2-4','Doble','240 kg','4 m','360 kg'],
    ['SJYL0.23-6','Doble','230 kg','6 m','400 kg'],['SJYL0.23-8','Doble','230 kg','8 m','440 kg'],
    ['SJYL0.23-10','Doble','230 kg','10 m','520 kg'],['SJYL0.22-12','Doble','220 kg','12 m','610 kg'],
    ['SJYL0.2-14','Doble','200 kg','14 m','670 kg'],['SJYL0.15-16','Doble','150 kg','16 m','750 kg'] ] },
  'Minicargadora (Skid Steer)': { h: ['Modelo', 'Carga operativa', 'Potencia'], r: [
    ['320T','250 kg','13 HP'],['S360','320 kg','13,5 HP'],['380T','300 kg','21,5–23 HP'],['S380','300 kg','21,5–23 HP'],
    ['S382T','380 kg','26 HP'],['SL390','250 kg','13,5 HP'],['T470','350 kg','20–25 HP'],['S530','450 kg','19 HP'],
    ['S530T','380 kg','23 HP'],['V1000','454 kg','25 HP'],['S25','380 kg','25 HP'],['S35','500 kg','50 HP'],
    ['S45','700 kg','50 HP'],['S50','750 kg','49,5 HP'],['S60','700 kg','48 HP'],['S65','700 kg','48 HP'],
    ['S75','1050 kg','74 HP'],['S100','1200 kg','100,5 HP'],['S120','1500 kg','138 HP'],['S125','1500 kg','138 HP'] ] },
  'Retroexcavadora': { h: ['Modelo', 'Potencia', 'Prof. excavación', 'Cuchara carg./retro', 'Peso'], r: [
    ['SLA08-12','37 kW','1500 mm','0,4 / 0,08 m³','2800 kg'],['SLA10-20','37 kW','2000 mm','0,5 / 0,1 m³','3400 kg'],
    ['SLA15-26','58 kW','2700 mm','0,7 / 0,2 m³','4500 kg'],['SLA20-28','76 kW','2600 mm','1 / 0,2 m³','5400 kg'],
    ['SLA25-30','92 kW','2600 mm','1,2 / 0,25 m³','6200 kg'],['SLA30-40','92 kW','2700 mm','1,2 / 0,25 m³','7000 kg'],
    ['SLA40-28','72 kW','3800 mm','1 / 0,3 m³','8000 kg'] ] },
  'Hincadora de Pilotes': { h: ['Modelo', 'Motor', 'Oruga', 'Áng. inclinación'], r: [
    ['SRS-G47','Yuchai 4 cilindros','300 mm','45°'],['SRS-G47N','Yuchai 6 cilindros','300 mm','45°'],
    ['SRY-G47','Yuchai 6 cilindros','400 mm','30°'],['SRY-G65','Yuchai 6 cil. (130 kW)','400 mm','30°'],
    ['SRY-G65i','Yuchai 4 cil. (85 kW)','400 mm','30°'],['SRF-G42P','75 kW','400 mm','30°'],['SRF-G42','50 kW','400 mm','30°'] ] },
  'Perforadora para Taludes': { h: ['Modelo', 'Perforación', 'Par reductor', 'Dimensiones'], r: [
    ['SH-350','300 mm','13000 N·m','16500×3000×3400 mm'],['SH-300','300 mm','13000 N·m','14800×3000×3400 mm'],
    ['SH-250','300 mm','13000 N·m','14500×2800×3400 mm'],['SH-220','300 mm','13000 N·m','14300×2800×3400 mm'],
    ['SH-200','300 mm','13000 N·m','11800×2800×3400 mm'],['SH-150','300 mm','8000 N·m','11500×2300×3200 mm'],
    ['SH-120','300 mm','8000 N·m','11000×2300×2900 mm'],['SH-100','300 mm','8000 N·m','9900×2300×2500 mm'],
    ['SH-80','300 mm','8000 N·m','9500×2300×2500 mm'],['SH-60','300 mm','8000 N·m','9500×2300×2500 mm'] ] },
  'Cortacésped a Control Remoto': { h: ['Versión', 'Ancho de corte', 'Motor'], r: [
    ['Oruga 800','800 mm','16 HP gasolina'],['Oruga 1000','1000 mm','22 / 25 / 27 HP gasolina'],
    ['Oruga 1200','1200 mm','22 / 25 / 27 HP gasolina'],['Cuchilla vertical','800 mm','22 / 25 / 27 HP gasolina'],
    ['Cortadora vertical','1000 mm','13–25 HP diésel / gasolina'],['EV eléctrica','550–800 mm','Batería 48 V / 60 V'] ] },
}

/* injeta as tabelas de modelos nos produtos correspondentes */
for (const c of CATALOG) {
  const prods = [...(c.groups ?? []).flatMap((g) => g.products), ...(c.products ?? [])]
  for (const pr of prods) if (SPECS[pr.name]) pr.specs = SPECS[pr.name]
}
