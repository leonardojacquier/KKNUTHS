import { ConcreteInput, FiberResult } from '../types';

/**
 * Dimensionamento de fibras para concreto de pavimento
 * Referências:
 *  - Aço: ABNT NBR 15530, ACI 544, fib Model Code 2010
 *  - Sintética: ASTM C1609, TR34
 */

export function calcularFibras(input: ConcreteInput, espessura_placa_cm: number): FiberResult | undefined {
  if (input.fibra_tipo === 'none') return undefined;

  const tipo = input.fibra_tipo;
  const fck = input.fck;

  if (tipo === 'steel' || tipo === 'both') {
    return calcularFibraAco(input, espessura_placa_cm);
  }
  if (tipo === 'synthetic') {
    return calcularFibraSintetica(input, espessura_placa_cm);
  }
  return undefined;
}

function calcularFibraAco(input: ConcreteInput, espessura: number): FiberResult {
  const { fck, fibra_comprimento, fibra_diametro } = input;

  const L  = fibra_comprimento ?? 50;   // mm
  const d  = fibra_diametro ?? 1.0;     // mm
  const esbeltez = L / d;

  // Dosagem mínima para pavimentos (NBR 15530 / fib MC2010)
  // Pisos industriais pesados: 20-40 kg/m³
  // Pavimentos de rodovia: 30-45 kg/m³
  // Aeroportos: 35-50 kg/m³
  let dosagem_min: number;
  if (fck >= 40) dosagem_min = 30;
  else if (fck >= 30) dosagem_min = 25;
  else dosagem_min = 20;

  // Fator de correção pela espessura
  if (espessura > 25) dosagem_min += 5;
  if (espessura > 35) dosagem_min += 5;

  const dosagem = input.fibra_dosagem ?? dosagem_min;

  // Resistência à tração do aço da fibra (MPa) – mínima NBR 15530
  const fy_fibra = 800; // MPa (fibras de aço conformadas)

  // Eficiência volumétrica (% volume)
  const Vf = dosagem / 7850 * 100; // 7850 kg/m³ = densidade do aço

  // Resistência pós-fissuração (fib MC2010 – modelo simplificado)
  // fR1 ≈ 0.3 * sqrt(fck) * Vf * (L/d) * 0.25  (MPa)
  const fR1 = 0.3 * Math.sqrt(fck) * Vf * (esbeltez / 100);
  const fR3 = 0.7 * fR1; // resistência residual a 3 mm abertura de fissura

  const distribuicao = esbeltez >= 60
    ? 'Distribuição aleatória 3D – esbeltez adequada (≥60)'
    : 'Distribuição aleatória 3D – considerar aumentar esbeltez';

  const observacoes: string[] = [
    `Fibra: ${L}mm × ∅${d}mm – esbeltez L/d = ${esbeltez.toFixed(0)}`,
    `Volume de fibras: ${Vf.toFixed(2)}% (${dosagem} kg/m³)`,
    `Resistência pós-fissuração fR1 ≈ ${fR1.toFixed(2)} MPa`,
    `Resistência residual fR3 ≈ ${fR3.toFixed(2)} MPa`,
    esbeltez < 60 ? 'ATENÇÃO: esbeltez < 60 – eficiência reduzida' : '',
    dosagem > 50 ? 'ATENÇÃO: dosagem > 50 kg/m³ – verificar trabalhabilidade' : '',
  ].filter(Boolean);

  return {
    tipo: input.fibra_tipo,
    dosagem,
    comprimento: L,
    diametro: d,
    esbeltez,
    resistencia_trecagem: Math.round(fR1 * 100) / 100,
    modelo_calculo: 'fib Model Code 2010 – FRC Classe de Desempenho',
    distribuicao,
    observacoes,
  };
}

function calcularFibraSintetica(input: ConcreteInput, espessura: number): FiberResult {
  const L  = input.fibra_comprimento ?? 54;   // mm
  const d  = input.fibra_diametro ?? 0.9;     // mm (monofilamento macro)
  const esbeltez = L / d;

  // Dosagem mínima para macro-fibras sintéticas
  // Equivalência prática: 4-8 kg/m³ macro-fibra ≈ 20-30 kg/m³ fibra de aço
  let dosagem_min: number;
  if (espessura > 25) dosagem_min = 6;
  else dosagem_min = 4;

  const dosagem = input.fibra_dosagem ?? dosagem_min;

  // Volume de fibras (densidade PP ≈ 900 kg/m³)
  const Vf = dosagem / 900 * 100;

  const observacoes: string[] = [
    `Fibra sintética (PP/PVA): ${L}mm × ∅${d}mm – esbeltez ${esbeltez.toFixed(0)}`,
    `Dosagem: ${dosagem} kg/m³ (Vf = ${Vf.toFixed(2)}%)`,
    'Resistência ao fogo melhorada',
    'Controle de fissuração plástica – excelente',
    'Para uso estrutural, verificar classificação ASTM C1609 (f150,0.5 / f150,3.0)',
    dosagem < 3 ? 'ATENÇÃO: dosagem < 3 kg/m³ – eficácia estrutural limitada' : '',
  ].filter(Boolean);

  return {
    tipo: 'synthetic',
    dosagem,
    comprimento: L,
    diametro: d,
    esbeltez,
    modelo_calculo: 'ASTM C1609 / TR34 – Macro-fibra sintética',
    distribuicao: 'Distribuição aleatória 3D (fibra sintética)',
    observacoes,
  };
}
