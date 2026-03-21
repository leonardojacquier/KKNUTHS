import { GeometryInput, ConcreteInput, ReinforcementResult, MeshType, MeshResult } from '../types';

/**
 * Dimensionamento de armadura de temperatura, retração e estrutural
 * Inclui: barras individuais e malhas eletrossoldadas
 * Referências: ACI 318, ACI 360R, DNIT, NBR 6118, NBR 7480
 */

// Malhas eletrossoldadas padrão (ABNT NBR 7480 - CA-60)
// Nomenclatura Q(área mm²/m por direção)
interface MeshSpec {
  tipo: MeshType;
  diametro: number;       // mm
  espacamento: number;    // mm
  as_mm2: number;         // mm²/m por direção
  peso_m2: number;        // kg/m² (ambas direções)
  descricao: string;
}

const MALHAS: MeshSpec[] = [
  { tipo: 'Q92',  diametro: 4.2, espacamento: 150, as_mm2:  92, peso_m2: 0.91, descricao: 'Q-92 (∅4.2@150mm)' },
  { tipo: 'Q131', diametro: 4.7, espacamento: 133, as_mm2: 131, peso_m2: 1.31, descricao: 'Q-131 (∅4.7@133mm)' },
  { tipo: 'Q188', diametro: 5.0, espacamento: 104, as_mm2: 188, peso_m2: 1.89, descricao: 'Q-188 (∅5.0@104mm)' },
  { tipo: 'Q283', diametro: 6.0, espacamento: 100, as_mm2: 283, peso_m2: 2.84, descricao: 'Q-283 (∅6.0@100mm)' },
  { tipo: 'Q335', diametro: 6.5, espacamento: 100, as_mm2: 335, peso_m2: 3.35, descricao: 'Q-335 (∅6.5@100mm)' },
  { tipo: 'Q503', diametro: 8.0, espacamento: 100, as_mm2: 503, peso_m2: 5.03, descricao: 'Q-503 (∅8.0@100mm)' },
  { tipo: 'Q636', diametro: 9.0, espacamento: 100, as_mm2: 636, peso_m2: 6.36, descricao: 'Q-636 (∅9.0@100mm)' },
];

// Seleciona malha adequada para o As requerido (mm²/m)
function selecionarMalha(as_requerida_mm2: number, tipo_preferido?: MeshType): MeshSpec {
  if (tipo_preferido) {
    const m = MALHAS.find(m => m.tipo === tipo_preferido);
    if (m) return m;
  }
  // Seleciona a menor malha que atende ao As requerido
  const adequada = MALHAS.find(m => m.as_mm2 >= as_requerida_mm2);
  return adequada ?? MALHAS[MALHAS.length - 1]; // maior disponível
}

// Dimensões padrão de folha de malha no mercado (m)
function dimensoesFolhaMalha(): { larg: number; comp: number } {
  return { larg: 2.45, comp: 6.10 }; // padrão ABNT mais comum
}

function calcularMalha(
  as_requerida_cm2: number, // cm²/m
  geo: GeometryInput
): MeshResult {
  const as_requerida_mm2 = as_requerida_cm2 * 100; // cm²/m → mm²/m
  const spec = selecionarMalha(as_requerida_mm2, geo.tipo_malha);
  const { larg, comp } = dimensoesFolhaMalha();
  const area_folha = larg * comp; // m²
  const area_placa = geo.comprimento_placa * geo.largura_placa;
  const folhas = Math.ceil(area_placa / area_folha * 1.10); // 10% perda/emenda

  return {
    tipo_malha: spec.tipo,
    diametro_fio: spec.diametro,
    espacamento: spec.espacamento,
    as_fornecida: spec.as_mm2,
    as_requerida: as_requerida_mm2,
    peso_por_m2: spec.peso_m2,
    dimensoes_padrao: `${larg.toFixed(2)}m × ${comp.toFixed(2)}m`,
    folhas_por_placa: folhas,
  };
}

export function calcularArmadura(
  geo: GeometryInput,
  conc: ConcreteInput,
  espessura_cm: number,
  tipo_pavimento: string,
  fibras_substitui_temp?: boolean
): ReinforcementResult {
  const h = espessura_cm; // cm
  const tipo_arm = geo.tipo_armadura ?? 'temperature';

  // ---- Armadura de temperatura / retração ----
  // ACI 318 / ACI 360R: As_min = 0.0018 * b * h (taxa mínima 0.18%)
  const tem_armadura =
    !fibras_substitui_temp &&
    (h > 20 || tipo_pavimento === 'rodovia' || tipo_arm !== 'none');

  let as_m2 = 0;       // cm²/m
  let diametro = 0;    // mm
  let espacamento = 0; // cm
  let taxa = 0;

  if (tem_armadura) {
    taxa = tipo_pavimento === 'piso' ? 0.0015 : 0.0018;
    // Ajuste para armadura estrutural (maior taxa)
    if (tipo_arm === 'structural_bars') taxa = Math.max(taxa, 0.0020);

    // As (cm²/m) = taxa * h (cm) * 100 (base 1m)
    as_m2 = taxa * h * 100;

    // Bitola comercial
    const bitolas = [8, 10, 12, 16, 20];
    diametro = 10;
    for (const d of bitolas) {
      const as_barra = Math.PI * d * d / 4; // mm²
      const esp = Math.floor((as_barra / 100) / (as_m2 / 100) * 100);
      if (esp >= 15 && esp <= 40) {
        diametro = d;
        espacamento = Math.floor(esp / 5) * 5;
        break;
      }
    }
    if (espacamento === 0) { diametro = 12; espacamento = 20; }
  }

  // ---- Armadura Estrutural (além da temperatura) ----
  let as_estrutural: number | undefined;
  let diametro_estrutural: number | undefined;
  let esp_estrutural: number | undefined;

  if (geo.usar_armadura_estrutural && tipo_arm === 'structural_bars') {
    // Armadura estrutural para controle de fissuras e distribuição de cargas
    // NBR 6118 / ACI 360R: taxa mínima para pavimentos 0.25-0.50%
    const taxa_estru = tipo_pavimento === 'aeroporto' ? 0.0040 : 0.0025;
    as_estrutural = taxa_estru * h * 100; // cm²/m

    // Seleciona bitola para armadura estrutural
    const bitolas_estru = [10, 12, 16, 20, 25];
    diametro_estrutural = 12;
    esp_estrutural = 20;
    for (const d of bitolas_estru) {
      const as_barra = Math.PI * d * d / 4;
      const esp = Math.floor((as_barra / 100) / (as_estrutural / 100) * 100);
      if (esp >= 10 && esp <= 30) {
        diametro_estrutural = d;
        esp_estrutural = Math.floor(esp / 5) * 5;
        break;
      }
    }
  }

  // ---- Malha Eletrossoldada ----
  let malha: MeshResult | undefined;
  if (tipo_arm === 'mesh' && tem_armadura) {
    malha = calcularMalha(as_m2, geo);
  }

  // ---- Dowels (barras de transferência de carga nas juntas transversais) ----
  const usar_dowels = geo.dowels || h >= 18;
  let diametro_dowel = geo.diametro_dowel ?? 0;
  let espaco_dowel = geo.espaco_dowel ?? 0;
  let comprimento_dowel = 0;

  if (usar_dowels) {
    if (diametro_dowel === 0) {
      if (h <= 20) diametro_dowel = 20;
      else if (h <= 25) diametro_dowel = 25;
      else if (h <= 30) diametro_dowel = 32;
      else if (h <= 40) diametro_dowel = 38;
      else diametro_dowel = 45;
    }
    // Comprimento: max(500mm, 18∅) – DNIT/PCA; aeroportos usam 450-600mm
    comprimento_dowel = Math.max(500, diametro_dowel * 18);
    if (espaco_dowel === 0) espaco_dowel = 30;
  }

  // ---- Tie Bars (barras de ligação nas juntas longitudinais) ----
  const usar_tie = geo.tie_bars || tipo_pavimento === 'rodovia';
  let diametro_tie = geo.diametro_tie_bar ?? 0;
  let espaco_tie = geo.espaco_tie_bar ?? 0;
  let comprimento_tie = 0;

  if (usar_tie) {
    if (diametro_tie === 0) {
      // CA-50 nervurado: ∅12-∅16
      diametro_tie = h >= 25 ? 16 : 12;
    }
    comprimento_tie = Math.max(700, diametro_tie * 48);
    if (espaco_tie === 0) espaco_tie = 75;
  }

  return {
    tipo: tipo_arm,
    armadura_temperatura: tem_armadura,
    diametro_barra: diametro,
    espacamento,
    taxa_armadura: taxa * 100,
    as_calculado: Math.round(as_m2 * 100) / 100,
    malha,
    armadura_estrutural: geo.usar_armadura_estrutural && tipo_arm === 'structural_bars',
    as_estrutural: as_estrutural ? Math.round(as_estrutural * 100) / 100 : undefined,
    diametro_estrutural,
    espacamento_estrutural: esp_estrutural,
    dowels: usar_dowels,
    diametro_dowel: usar_dowels ? diametro_dowel : undefined,
    comprimento_dowel: usar_dowels ? comprimento_dowel : undefined,
    espacamento_dowel: usar_dowels ? espaco_dowel : undefined,
    tie_bars: usar_tie,
    diametro_tie_bar: usar_tie ? diametro_tie : undefined,
    comprimento_tie_bar: usar_tie ? comprimento_tie : undefined,
    espacamento_tie_bar: usar_tie ? espaco_tie : undefined,
  };
}

export { MALHAS, selecionarMalha };
