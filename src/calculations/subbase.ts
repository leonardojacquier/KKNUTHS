import { SubbaseBaseInput, LayerResult } from '../types';
import { cbrToK, kWithSubbase } from './subgrade';

const MATERIAL_NAMES: Record<string, string> = {
  bgt:           'BGT – Brita Graduada Tratada',
  bgtm:          'BGTM – Brita Graduada Tratada Mista',
  brta:           'BRTA – Brita Run of Quarry Tratada',
  solo_cimento:  'Solo-Cimento',
  rachao:        'Rachão (Pedra Irregular)',
  brita_graduada:'Brita Graduada Simples',
};

const CBR_DEFAULTS: Record<string, number> = {
  bgt:           80,
  bgtm:          60,
  brta:          80,
  solo_cimento:  100,  // resistência mecânica, não CBR real
  rachao:        40,
  brita_graduada:80,
};

/**
 * Determina espessura mínima da subbase
 * Baseado no CBR do subleito (método DNIT / PCA)
 */
export function espessuraMinSubbase(cbr_subgrade: number, tipo: string): number {
  // Espessura mínima recomendada (cm)
  if (cbr_subgrade < 2)  return 30;
  if (cbr_subgrade < 5)  return 20;
  if (cbr_subgrade < 10) return 15;
  // Para pavimento aero e piso pesado sempre recomenda-se pelo menos 15 cm
  return tipo === 'solo_cimento' ? 12 : 15;
}

/**
 * Determina espessura mínima da base
 * Depende do tipo e do tráfego
 */
export function espessuraMinBase(tipo: string, n_esal?: number): number {
  const n = n_esal ?? 1e6;
  if (tipo === 'solo_cimento') {
    return n > 1e7 ? 20 : 15;
  }
  if (tipo === 'bgtm' || tipo === 'brta') {
    return n > 5e7 ? 25 : 20;
  }
  return 15;
}

export function calcularSubbase(
  input: SubbaseBaseInput,
  cbr_subgrade: number,
  k_subgrade: number,
  tipo_pavimento: string
): { subbase?: LayerResult; base?: LayerResult; k_final: number } {
  let k_atual = k_subgrade;

  let subbase: LayerResult | undefined;
  let base: LayerResult | undefined;

  if (input.incluir_subbase && input.tipo_subbase) {
    const tipo = input.tipo_subbase;
    const cbr_sb = input.cbr_subbase ?? CBR_DEFAULTS[tipo] ?? 60;
    let esp = input.espessura_subbase ?? 0;
    if (esp <= 0) {
      esp = espessuraMinSubbase(cbr_subgrade, tipo);
      // arredondar para múltiplo de 5
      esp = Math.ceil(esp / 5) * 5;
    }

    k_atual = kWithSubbase(k_atual, tipo, esp);

    subbase = {
      material: MATERIAL_NAMES[tipo] ?? tipo,
      espessura: esp,
      cbr: cbr_sb,
      k_contribuido: k_atual,
      volume_por_m2: esp / 100,
    };
  }

  if (input.incluir_base && input.tipo_base) {
    const tipo = input.tipo_base;
    const cbr_base = input.cbr_base ?? CBR_DEFAULTS[tipo] ?? 80;
    let esp = input.espessura_base ?? 0;
    if (esp <= 0) {
      esp = espessuraMinBase(tipo, undefined);
      esp = Math.ceil(esp / 5) * 5;
    }

    k_atual = kWithSubbase(k_atual, tipo, esp);

    base = {
      material: MATERIAL_NAMES[tipo] ?? tipo,
      espessura: esp,
      cbr: cbr_base,
      k_contribuido: k_atual,
      volume_por_m2: esp / 100,
    };
  }

  return { subbase, base, k_final: k_atual };
}
