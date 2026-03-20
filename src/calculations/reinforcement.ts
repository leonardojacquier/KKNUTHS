import { GeometryInput, ConcreteInput, ReinforcementResult } from '../types';

/**
 * Dimensionamento da armadura de temperatura e retração
 * Referências: ACI 318, DNIT, ACI 360R, NBR 6118
 */
export function calcularArmadura(
  geo: GeometryInput,
  conc: ConcreteInput,
  espessura_cm: number,
  tipo_pavimento: string
): ReinforcementResult {
  const h = espessura_cm; // cm

  // ---- Armadura de temperatura / retração ----
  // ACI 318 / ACI 360R: As_min = 0.0018 * b * h (taxa mínima 0.18%)
  // Para pavimentos de concreto simples: armadura apenas se h > 25 cm
  // Para pisos com juntas: geralmente não há armadura convencional
  const tem_armadura = h > 20 || tipo_pavimento === 'rodovia';

  let as_m2 = 0;
  let diametro = 0;
  let espacamento = 0;
  let taxa = 0;

  if (tem_armadura) {
    // Taxa mínima para temperatura/retração
    taxa = tipo_pavimento === 'piso' ? 0.0015 : 0.0018; // ACI 318

    // As (cm²/m) = taxa * h (cm) * 100 (base 1m)
    as_m2 = taxa * h * 100; // cm²/m

    // Bitola comercial mínima para pavimentos
    // Série: ∅8, ∅10, ∅12, ∅16, ∅20
    const bitolas = [8, 10, 12, 16, 20];
    diametro = 10; // padrão
    for (const d of bitolas) {
      const as_barra = Math.PI * d * d / 4; // mm²
      const esp = Math.floor((as_barra / 100) / (as_m2 / 100) * 100); // cm
      if (esp >= 15 && esp <= 40) {
        diametro = d;
        espacamento = Math.floor(esp / 5) * 5; // múltiplo de 5 cm
        break;
      }
    }
    if (espacamento === 0) {
      diametro = 12;
      espacamento = 20;
    }
  }

  // ---- Dowels (barras de transferência de carga nas juntas transversais) ----
  // Critério: usar se h > 18 cm (DNIT / PCA)
  const usar_dowels = geo.dowels || h >= 18;
  let diametro_dowel = geo.diametro_dowel ?? 0;
  let espaco_dowel = geo.espaco_dowel ?? 0;
  let comprimento_dowel = 0;

  if (usar_dowels) {
    // Diâmetro do dowel em função da espessura (PCA)
    if (diametro_dowel === 0) {
      if (h <= 20) diametro_dowel = 20;       // ∅20 mm
      else if (h <= 25) diametro_dowel = 25;  // ∅25 mm
      else if (h <= 30) diametro_dowel = 32;  // ∅32 mm
      else diametro_dowel = 38;               // ∅38 mm
    }
    comprimento_dowel = Math.max(500, diametro_dowel * 18); // mín 500 mm, norma 18∅
    if (espaco_dowel === 0) espaco_dowel = 30; // cm padrão (300 mm)
  }

  // ---- Tie Bars (barras de ligação nas juntas longitudinais) ----
  // Critério: usar em juntas longitudinais para amarrar faixas
  const usar_tie = geo.tie_bars || tipo_pavimento === 'rodovia';
  let diametro_tie = geo.diametro_tie_bar ?? 0;
  let espaco_tie = geo.espaco_tie_bar ?? 0;
  let comprimento_tie = 0;

  if (usar_tie) {
    // Tie bars: CA-50, ∅12 a ∅16 mm (ACI / PCA)
    if (diametro_tie === 0) diametro_tie = 12;
    comprimento_tie = Math.max(700, diametro_tie * 48); // 48∅ de ancoragem + comprimento de emenda
    if (espaco_tie === 0) espaco_tie = 75; // cm padrão
  }

  return {
    armadura_temperatura: tem_armadura,
    diametro_barra: diametro,
    espacamento,
    taxa_armadura: taxa * 100,
    as_calculado: Math.round(as_m2 * 100) / 100,
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
