import { ProjectInput, CalculationResult, QuantityResult } from '../types';
import { calcularSubleito } from './subgrade';
import { calcularSubbase } from './subbase';
import { calcularMR, dimensionarRodovia, dimensionarAeroporto, dimensionarPiso } from './slab';
import { calcularTraco } from './concrete';
import { calcularFibras } from './fibers';
import { calcularArmadura } from './reinforcement';
import { calcularAditivos } from './additives';
import { calcularCompactacao } from './compaction';

export function calcularPavimento(input: ProjectInput): CalculationResult {
  const alertas: string[] = [];

  // 1. Subleito
  const subleito = calcularSubleito(input.subleito);
  if (subleito.melhoramento_necessario) {
    alertas.push('CBR < 2% – melhoramento do subleito necessário (troca de solo ou estabilização)');
  }

  // 2. Subbase e base
  const { subbase, base, k_final } = calcularSubbase(
    input.camadas,
    input.subleito.cbr,
    subleito.k_value,
    input.tipo_pavimento
  );
  subleito.k_corrigido = k_final;

  // 3. Traço do concreto
  const concreto = calcularTraco(input.concreto);

  // 3a. Aditivos (ajusta concreto)
  let aditivos;
  if (input.concreto.aditivos) {
    aditivos = calcularAditivos(
      input.concreto.aditivos,
      concreto.consumo_cimento,
      concreto.consumo_agua,
      concreto.fck
    );
    // Aplica redução de água ao traço
    if (aditivos.reducao_agua_total_pct > 0) {
      const fator = 1 - aditivos.reducao_agua_total_pct / 100;
      concreto.consumo_agua = Math.round(concreto.consumo_agua * fator);
      concreto.relacao_agua_cimento = Math.round(concreto.relacao_agua_cimento * fator * 1000) / 1000;
      // Recalcula traço mássico
      const t_areia = concreto.consumo_areia / concreto.consumo_cimento;
      const t_brita = concreto.consumo_brita / concreto.consumo_cimento;
      concreto.traco_massico = `1 : ${t_areia.toFixed(2)} : ${t_brita.toFixed(2)} (a/c = ${concreto.relacao_agua_cimento.toFixed(2)})`;
    }
    // Adições minerais
    const ads = input.concreto.aditivos;
    if (ads.silica_ativa && ads.silica_ativa_teor) {
      concreto.consumo_silica = Math.round(concreto.consumo_cimento * ads.silica_ativa_teor / 100);
      concreto.consumo_cimento -= concreto.consumo_silica; // substituição parcial
    }
    if (ads.cinza_volante && ads.cinza_volante_teor) {
      concreto.consumo_cinza = Math.round(concreto.consumo_cimento * ads.cinza_volante_teor / 100);
      concreto.consumo_cimento -= concreto.consumo_cinza;
    }
    if (ads.escoria && ads.escoria_teor) {
      concreto.consumo_escoria = Math.round(concreto.consumo_cimento * ads.escoria_teor / 100);
      concreto.consumo_cimento -= concreto.consumo_escoria;
    }
    if (ads.micro_fibra_pp) {
      concreto.consumo_micro_pp = 0.9;
    }
    // Teor de ar
    if (ads.incorporador_ar) {
      concreto.teor_ar = 4 + (ads.incorporador_ar_dosagem ?? 0.1) * 20;
    }

    // Alertas de aditivos
    if (aditivos.observacoes.length > 0) {
      aditivos.observacoes.forEach(obs => {
        if (obs.startsWith('ATENÇÃO')) alertas.push(obs);
      });
    }
  }

  const mr = concreto.fct_flex;

  // 4. Dimensionamento da placa
  let placa;
  const tipo = input.tipo_pavimento;
  const geo  = input.geometria;
  const traf = input.trafico;

  if (tipo === 'rodovia') {
    const N = traf.n_equivalente ?? 5;
    placa = dimensionarRodovia(input.concreto.fck, k_final, N * 1e6, mr);
    if (N < 0.5) alertas.push('Tráfego baixo (N < 0.5×10⁶) – verificar necessidade de placa de concreto');
  } else if (tipo === 'aeroporto') {
    const carga_roda = traf.carga_roda ?? 150;
    const pressao    = traf.pressao_pneu ?? 1.2;
    const ops        = traf.operacoes_anuais ?? 5000;
    const periodo    = traf.periodo_projeto ?? 20;
    placa = dimensionarAeroporto(input.concreto.fck, k_final, carga_roda, pressao, ops, periodo, mr);
  } else {
    const carga_conc = traf.carga_concentrada ?? 50;
    const carga_dist = traf.carga_distribuida ?? 10;
    const carga_emp  = traf.carga_empilhadeira ?? 80;
    const dist_rodas = traf.distancia_rodas ?? 1.0;
    placa = dimensionarPiso(input.concreto.fck, k_final, carga_conc, carga_dist, carga_emp, dist_rodas, mr);
  }

  // Espessura real (pode ter sido definida pelo usuário)
  if (geo.espessura_placa && geo.espessura_placa > 0) {
    if (geo.espessura_placa < placa.espessura) {
      alertas.push(`ATENÇÃO: Espessura definida (${geo.espessura_placa} cm) é menor que a calculada (${placa.espessura} cm)!`);
    }
    placa = { ...placa, espessura: geo.espessura_placa };
  }

  // 5. Fibras
  const fibras = calcularFibras(input.concreto, placa.espessura, tipo);
  if (fibras && input.concreto.fibra_tipo !== 'none') {
    concreto.consumo_fibras = fibras.dosagem;
    if (fibras.substitui_armadura_temperatura) {
      alertas.push(`ℹ Fibras atendem critério TR34 para substituição da armadura de temperatura (${fibras.dosagem.toFixed(0)} kg/m³)`);
    }
  }

  // 6. Armadura
  const armadura = calcularArmadura(
    geo,
    input.concreto,
    placa.espessura,
    tipo,
    fibras?.substitui_armadura_temperatura
  );

  // 7. Compactação
  const compactacao = calcularCompactacao(input.subleito, input.camadas);

  // 8. Quantitativos
  const area = geo.comprimento_placa * geo.largura_placa;
  const vol_placa   = area * placa.espessura / 100;
  const vol_base    = base ? area * base.espessura / 100 : 0;
  const vol_subbase = subbase ? area * subbase.espessura / 100 : 0;

  const num_placas_x = Math.ceil(geo.comprimento_placa / geo.espaco_junta_transversal);
  const num_placas_y = Math.ceil(geo.largura_placa / geo.espaco_junta_longitudinal);
  const num_placas   = num_placas_x * num_placas_y;

  const perim_juntas = (num_placas_x - 1) * geo.largura_placa + (num_placas_y - 1) * geo.comprimento_placa;

  // Massa de aço dos dowels
  let massa_dowels = 0;
  if (armadura.dowels && armadura.diametro_dowel && armadura.espacamento_dowel && armadura.comprimento_dowel) {
    const n_juntas_transv = num_placas_x - 1;
    const n_dowels_por_junta = Math.ceil(geo.largura_placa * 100 / armadura.espacamento_dowel) + 1;
    const n_total_dowels = n_juntas_transv * n_dowels_por_junta;
    const d_m = armadura.diametro_dowel / 1000;
    const L_m = armadura.comprimento_dowel / 1000;
    massa_dowels = n_total_dowels * (Math.PI * d_m * d_m / 4) * L_m * 7850;
  }

  // Massa das barras de temperatura / estrutural
  let massa_aco_barras = 0;
  if (armadura.armadura_temperatura && armadura.diametro_barra > 0 && armadura.tipo !== 'mesh') {
    const as_m2_m = armadura.as_calculado / 10000;
    massa_aco_barras = area * as_m2_m * 2 * 7850;
  }

  // Massa de malha eletrossoldada
  let massa_malha = 0;
  if (armadura.malha) {
    massa_malha = area * armadura.malha.peso_por_m2 * 1.10; // 10% emenda
  }

  // Massa armadura estrutural adicional
  if (armadura.armadura_estrutural && armadura.as_estrutural) {
    const as_m2_m = armadura.as_estrutural / 10000;
    massa_aco_barras += area * as_m2_m * 2 * 7850;
  }

  // Adições minerais
  const massa_silica  = concreto.consumo_silica  ? Math.round(vol_placa * concreto.consumo_silica)  : undefined;
  const massa_cinza   = concreto.consumo_cinza   ? Math.round(vol_placa * concreto.consumo_cinza)   : undefined;
  const massa_escoria = concreto.consumo_escoria ? Math.round(vol_placa * concreto.consumo_escoria) : undefined;

  const quantidades: QuantityResult = {
    area_total: area,
    volume_concreto: Math.round(vol_placa * 100) / 100,
    volume_subbase: Math.round(vol_subbase * 100) / 100,
    volume_base: Math.round(vol_base * 100) / 100,
    massa_cimento: Math.round(vol_placa * concreto.consumo_cimento),
    massa_areia: Math.round(vol_placa * concreto.consumo_areia / 1000),
    massa_brita: Math.round(vol_placa * concreto.consumo_brita / 1000),
    massa_fibras: fibras ? Math.round(vol_placa * fibras.dosagem) : 0,
    massa_aco_barras: Math.round(massa_aco_barras),
    massa_malha: massa_malha > 0 ? Math.round(massa_malha) : undefined,
    massa_dowels: Math.round(massa_dowels),
    massa_silica,
    massa_cinza,
    massa_escoria,
    num_placas,
    perimetro_juntas: Math.round(perim_juntas * 10) / 10,
  };

  // Alertas adicionais
  if (placa.fator_seguranca < 1.05) {
    alertas.push('Fator de segurança próximo de 1.0 – recomenda-se aumentar fck ou espessura');
  }
  if (concreto.relacao_agua_cimento > 0.65) {
    alertas.push('Relação a/c > 0.65 – durabilidade comprometida, verificar fck mínimo');
  }
  if (input.concreto.fibra_tipo !== 'none' && !fibras) {
    alertas.push('Erro no dimensionamento das fibras');
  }
  if (armadura.malha && armadura.malha.as_fornecida < armadura.malha.as_requerida) {
    alertas.push(`Malha ${armadura.malha.tipo_malha} insuficiente – As fornecida < requerida`);
  }

  return {
    subleito,
    subbase,
    base,
    placa,
    concreto,
    fibras,
    aditivos,
    armadura,
    compactacao,
    quantidades,
    alertas,
    ok: alertas.filter(a => a.startsWith('ATENÇÃO') || a.startsWith('Erro')).length === 0,
  };
}
