import { ProjectInput, SlabResult } from '../types';

const E_CONCRETO = 30e3;   // MPa (módulo de elasticidade padrão)
const NU = 0.15;           // coeficiente de Poisson do concreto

/**
 * Calcula a resistência à flexo-tração do concreto
 * NBR 6118: fct,f = 0.7 * fct (onde fct = 0.3 * fck^(2/3))
 * Valor de projeto: fctk,inf = 0.7 * 0.3 * fck^(2/3)
 * Para pavimentos usa-se: Mr = k * fck^0.5
 */
export function calcularMR(fck: number): number {
  // Módulo de Ruptura (MR) – resistência à flexo-tração
  // Mr ≈ 0.45 * sqrt(fck)  (ACI 318) ou aproximação brasileira
  // Adotamos: Mr = 0.6 * fck^(2/3) / gammaF (mais conservador para pavimentos)
  return 0.6 * Math.pow(fck, 2 / 3);
}

/**
 * Raio de rigidez relativa (Westergaard)
 * l = (E * h³ / (12 * (1 - nu²) * k))^(1/4)
 * h em metros, k em MPa/m, retorna l em metros
 */
export function raioRigidez(h_m: number, k_MPa_m: number): number {
  return Math.pow((E_CONCRETO * 1e6 * Math.pow(h_m, 3)) / (12 * (1 - NU * NU) * k_MPa_m * 1e6), 0.25);
}

// ============================================================
// RODOVIA (PUC) – Método DNIT baseado em Westergaard (1939)
// Tensão crítica na borda (canto) por carga no canto/borda
// ============================================================

/**
 * Dimensionamento para rodovia (DNIT/PCA)
 * Referência: DNIT 005/2003-PRO, Método PCA (1984)
 * Parâmetro de projeto: N10^6 eixos equivalentes
 */
export function dimensionarRodovia(
  fck: number,
  k: number,         // MPa/m
  N: number,         // x10^6 eixos equivalentes padrão (P = 80 kN)
  mr: number
): SlabResult {
  // Tensão admissível = MR / fator fadiga
  // Fator de fadiga em função de N (PCA 1984, tabela)
  let fs: number;
  if (N < 0.1e6)     fs = 1.30;
  else if (N < 1e6)  fs = 1.35;
  else if (N < 10e6) fs = 1.50;
  else if (N < 50e6) fs = 1.65;
  else               fs = 1.80;

  const tensao_adm = mr / fs;

  // Carga padrão de projeto: 80 kN por eixo simples => P = 40 kN por roda
  const P = 40e3; // N
  // Área de contato circular: ac = P / (0.8 * p_pneu)
  // pressão pneu = 0.56 MPa (eixo padrão DNIT)
  const p_pneu = 0.56e6; // Pa
  const a = Math.sqrt((P / p_pneu) / Math.PI); // raio de contato (m)

  // Iteração de h (espessura da placa)
  let h = 0.15; // início 15 cm
  let tensao_calc = 999;
  let iteracoes = 0;

  while (tensao_calc > tensao_adm && iteracoes < 200) {
    const l = raioRigidez(h, k);
    const b = a < 1.724 * h
      ? Math.sqrt(1.6 * a * a + h * h) - 0.675 * h
      : a;

    // Tensão de borda (interior – fórmula Westergaard 1939, revisada Kelley)
    tensao_calc = (0.316 * P) / (h * h) * (4 * Math.log10(l / b) + 1.069);
    // Convert to MPa
    tensao_calc = tensao_calc / 1e6;

    if (tensao_calc > tensao_adm) h += 0.005;
    iteracoes++;
  }

  const espessura_calc = h * 100; // metros → cm
  const espessura_final = arredondarEspessura(espessura_calc);
  const l_final = raioRigidez(h, k);

  return {
    espessura: espessura_final,
    espessura_calculada: Math.round(espessura_calc * 10) / 10,
    tensao_critica: Math.round(tensao_calc * 1000) / 1000,
    tensao_admissivel: Math.round(tensao_adm * 1000) / 1000,
    fator_seguranca: Math.round((tensao_adm / tensao_calc) * 100) / 100,
    raio_rigidez: Math.round(l_final * 100) / 100,
    metodo: 'DNIT – Westergaard / PCA 1984',
    equacao: 'σ = 0.316·P/h² · (4·log(l/b) + 1.069)',
  };
}

// ============================================================
// AEROPORTO – Método FAA (AC 150/5370-10)
// ============================================================

/**
 * Dimensionamento para aeroporto (FAA AC 150/5320-6)
 * Baseado na carga por roda e CBR do subleito
 */
export function dimensionarAeroporto(
  fck: number,
  k: number,       // MPa/m
  carga_roda: number,   // kN
  pressao_pneu: number, // MPa
  operacoes_anuais: number,
  periodo: number,  // anos
  mr: number
): SlabResult {
  // Eixos de projeto em pistas de aeroporto
  const N_total = operacoes_anuais * periodo * 2; // decolagem + pouso

  // Fator de fadiga para aeroportos (mais conservador)
  let fs: number;
  if (N_total < 1000)    fs = 1.25;
  else if (N_total < 5000) fs = 1.35;
  else if (N_total < 50000) fs = 1.50;
  else                     fs = 1.65;

  const tensao_adm = mr / fs;

  const P = carga_roda * 1e3; // N
  const a = Math.sqrt((P / (pressao_pneu * 1e6)) / Math.PI);

  let h = 0.20; // mínimo 20 cm para aeroportos
  let tensao_calc = 999;
  let iteracoes = 0;

  while (tensao_calc > tensao_adm && iteracoes < 200) {
    const l = raioRigidez(h, k);
    const b = a < 1.724 * h
      ? Math.sqrt(1.6 * a * a + h * h) - 0.675 * h
      : a;

    // Fórmula de borda (Westergaard) – aeronaves normalmente passam pela borda da pista
    tensao_calc = (0.316 * P) / (h * h) * (4 * Math.log10(l / b) + 1.069);
    tensao_calc = tensao_calc / 1e6;

    if (tensao_calc > tensao_adm) h += 0.01;
    iteracoes++;
  }

  const espessura_calc = h * 100;
  const espessura_final = arredondarEspessura(Math.max(espessura_calc, 25)); // mín 25 cm para aeroportos
  const l_final = raioRigidez(espessura_final / 100, k);

  return {
    espessura: espessura_final,
    espessura_calculada: Math.round(espessura_calc * 10) / 10,
    tensao_critica: Math.round(tensao_calc * 1000) / 1000,
    tensao_admissivel: Math.round(tensao_adm * 1000) / 1000,
    fator_seguranca: Math.round((tensao_adm / tensao_calc) * 100) / 100,
    raio_rigidez: Math.round(l_final * 100) / 100,
    metodo: 'FAA AC 150/5320-6 – Westergaard',
    equacao: 'σ = 0.316·P/h² · (4·log(l/b) + 1.069)',
  };
}

// ============================================================
// PISO INDUSTRIAL – Método TR34 / ACI 360R
// ============================================================

/**
 * Dimensionamento de piso industrial
 * Referências: Concrete Society TR34 (4ª ed.), ACI 360R
 */
export function dimensionarPiso(
  fck: number,
  k: number,       // MPa/m
  carga_conc: number,    // kN (carga concentrada por ponto)
  carga_dist: number,    // kN/m² (carga distribuída)
  carga_empilhadeira: number, // kN (por roda)
  distancia_rodas: number,    // m
  mr: number
): SlabResult {
  const tensao_adm = mr / 1.4; // FS = 1.4 para pisos industriais (TR34)

  // Carga máxima governante
  const P_max = Math.max(carga_conc, carga_empilhadeira) * 1e3; // N
  const pressao_pneu_empilhadeira = 0.8e6; // Pa (empilhadeiras industriais típicas)
  const a = Math.sqrt((P_max / pressao_pneu_empilhadeira) / Math.PI);

  let h = 0.10;
  let tensao_calc = 999;
  let iteracoes = 0;

  while (tensao_calc > tensao_adm && iteracoes < 200) {
    const l = raioRigidez(h, k);
    const b = a < 1.724 * h
      ? Math.sqrt(1.6 * a * a + h * h) - 0.675 * h
      : a;

    // Tensão interior (piso – carga no interior da placa, Westergaard)
    // σ_interior = (0.316 * P / h²) * (4*log(l/b) + 1.069) corrigido por posição
    // Para interior: menor que borda por ~30%
    tensao_calc = 0.70 * (0.316 * P_max) / (h * h) * (4 * Math.log10(l / b) + 1.069);
    tensao_calc = tensao_calc / 1e6;

    // Verificar também carga distribuída (placa semi-infinita)
    const tensao_dist = (3 * carga_dist * 1e3 * (1 + NU)) / (4 * Math.PI * k * 1e6 * h * h);
    tensao_calc = Math.max(tensao_calc, tensao_dist / 1e3);

    if (tensao_calc > tensao_adm) h += 0.005;
    iteracoes++;
  }

  const espessura_calc = h * 100;
  const espessura_final = arredondarEspessura(Math.max(espessura_calc, 12)); // mín 12 cm para pisos
  const l_final = raioRigidez(espessura_final / 100, k);

  return {
    espessura: espessura_final,
    espessura_calculada: Math.round(espessura_calc * 10) / 10,
    tensao_critica: Math.round(tensao_calc * 1000) / 1000,
    tensao_admissivel: Math.round(tensao_adm * 1000) / 1000,
    fator_seguranca: Math.round((tensao_adm / tensao_calc) * 100) / 100,
    raio_rigidez: Math.round(l_final * 100) / 100,
    metodo: 'TR34 / ACI 360R – Westergaard',
    equacao: 'σ = 0.70 · (0.316·P/h²) · (4·log(l/b) + 1.069)',
  };
}

/**
 * Arredonda para espessuras comerciais (múltiplos de 2.5 cm)
 */
function arredondarEspessura(h_calc: number): number {
  // Série comercial: 10, 12, 14, 15, 16, 18, 20, 22, 24, 25, 28, 30, 33, 35, 38, 40...
  const serie = [10, 12, 14, 15, 16, 18, 20, 22, 24, 25, 28, 30, 33, 35, 38, 40, 42, 45, 48, 50, 55, 60];
  for (const v of serie) {
    if (v >= h_calc) return v;
  }
  return Math.ceil(h_calc / 5) * 5;
}
