import { AdditiveInput, AdditiveResult, AdditiveEffect } from '../types';

/**
 * Cálculo dos efeitos de aditivos químicos e adições minerais
 * Referências: ABNT NBR 11768, ASTM C494, EN 934-2, NBR 12653 (pozolanas)
 */

interface AdditiveEffectParams {
  nome: string;
  tipo_norma: string;
  dosagem_pct_cimento: number;
  reducao_agua_pct: number;
  aumento_resistencia_pct: number;
  obs: string[];
}

export function calcularAditivos(
  aditivos: AdditiveInput,
  consumo_cimento_base: number, // kg/m³ antes dos aditivos
  agua_base: number,            // L/m³
  fck_base: number
): AdditiveResult {
  const efeitos: AdditiveEffect[] = [];
  let reducao_agua_total = 0;

  // 1. Plastificante (ASTM C494 Tipo A / NBR 11768 Tipo P)
  if (aditivos.plastificante) {
    const dos = aditivos.plastificante_dosagem ?? 0.3; // % cimento
    const red_agua = 5 + dos * 6; // 5-8% redução típica
    const red_agua_clamped = Math.min(red_agua, 10);
    reducao_agua_total += red_agua_clamped;
    efeitos.push({
      nome: 'Plastificante',
      tipo: 'ASTM C494 Tipo A / NBR 11768 Tipo P',
      dosagem: consumo_cimento_base * dos / 100,
      reducao_agua_pct: red_agua_clamped,
      aumento_resistencia_pct: red_agua_clamped * 0.6, // +0.6% resist por 1% água reduzida
      observacoes: [
        `Dosagem: ${dos}% sobre massa de cimento = ${(consumo_cimento_base * dos / 100).toFixed(1)} kg/m³`,
        `Redução de água: ${red_agua_clamped.toFixed(1)}%`,
        'Mantém consistência ou reduz relação a/c',
        'Prazo de trabalhabilidade: 1-2h (verificar especificação do produto)',
      ],
    });
  }

  // 2. Superplastificante (ASTM C494 Tipo F / NBR 11768 Tipo SP)
  if (aditivos.superplastificante) {
    const dos = aditivos.superplastificante_dosagem ?? 1.0; // % cimento
    const red_agua = 12 + dos * 8; // 12-30% redução típica
    const red_agua_clamped = Math.min(red_agua, 35);
    reducao_agua_total += red_agua_clamped;
    efeitos.push({
      nome: 'Superplastificante (HRWR)',
      tipo: 'ASTM C494 Tipo F/G / NBR 11768 Tipo SP',
      dosagem: consumo_cimento_base * dos / 100,
      reducao_agua_pct: red_agua_clamped,
      aumento_resistencia_pct: red_agua_clamped * 0.7,
      observacoes: [
        `Dosagem: ${dos}% sobre massa de cimento = ${(consumo_cimento_base * dos / 100).toFixed(1)} kg/m³`,
        `Redução de água: ${red_agua_clamped.toFixed(1)}%`,
        'Permite concreto de alto desempenho e alto fluxo',
        'Atenção à perda de consistência (slump loss) – verificar compatibilidade cimento-aditivo',
        dos > 1.5 ? 'ATENÇÃO: Dosagem elevada – risco de retardo de pega e segregação' : '',
      ].filter(Boolean),
    });
  }

  // 3. Retardador (ASTM C494 Tipo B/D)
  if (aditivos.retardador) {
    const dos = aditivos.retardador_dosagem ?? 0.3;
    efeitos.push({
      nome: 'Retardador de Pega',
      tipo: 'ASTM C494 Tipo B (redutor-retardador: Tipo D)',
      dosagem: consumo_cimento_base * dos / 100,
      reducao_agua_pct: 0,
      aumento_resistencia_pct: 0,
      observacoes: [
        `Dosagem: ${dos}% sobre massa de cimento`,
        'Indicado para concretagem em clima quente (T > 30°C)',
        'Permite maior prazo de trabalhabilidade (2-4h adicionais)',
        'Retardo de início de pega: 1-3h extra (conforme dosagem)',
        'Resistência final aos 28 dias não é afetada significativamente',
      ],
    });
  }

  // 4. Acelerador de pega (ASTM C494 Tipo C/E)
  if (aditivos.acelerador) {
    const dos = aditivos.acelerador_dosagem ?? 1.0;
    efeitos.push({
      nome: 'Acelerador de Pega',
      tipo: 'ASTM C494 Tipo C (acelerador) / Tipo E (red.-acelerador)',
      dosagem: consumo_cimento_base * dos / 100,
      reducao_agua_pct: 0,
      aumento_resistencia_pct: 15, // resistência inicial maior
      observacoes: [
        `Dosagem: ${dos}% sobre massa de cimento`,
        'Indicado para clima frio (T < 10°C) ou liberação rápida de forma',
        'Resistência a 24h pode ser 50-100% maior que concreto sem aditivo',
        'Verificar compatibilidade com cimento (especialmente CP-V-ARI)',
        'Evitar uso com retardador simultâneo',
      ],
    });
  }

  // 5. Incorporador de Ar (ASTM C260 / NBR 11768)
  if (aditivos.incorporador_ar) {
    const dos = aditivos.incorporador_ar_dosagem ?? 0.1;
    const teor_ar = 3 + dos * 20; // estimativa de teor de ar (%)
    const teor_clamped = Math.min(teor_ar, 7);
    const perda_resist = teor_clamped * 4; // ~4-5% por 1% ar incorporado
    efeitos.push({
      nome: 'Incorporador de Ar',
      tipo: 'ASTM C260 / NBR 11768 Tipo IAR',
      dosagem: consumo_cimento_base * dos / 100,
      reducao_agua_pct: 3, // pequena redução de água
      aumento_resistencia_pct: -perda_resist, // negativo = redução
      observacoes: [
        `Dosagem: ${dos}% sobre massa de cimento`,
        `Teor de ar estimado: ${teor_clamped.toFixed(1)}% (verificar por pressão ABNT NBR 9833)`,
        `Perda de resistência estimada: ${perda_resist.toFixed(1)}% (compensar reduzindo a/c)`,
        'Melhora significativamente resistência ao gelo-degelo (pavimentos em regiões frias)',
        'Aumenta durabilidade frente a sais de degelo (aeroportos)',
        'Recomendado para regiões Sul do Brasil e áreas de altitude',
      ],
    });
  }

  // 6. Sílica Ativa (NBR 13956 / ASTM C1240)
  if (aditivos.silica_ativa) {
    const teor = aditivos.silica_ativa_teor ?? 8; // % substituição cimento
    const red_agua = teor * 0.8; // sílica aumenta demanda de água sem SP
    reducao_agua_total -= red_agua; // aumenta demanda de água
    const aumento_resist = teor * 2.5; // ~2-3% por % silica (com sp)
    efeitos.push({
      nome: 'Sílica Ativa (Microssílica)',
      tipo: 'NBR 13956 / ASTM C1240 – Adição tipo IV',
      dosagem: consumo_cimento_base * teor / 100,
      reducao_agua_pct: -red_agua, // aumenta demanda de água
      aumento_resistencia_pct: aumento_resist,
      observacoes: [
        `Teor: ${teor}% de substituição ao cimento`,
        `Consumo: ${(consumo_cimento_base * teor / 100).toFixed(0)} kg/m³`,
        `Aumento de resistência estimado: +${aumento_resist.toFixed(0)}%`,
        'Recomendado uso conjunto com superplastificante',
        'Reduz significativamente permeabilidade (cl⁻, CO₂)',
        'Ideal para ambientes agressivos (Classe III e IV NBR 6118)',
        'Aumenta resistência à abrasão – excelente para pisos industriais',
      ],
    });
  }

  // 7. Cinza Volante – Fly Ash (NBR 12653 Tipo C / ASTM C618)
  if (aditivos.cinza_volante) {
    const teor = aditivos.cinza_volante_teor ?? 20; // % substituição
    const red_agua = teor * 0.4; // CF reduz levemente demanda de água
    reducao_agua_total += red_agua;
    const delta_resist = teor > 25 ? -(teor - 25) * 0.5 : teor * 0.3; // pequena variação
    efeitos.push({
      nome: 'Cinza Volante (Fly Ash)',
      tipo: 'NBR 12653 Tipo C / ASTM C618 Tipo F',
      dosagem: consumo_cimento_base * teor / 100,
      reducao_agua_pct: red_agua,
      aumento_resistencia_pct: delta_resist,
      observacoes: [
        `Teor: ${teor}% de substituição ao cimento`,
        `Consumo: ${(consumo_cimento_base * teor / 100).toFixed(0)} kg/m³`,
        'Retarda desenvolvimento de resistência – cuidado no desforma precoce',
        'Calor de hidratação reduzido – ótimo para concretagens em massa',
        'Melhora trabalhabilidade e reduz retração',
        'Resistência final (90 dias) pode superar referência sem cinza',
        teor > 30 ? 'ATENÇÃO: Teor > 30% requer aprovação do projetista e ensaios de dosagem' : '',
      ].filter(Boolean),
    });
  }

  // 8. Escória de Alto Forno – GGBS (NBR 12989 / ASTM C989)
  if (aditivos.escoria) {
    const teor = aditivos.escoria_teor ?? 40; // % substituição
    const red_agua = teor * 0.2;
    reducao_agua_total += red_agua;
    efeitos.push({
      nome: 'Escória de Alto Forno Granulada (GGBS)',
      tipo: 'NBR 12989 / ASTM C989 – Adição tipo II',
      dosagem: consumo_cimento_base * teor / 100,
      reducao_agua_pct: red_agua,
      aumento_resistencia_pct: teor * 0.15,
      observacoes: [
        `Teor: ${teor}% de substituição ao cimento`,
        `Consumo: ${(consumo_cimento_base * teor / 100).toFixed(0)} kg/m³`,
        'Excelente resistência a sulfatos e reação álcali-sílica (RAS)',
        'Calor de hidratação muito reduzido',
        'Desenvolvimento lento de resistência – curar por período maior (≥14 dias)',
        'Ótimo para ambientes com ataque de sulfatos (solos e águas agressivas)',
      ],
    });
  }

  // 9. Micro-fibra de Polipropileno anti-fissuração (0.9 kg/m³)
  if (aditivos.micro_fibra_pp) {
    efeitos.push({
      nome: 'Micro-fibra PP (anti-fissuração plástica)',
      tipo: 'ASTM C1116 Tipo III / NBR 15530',
      dosagem: 0.9,
      reducao_agua_pct: 0,
      aumento_resistencia_pct: 0,
      observacoes: [
        'Dosagem padrão: 0,9 kg/m³ (600 milhões fibras/m³)',
        'Controle de fissuração plástica (retração plástica nas primeiras horas)',
        'Não é substituta de armadura estrutural',
        'Fibra monofilamento PP: ∅0.018mm × 18mm comprimento típico',
        'Uso cumulativo com fibras estruturais de aço ou sintéticas',
        'Melhora resistência ao impacto em idades precoces',
      ],
    });
  }

  // Calcula água efetiva após aditivos
  const reducao_agua_real = Math.min(reducao_agua_total, 35); // máx 35% redução
  const agua_efetiva = agua_base * (1 - reducao_agua_real / 100);

  // Consumo total de aditivos químicos (líquidos)
  const consumo_quimicos = efeitos
    .filter(e => !['Sílica Ativa (Microssílica)', 'Cinza Volante (Fly Ash)', 'Escória de Alto Forno Granulada (GGBS)', 'Micro-fibra PP (anti-fissuração plástica)'].includes(e.nome))
    .reduce((s, e) => s + e.dosagem, 0);

  const obs: string[] = [];
  if (efeitos.length === 0) obs.push('Nenhum aditivo selecionado');
  if (aditivos.plastificante && aditivos.superplastificante) {
    obs.push('ATENÇÃO: Uso de plastificante e superplastificante simultaneamente – verificar compatibilidade');
  }
  if (aditivos.retardador && aditivos.acelerador) {
    obs.push('ATENÇÃO: Retardador e acelerador não devem ser usados juntos');
  }
  if (reducao_agua_total > 25) {
    obs.push('Redução de água acumulada > 25% – verificar por ensaio de dosagem específico (NBR 12820)');
  }

  return {
    aditivos_utilizados: efeitos,
    reducao_agua_total_pct: Math.round(reducao_agua_real * 10) / 10,
    agua_efetiva: Math.round(agua_efetiva),
    consumo_total_aditivos: Math.round(consumo_quimicos * 10) / 10,
    custo_adicional_estimado: estimarCustoAditivos(efeitos),
    observacoes: obs,
  };
}

function estimarCustoAditivos(efeitos: AdditiveEffect[]): string {
  // Estimativa de custo relativo (qualitativo)
  const custo_por_aditivo: Record<string, string> = {
    'Plastificante': 'baixo',
    'Superplastificante (HRWR)': 'médio-alto',
    'Retardador de Pega': 'baixo',
    'Acelerador de Pega': 'médio',
    'Incorporador de Ar': 'baixo',
    'Sílica Ativa (Microssílica)': 'alto',
    'Cinza Volante (Fly Ash)': 'baixo',
    'Escória de Alto Forno Granulada (GGBS)': 'baixo-médio',
    'Micro-fibra PP (anti-fissuração plástica)': 'médio',
  };
  if (efeitos.length === 0) return 'Sem aditivos';
  const custos = efeitos.map(e => custo_por_aditivo[e.nome] ?? 'médio');
  const temAlto = custos.includes('alto');
  const temMedioAlto = custos.includes('médio-alto');
  if (temAlto || (temMedioAlto && efeitos.length > 2)) return 'Alto (+R$ 15-40/m³)';
  if (temMedioAlto || efeitos.length > 2) return 'Médio (+R$ 5-15/m³)';
  return 'Baixo (+R$ 2-8/m³)';
}
