import { ConcreteInput, FiberResult, FiberPerformanceClass } from '../types';

/**
 * Dimensionamento estrutural de fibras para concreto de pavimento
 * Referências:
 *  - Aço: ABNT NBR 15530, ACI 544.4R, fib Model Code 2010
 *  - Sintética: ASTM C1609, TR34 (4th Ed.), ACI 360R
 *  - Classes de desempenho: fib MC2010 Seção 5.6
 */

// Classes de desempenho fib MC2010 (fR1 / fR3 mínimos em MPa)
const CLASSES_DESEMPENHO: FiberPerformanceClass[] = [
  { classe: '1a', fR1_min: 1.0, fR3_min: 0.7, descricao: 'Fissuração controlada, cargas leves' },
  { classe: '1b', fR1_min: 1.0, fR3_min: 1.0, descricao: 'Fissuração controlada, mantém capacidade' },
  { classe: '2a', fR1_min: 2.0, fR3_min: 1.4, descricao: 'Pisos industriais leves e médios' },
  { classe: '2b', fR1_min: 2.0, fR3_min: 2.0, descricao: 'Pisos industriais médios' },
  { classe: '3',  fR1_min: 3.0, fR3_min: 2.1, descricao: 'Pisos industriais pesados / Rodovias leves' },
  { classe: '4',  fR1_min: 4.0, fR3_min: 2.8, descricao: 'Rodovias e aeroportos (alta performance)' },
  { classe: '5',  fR1_min: 5.0, fR3_min: 3.5, descricao: 'Alto desempenho – grande rigidez residual' },
  { classe: '6',  fR1_min: 6.0, fR3_min: 4.2, descricao: 'Ultra-alto desempenho' },
];

// Determina classe de desempenho alcançada a partir de fR1 e fR3
function determinarClasse(fR1: number, fR3: number): string {
  let classe_alcancada = 'Abaixo de 1a';
  for (const cls of CLASSES_DESEMPENHO) {
    if (fR1 >= cls.fR1_min && fR3 >= cls.fR3_min) {
      classe_alcancada = cls.classe;
    }
  }
  return classe_alcancada;
}

// Dosagem mínima requerida por tipo de pavimento e espessura
function dosagem_minima_estrutural(
  fck: number,
  espessura: number,
  tipo_pavimento: string
): number {
  // Baseado em fib MC2010 e prática de mercado (Concreto & Construções)
  let base: number;
  if (tipo_pavimento === 'aeroporto') {
    base = fck >= 40 ? 35 : 30;
  } else if (tipo_pavimento === 'rodovia') {
    base = fck >= 35 ? 30 : 25;
  } else {
    // piso industrial
    base = fck >= 40 ? 25 : 20;
  }
  // Correção por espessura
  if (espessura > 35) base += 10;
  else if (espessura > 25) base += 5;
  return base;
}

// Fator de conformação da fibra (hook-end mais eficiente)
function fatorConformacao(comprimento: number, diametro: number): number {
  const esbeltez = comprimento / diametro;
  // Fibra hook-end: fator 1.0 (referência)
  // Fibra ondulada (crimped): fator 0.85
  // Fibra reta: fator 0.60
  // Aproximação pela esbeltez
  if (esbeltez >= 80) return 1.05; // alta esbeltez, hook-end longa
  if (esbeltez >= 60) return 1.0;
  if (esbeltez >= 40) return 0.85;
  return 0.70;
}

export function calcularFibras(
  input: ConcreteInput,
  espessura_placa_cm: number,
  tipo_pavimento: string = 'piso'
): FiberResult | undefined {
  if (input.fibra_tipo === 'none') return undefined;

  if (input.fibra_tipo === 'steel' || input.fibra_tipo === 'both') {
    return calcularFibraAco(input, espessura_placa_cm, tipo_pavimento);
  }
  if (input.fibra_tipo === 'synthetic') {
    return calcularFibraSintetica(input, espessura_placa_cm, tipo_pavimento);
  }
  return undefined;
}

function calcularFibraAco(
  input: ConcreteInput,
  espessura: number,
  tipo_pavimento: string
): FiberResult {
  const { fck, fibra_comprimento, fibra_diametro } = input;

  const L = fibra_comprimento ?? 50;   // mm
  const d = fibra_diametro ?? 1.0;     // mm
  const esbeltez = L / d;

  // Dosagem mínima estrutural
  const dosagem_min = dosagem_minima_estrutural(fck, espessura, tipo_pavimento);
  const dosagem = Math.max(input.fibra_dosagem ?? dosagem_min, dosagem_min);

  // Resistência à tração do aço da fibra (NBR 15530: fy ≥ 800 MPa para hook-end)
  const fy_fibra = 1100; // MPa (fibras de aço conformadas de alta resistência)

  // Volume de fibras (% em volume) – densidade aço = 7850 kg/m³
  const Vf = dosagem / 7850; // fração volumétrica (não multiplicado por 100)

  // Fator de conformação (hook-end vs crimped vs reta)
  const fc = fatorConformacao(L, d);

  // Resistência pós-fissuração – fib MC2010 modelo simplificado
  // fR1 = η_o × η_l × Vf × L/d × τ_fu
  // onde: η_o = 0.5 (orientação aleatória 3D), η_l = fator comprimento
  // τ_fu ≈ 0.5 * fck^0.5 (resistência de aderência fibra-matriz)
  const eta_o = 0.5; // fator orientação aleatória 3D
  const eta_l = esbeltez >= 60 ? 0.85 : esbeltez >= 40 ? 0.65 : 0.50;
  const tau_fu = 0.5 * Math.sqrt(fck); // MPa

  const fR1 = eta_o * eta_l * fc * Vf * esbeltez * tau_fu;
  const fR3 = fR1 * 0.70; // razão fR3/fR1 ≈ 0.7 (fibra hook-end padrão)

  // Determina classe de desempenho alcançada
  const classe_alcancada = determinarClasse(fR1, fR3);

  // Verifica se pode substituir armadura de temperatura
  // Condição TR34: fR1 ≥ 0.4 × fct_flex E dosagem ≥ 30 kg/m³
  const fct = 0.3 * Math.pow(fck, 2 / 3);
  const fct_flex = 1.5 * fct;
  const substitui_armadura = fR1 >= 0.4 * fct_flex && dosagem >= 30;

  const distribuicao = esbeltez >= 60
    ? 'Distribuição aleatória 3D – esbeltez adequada (≥60)'
    : 'Distribuição aleatória 3D – recomenda-se aumentar esbeltez para ≥60';

  const observacoes: string[] = [
    `Fibra de aço conformada: ${L}mm × ∅${d}mm | Esbeltez L/d = ${esbeltez.toFixed(0)}`,
    `Volume de fibras: Vf = ${(Vf * 100).toFixed(3)}% (${dosagem.toFixed(1)} kg/m³)`,
    `fR1 = ${fR1.toFixed(2)} MPa (resistência residual a 0,5mm abertura)`,
    `fR3 = ${fR3.toFixed(2)} MPa (resistência residual a 2,5mm abertura)`,
    `Classe de desempenho alcançada: ${classe_alcancada} (fib MC2010)`,
    `Resistência de aderência τ = ${tau_fu.toFixed(2)} MPa`,
    esbeltez < 60 ? '⚠ Esbeltez < 60 – eficiência reduzida (usar fibra mais esbelta)' : `✓ Esbeltez adequada (L/d = ${esbeltez.toFixed(0)})`,
    dosagem > 50 ? '⚠ Dosagem > 50 kg/m³ – verificar trabalhabilidade (slump reduzido)' : '',
    dosagem > 60 ? '⚠ Dosagem > 60 kg/m³ – uso de superplastificante obrigatório' : '',
    substitui_armadura
      ? `✓ Dosagem satisfaz critério TR34 – pode substituir armadura de temperatura`
      : `ℹ Dosagem insuficiente para substituição da armadura de temperatura (mín: 30 kg/m³ e fR1 ≥ ${(0.4 * fct_flex).toFixed(2)} MPa)`,
    `Normas: NBR 15530, fib MC2010 Seção 5.6, ACI 544.4R`,
    `Ensaio de controle: EN 14651 (viga entalhada) ou ASTM C1609 (viga sem entalhe)`,
  ].filter(Boolean);

  return {
    tipo: input.fibra_tipo,
    dosagem,
    comprimento: L,
    diametro: d,
    esbeltez,
    resistencia_trecagem: Math.round(fR1 * 100) / 100,
    fR1: Math.round(fR1 * 100) / 100,
    fR3: Math.round(fR3 * 100) / 100,
    classe_desempenho: classe_alcancada,
    substitui_armadura_temperatura: substitui_armadura,
    modelo_calculo: 'fib Model Code 2010 – FRC Classe de Desempenho (Seção 5.6)',
    distribuicao,
    observacoes,
  };
}

function calcularFibraSintetica(
  input: ConcreteInput,
  espessura: number,
  tipo_pavimento: string
): FiberResult {
  const L = input.fibra_comprimento ?? 54;   // mm
  const d = input.fibra_diametro ?? 0.9;     // mm (macro-fibra)
  const esbeltez = L / d;

  // Macro-fibras sintéticas estruturais (PP/PVA)
  // Densidade PP ≈ 910 kg/m³, PVA ≈ 1300 kg/m³
  const densidade_fibra = 910; // PP macro-fiber

  // Dosagem mínima estrutural (macro-sintética)
  let dosagem_min: number;
  if (tipo_pavimento === 'aeroporto') {
    dosagem_min = 8;
  } else if (tipo_pavimento === 'rodovia') {
    dosagem_min = 6;
  } else {
    dosagem_min = espessura > 25 ? 6 : 4;
  }
  const dosagem = Math.max(input.fibra_dosagem ?? dosagem_min, dosagem_min);

  const Vf = dosagem / densidade_fibra;

  // Resistência pós-fissuração para macro-sintética (ASTM C1609 / TR34)
  // Macro-PP de alta tenacidade: fR1 ≈ 0.15 × sqrt(fck) × Vf × L/d × 0.4
  // Valor conservador pois sintética tem menor módulo que aço
  const fR1 = 0.15 * Math.sqrt(input.fck) * Vf * (esbeltez / 60) * 100;
  const fR3 = fR1 * 0.65;

  const classe_alcancada = determinarClasse(fR1, fR3);

  const fct = 0.3 * Math.pow(input.fck, 2 / 3);
  const fct_flex = 1.5 * fct;
  const substitui_armadura = fR1 >= 0.4 * fct_flex && dosagem >= 5;

  const observacoes: string[] = [
    `Macro-fibra sintética PP: ${L}mm × ∅${d}mm | Esbeltez = ${esbeltez.toFixed(0)}`,
    `Dosagem: ${dosagem.toFixed(1)} kg/m³ | Vf = ${(Vf * 100).toFixed(3)}%`,
    `fR1 estimado = ${fR1.toFixed(2)} MPa | fR3 estimado = ${fR3.toFixed(2)} MPa`,
    `Classe de desempenho estimada: ${classe_alcancada} (fib MC2010)`,
    '⚠ Para uso estrutural: confirmar por ensaio ASTM C1609 ou EN 14651',
    'Resistência ao fogo: excelente (isento de fusão por fusão de PP)',
    'Controle de fissuração plástica superior ao aço',
    substitui_armadura
      ? '✓ Pode substituir armadura de temperatura (confirmar por dosagem de obra)'
      : 'ℹ Não substitui armadura de temperatura com esta dosagem',
    `Custo relativo: ${dosagem <= 4 ? 'similar à fibra de aço (kg base)' : 'verificar com fornecedor'}`,
    'Normas: ASTM C1116 Tipo III, TR34 4ª Ed., ACI 360R-10',
  ].filter(Boolean);

  return {
    tipo: input.fibra_tipo,
    dosagem,
    comprimento: L,
    diametro: d,
    esbeltez,
    resistencia_trecagem: Math.round(fR1 * 100) / 100,
    fR1: Math.round(fR1 * 100) / 100,
    fR3: Math.round(fR3 * 100) / 100,
    classe_desempenho: classe_alcancada,
    substitui_armadura_temperatura: substitui_armadura,
    modelo_calculo: 'ASTM C1609 / TR34 4ª Ed. – Macro-fibra sintética estrutural',
    distribuicao: 'Distribuição aleatória 3D (fibra sintética macro)',
    observacoes,
  };
}

export { CLASSES_DESEMPENHO };
