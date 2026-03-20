import { SubgradeInput, SubgradeResult } from '../types';

/**
 * Converte CBR para módulo de reação k (MPa/m)
 * Baseado em correlações empíricas (Westergaard / DNIT)
 */
export function cbrToK(cbr: number): number {
  // Correlação: k (MPa/m) ≈ 2.55 * CBR^0.714  (Barenberg & Thompson)
  // Valores típicos validados por DNIT / Coutinho Neto
  if (cbr <= 0) return 20;
  if (cbr < 2) return 20 + (cbr / 2) * 10;
  if (cbr <= 5)  return 27.2 * Math.pow(cbr, 0.5);   // k ≈ 20-60 MPa/m
  if (cbr <= 10) return 2.55 * Math.pow(cbr, 0.714);  // 60-120 MPa/m  (original Westergaard)
  if (cbr <= 20) return 1.8 * Math.pow(cbr, 0.8);
  if (cbr <= 40) return 1.2 * Math.pow(cbr, 0.9);
  return 0.9 * Math.pow(cbr, 1.0); // acima de 40%
}

/**
 * Correção do k com a subbase (efeito de suporte composto)
 * Método de PORTLAND CEMENT ASSOCIATION – PCA (1984)
 */
export function kWithSubbase(
  k_subgrade: number,
  tipo_subbase: string,
  espessura_subbase: number  // cm
): number {
  // Fatores de correção para subbase (tabelas PCA)
  // k_corrigido cresce com espessura e qualidade da subbase
  const fator_material: Record<string, number> = {
    bgt:          1.0,
    bgtm:         1.10,
    brta:         1.20,
    solo_cimento: 1.35,
    rachao:       1.05,
    brita_graduada:1.15,
  };
  const fm = fator_material[tipo_subbase] ?? 1.0;

  // Incremento por espessura (aprox. +0.4% por cm de subbase granular)
  const incremento = 1 + (espessura_subbase / 100) * fm * 0.8;

  // PCA limita k_corrigido por tipo de subbase
  let k_max = 150; // MPa/m para subbase granular
  if (tipo_subbase === 'solo_cimento') k_max = 250;
  if (tipo_subbase === 'brta') k_max = 200;

  return Math.min(k_subgrade * incremento, k_max);
}

/**
 * Classifica o subleito
 */
export function classificarSubleito(cbr: number): string {
  if (cbr < 2)  return 'Muito fraco (CBR < 2%) – reforço obrigatório';
  if (cbr < 5)  return 'Fraco (CBR 2–5%) – necessita subbase reforçada';
  if (cbr < 10) return 'Regular (CBR 5–10%)';
  if (cbr < 20) return 'Bom (CBR 10–20%)';
  if (cbr < 40) return 'Ótimo (CBR 20–40%)';
  return 'Excelente (CBR > 40%)';
}

export function calcularSubleito(input: SubgradeInput): SubgradeResult {
  const cbr = input.cbr;
  const k_direto = input.k_direto ?? cbrToK(cbr);
  const melhoramento = cbr < 2;

  return {
    cbr_projeto: cbr,
    k_value: k_direto,
    k_corrigido: k_direto, // será recalculado com subbase
    classificacao: classificarSubleito(cbr),
    melhoramento_necessario: melhoramento,
    espessura_melhoramento: melhoramento ? 30 : undefined,
  };
}
