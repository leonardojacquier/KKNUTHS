import { ConcreteInput, ConcreteMixResult } from '../types';

/**
 * Dimensionamento do traço do concreto
 * Referência: NBR 12655:2022 e ABCP – Método de Dosagem para Concreto Estrutural
 */

// Massa específica dos materiais (kg/dm³)
const DENSIDADE_CIMENTO = 3.1;
const DENSIDADE_AREIA   = 2.65;
const DENSIDADE_BRITA: Record<string, number> = {
  basalto:  3.0,
  granito:  2.65,
  calcario: 2.7,
  seixo:    2.60,
};

// Desvio padrão característico (MPa) por nível de controle NBR 12655
const DESVIO_PADRAO: Record<string, number> = {
  'I':   4.0,   // Controle rigoroso (obra grande)
  'II':  5.0,
  'III': 6.0,
  'IV':  7.0,
};

// Relação a/c máxima por classe de agressividade (NBR 6118)
const AC_MAX: Record<string, number> = {
  'I':   0.65,
  'II':  0.60,
  'III': 0.55,
  'IV':  0.45,
};

// Consumo mínimo de cimento por classe de agressividade (kg/m³)
const C_MIN: Record<string, number> = {
  'I':   260,
  'II':  280,
  'III': 320,
  'IV':  360,
};

/**
 * Relação a/c em função do fck (curva de Abrams adaptada para cimento CP-V-ARI)
 * a/c = A / (B + fck)  onde A e B dependem do tipo de cimento
 */
function acFromFck(fck: number, tipo_cimento: string): number {
  // Constantes para curva de Abrams (Petrucci / ABCP)
  const curvas: Record<string, [number, number]> = {
    'CP-I':     [87, 0.5],
    'CP-II-E':  [85, 0.5],
    'CP-II-F':  [88, 0.5],
    'CP-II-Z':  [86, 0.5],
    'CP-III':   [83, 0.5],
    'CP-IV':    [80, 0.5],
    'CP-V-ARI': [95, 0.5],
  };
  const [A] = curvas[tipo_cimento] ?? [85, 0.5];
  // Resistência de dosagem: fcd = fck + 1.65 * sigma_sd
  const sigma = 5.0;
  const fcj = fck + 1.65 * sigma;
  // Curva de Abrams: fcj = A * B^(c/a) → a/c = log(A/fcj) / log(B)
  // Simplificado: relação linear-log empírica
  const ac = Math.exp(Math.log(A / fcj) / 1.5);
  return Math.max(0.30, Math.min(0.75, ac));
}

/**
 * Cálculo do consumo de cimento (kg/m³)
 * Método ACI / ABCP
 */
function consumoCimento(ac: number, agua: number): number {
  return agua / ac;
}

/**
 * Consumo de água em função do abatimento e TMA do agregado
 * NBR 12655 Tabela 2 (aproximação)
 */
function consumoAgua(abatimento_mm: number, tma_mm: number): number {
  // Valores base (mm abatimento 60-100 mm, TMA variado)
  const tabela: Record<number, Record<number, number>> = {
    9.5:  { 40: 225, 80: 240, 120: 255, 160: 265 },
    12.5: { 40: 215, 80: 228, 120: 242, 160: 252 },
    19:   { 40: 200, 80: 213, 120: 226, 160: 236 },
    25:   { 40: 193, 80: 204, 120: 216, 160: 225 },
    38:   { 40: 181, 80: 192, 120: 202, 160: 211 },
  };

  const tmas = Object.keys(tabela).map(Number);
  const tma_ref = tmas.reduce((p, c) => Math.abs(c - tma_mm) < Math.abs(p - tma_mm) ? c : p);
  const slumps = Object.keys(tabela[tma_ref]).map(Number);
  const slump_ref = slumps.reduce((p, c) => Math.abs(c - abatimento_mm) < Math.abs(p - abatimento_mm) ? c : p);
  return tabela[tma_ref][slump_ref];
}

/**
 * Módulo de elasticidade do concreto (GPa)
 * NBR 6118: Eci = 5600 * sqrt(fck)  (MPa)
 */
function moduloElasticidade(fck: number): number {
  return 5600 * Math.sqrt(fck) / 1000; // GPa
}

export function calcularTraco(input: ConcreteInput): ConcreteMixResult {
  const { fck, tipo_cimento, diametro_agregado, tipo_agregado, abatimento, classe_agressividade, fibra_tipo, fibra_dosagem } = input;

  // Resistência de dosagem
  const sigma = DESVIO_PADRAO['II'];
  const fcj = fck + 1.65 * sigma;

  // Resistência à tração (NBR 6118)
  const fct = 0.3 * Math.pow(fck, 2 / 3);
  const fct_flex = 1.5 * fct;           // MR ≈ 1.5 * fct
  const fct_sp   = 0.9 * fct;

  // Relação a/c
  let ac = acFromFck(fck, tipo_cimento);
  const ac_max = AC_MAX[classe_agressividade] ?? 0.60;
  ac = Math.min(ac, ac_max);

  // Água de amassamento
  const agua = consumoAgua(abatimento, diametro_agregado);

  // Consumo de cimento
  let cimento = consumoCimento(ac, agua);
  const c_min = C_MIN[classe_agressividade] ?? 280;
  cimento = Math.max(cimento, c_min);

  // Ajuste a/c real (após garantir consumo mínimo)
  const ac_real = agua / cimento;

  // Volumes:
  // V_cimento = cimento / densidade_cimento (dm³)
  // V_agua = agua (dm³, pois água: 1 kg = 1 L)
  // V_ar ≈ 2% (concreto adensado com vibrador)
  // V_pasta = V_cimento + V_agua + V_ar
  // V_agregados = 1000 - V_pasta

  const v_cimento = cimento / DENSIDADE_CIMENTO;
  const v_agua    = agua;           // 1 L = 1 dm³
  const v_ar      = 20;             // dm³ (2% de 1 m³ = 1000 dm³)
  const v_pasta   = v_cimento + v_agua + v_ar;
  const v_agregados = 1000 - v_pasta;

  // Divisão areia / brita: relação de volumes
  // Proporção típica: ~40-45% areia, 55-60% brita (varia com TMA)
  const frac_areia = diametro_agregado <= 12.5 ? 0.45 : diametro_agregado <= 19 ? 0.42 : 0.38;
  const v_areia = v_agregados * frac_areia;
  const v_brita = v_agregados * (1 - frac_areia);

  const densidade_brita = DENSIDADE_BRITA[tipo_agregado] ?? 2.65;
  const areia = v_areia * DENSIDADE_AREIA;
  const brita = v_brita * densidade_brita;

  // Adições para fibras
  let consumo_fibras: number | undefined;
  if (fibra_tipo !== 'none' && fibra_dosagem) {
    consumo_fibras = fibra_dosagem;
  }

  // Traço mássico: C : A : B (por kg, base cimento = 1)
  const t_areia = areia / cimento;
  const t_brita = brita / cimento;
  const traco_massico = `1 : ${t_areia.toFixed(2)} : ${t_brita.toFixed(2)} (a/c = ${ac_real.toFixed(2)})`;

  // Traço volumétrico (dm³/m³)
  const traco_volumetrico = `C:${Math.round(v_cimento)}L | A:${Math.round(v_areia)}L | B:${Math.round(v_brita)}L | Água:${Math.round(agua)}L`;

  const mr = fct_flex;

  return {
    fck,
    fcj: Math.round(fcj * 10) / 10,
    fct_flex: Math.round(fct_flex * 100) / 100,
    fct_sp: Math.round(fct_sp * 100) / 100,
    resistencia_trecagem: Math.round(mr * 100) / 100,
    relacao_agua_cimento: Math.round(ac_real * 1000) / 1000,
    consumo_cimento: Math.round(cimento),
    consumo_agua: Math.round(agua),
    consumo_areia: Math.round(areia),
    consumo_brita: Math.round(brita),
    consumo_fibras,
    traco_massico,
    traco_volumetrico,
    classe_resistencia: `C${fck}`,
    modulo_elasticidade: Math.round(moduloElasticidade(fck) * 10) / 10,
    slump: abatimento,
  };
}
