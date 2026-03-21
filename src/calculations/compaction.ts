import { CompactionEquipment, CompactionLayer, CompactionResult } from '../types';
import { SubbaseBaseInput, SubgradeInput } from '../types';

/**
 * Dimensionamento da compactação de camadas de pavimento
 * Referências:
 *  - DNIT 136/2018-ES (Execução de camadas de pavimento)
 *  - ABNT NBR 7182 (Ensaio de Compactação - Proctor)
 *  - DNIT 137/2018-ES (Solo-cimento)
 *  - USACE EM 1110-3-137
 */

interface LayerCompactionInput {
  nome: string;
  material: string;
  espessura_total: number;     // cm
  tipo_solo: 'granular' | 'coesivo' | 'solo_cimento' | 'rachao';
  grau_compactacao: number;    // % Proctor Normal (95, 97, 100)
  equipamento: CompactionEquipment;
}

// Espessura máxima por camada (cm) por tipo de material e equipamento
function espessuraMaximaCamada(tipo_solo: string, equipamento: CompactionEquipment): number {
  const tabela: Record<string, Record<string, number>> = {
    granular: {
      rolo_vibratorio_pesado:  30,
      rolo_vibratorio_medio:   25,
      rolo_pneumatico:         20,
      rolo_pe_de_carneiro:     20,
      rolo_liso_estatico:      15,
      placa_vibratoria:        25,
    },
    coesivo: {
      rolo_vibratorio_pesado:  20,
      rolo_vibratorio_medio:   18,
      rolo_pneumatico:         20,
      rolo_pe_de_carneiro:     25, // melhor para solos coesivos
      rolo_liso_estatico:      15,
      placa_vibratoria:        15,
    },
    solo_cimento: {
      rolo_vibratorio_pesado:  20,
      rolo_vibratorio_medio:   18,
      rolo_pneumatico:         15,
      rolo_pe_de_carneiro:     15,
      rolo_liso_estatico:      15,
      placa_vibratoria:        15,
    },
    rachao: {
      rolo_vibratorio_pesado:  40,
      rolo_vibratorio_medio:   30,
      rolo_pneumatico:         20,
      rolo_pe_de_carneiro:     20,
      rolo_liso_estatico:      20,
      placa_vibratoria:        20,
    },
  };
  return tabela[tipo_solo]?.[equipamento] ?? 20;
}

// Número de passadas base para 95% Proctor
// Passadas de "ida-e-volta" = 2 passadas simples
function passadasBase(tipo_solo: string, equipamento: CompactionEquipment): number {
  const tabela: Record<string, Record<string, number>> = {
    granular: {
      rolo_vibratorio_pesado:  4,
      rolo_vibratorio_medio:   5,
      rolo_pneumatico:         8,
      rolo_pe_de_carneiro:     10,
      rolo_liso_estatico:      10,
      placa_vibratoria:        6,
    },
    coesivo: {
      rolo_vibratorio_pesado:  6,
      rolo_vibratorio_medio:   8,
      rolo_pneumatico:         10,
      rolo_pe_de_carneiro:     8, // pata-de-carneiro eficiente em coesivos
      rolo_liso_estatico:      12,
      placa_vibratoria:        10,
    },
    solo_cimento: {
      rolo_vibratorio_pesado:  6,
      rolo_vibratorio_medio:   8,
      rolo_pneumatico:         10,
      rolo_pe_de_carneiro:     10,
      rolo_liso_estatico:      12,
      placa_vibratoria:        10,
    },
    rachao: {
      rolo_vibratorio_pesado:  3,
      rolo_vibratorio_medio:   4,
      rolo_pneumatico:         6,
      rolo_pe_de_carneiro:     6,
      rolo_liso_estatico:      8,
      placa_vibratoria:        4,
    },
  };
  return tabela[tipo_solo]?.[equipamento] ?? 8;
}

// Fator de correção para grau de compactação
function fatorGrauCompactacao(grau: number): number {
  if (grau <= 95) return 1.0;
  if (grau <= 97) return 1.30;
  if (grau <= 100) return 1.70;
  return 2.00; // > 100% - muito difícil
}

// Velocidade operacional recomendada do equipamento (km/h)
function velocidadeOperacional(equipamento: CompactionEquipment): number {
  const vel: Record<CompactionEquipment, number> = {
    rolo_vibratorio_pesado:  3.5,
    rolo_vibratorio_medio:   3.0,
    rolo_pneumatico:         5.0,
    rolo_pe_de_carneiro:     3.0,
    rolo_liso_estatico:      4.0,
    placa_vibratoria:        0.5,
  };
  return vel[equipamento] ?? 3.0;
}

// Nome legível do equipamento
function nomeEquipamento(eq: CompactionEquipment): string {
  const nomes: Record<CompactionEquipment, string> = {
    rolo_vibratorio_pesado:  'Rolo Vibratório Pesado (>15t)',
    rolo_vibratorio_medio:   'Rolo Vibratório Médio (10-15t)',
    rolo_pneumatico:         'Rolo Pneumático (20-30t)',
    rolo_pe_de_carneiro:     'Rolo Pé-de-Carneiro (Sheep-foot)',
    rolo_liso_estatico:      'Rolo Liso Estático',
    placa_vibratoria:        'Placa Vibratória (áreas restritas)',
  };
  return nomes[eq] ?? eq;
}

function observacoesCompactacao(
  tipo_solo: string,
  equipamento: CompactionEquipment,
  grau: number,
  material: string
): string[] {
  const obs: string[] = [];

  // Adequação equipamento × material
  if (tipo_solo === 'coesivo' && equipamento === 'rolo_vibratorio_pesado') {
    obs.push('Rolo pé-de-carneiro é mais eficiente para solos coesivos/argilosos');
  }
  if (tipo_solo === 'granular' && equipamento === 'rolo_pe_de_carneiro') {
    obs.push('Para materiais granulares, rolo vibratório é mais eficiente');
  }
  if (tipo_solo === 'solo_cimento') {
    obs.push('Solo-cimento: compactar em até 2h após mistura (janela de pega)');
    obs.push('Verificar resistência à compressão simples aos 7 dias (DNIT-ES 137)');
    obs.push('Umidificação final com rolo pneumático para fechar fissuras de tração');
  }
  if (tipo_solo === 'rachao') {
    obs.push('Rachão: compactar em duas passadas com rolo vibratório antes de adicionar camada');
    obs.push('Verificar nivelamento após compactação (régua de 3m: max 10mm)');
  }
  if (grau >= 100) {
    obs.push('Grau de compactação ≥100% PN: Verificar por ensaio Proctor Modificado (NBR 7182)');
    obs.push('Pode ser necessário pré-umedecer o material e aguardar absorção');
  }
  if (grau >= 97) {
    obs.push(`Grau ${grau}% PN requer controle tecnológico rigoroso – densímetro nuclear ou frasco de areia a cada 500m²`);
  }

  // Umidade ótima
  obs.push('Controlar umidade: w = wótima ± 2% para compactação eficiente');
  obs.push(`Controle de campo: densímetro nuclear ASTM D6938 ou frasco de areia ABNT NBR 7185`);

  if (equipamento === 'placa_vibratoria') {
    obs.push('Placa vibratória: somente para áreas restritas e reparos – não substitui rolo em áreas abertas');
  }

  return obs;
}

function calcularCamada(input: LayerCompactionInput): CompactionLayer {
  const h_max = espessuraMaximaCamada(input.tipo_solo, input.equipamento);
  const num_subcamadas = Math.ceil(input.espessura_total / h_max);
  const h_subcamada = Math.ceil(input.espessura_total / num_subcamadas);

  const passadas_base = passadasBase(input.tipo_solo, input.equipamento);
  const fator_gc = fatorGrauCompactacao(input.grau_compactacao);
  const num_passadas = Math.ceil(passadas_base * fator_gc);
  const num_passadas_total = num_passadas * num_subcamadas;

  return {
    nome: input.nome,
    material: input.material,
    espessura_total: input.espessura_total,
    espessura_camada: h_subcamada,
    num_subcamadas,
    equipamento: input.equipamento,
    grau_compactacao: input.grau_compactacao,
    num_passadas,
    num_passadas_total,
    velocidade_recomendada: velocidadeOperacional(input.equipamento),
    observacoes: observacoesCompactacao(input.tipo_solo, input.equipamento, input.grau_compactacao, input.material),
  };
}

// Mapeia tipo de material para classe de solo de compactação
function tipoSoloCompactacao(tipo: string): 'granular' | 'coesivo' | 'solo_cimento' | 'rachao' {
  if (tipo === 'solo_cimento') return 'solo_cimento';
  if (tipo === 'rachao') return 'rachao';
  if (['bgt', 'bgtm', 'brta', 'brita_graduada', 'reciclado'].includes(tipo)) return 'granular';
  return 'coesivo'; // subleito argiloso padrão
}

function tipoSoloSubleito(tipo_solo: string): 'granular' | 'coesivo' | 'solo_cimento' | 'rachao' {
  const coesivos = ['argila', 'silte', 'argiloso', 'siltoso', 'fino'];
  const lower = tipo_solo.toLowerCase();
  if (coesivos.some(c => lower.includes(c))) return 'coesivo';
  return 'granular';
}

export function calcularCompactacao(
  subleito: SubgradeInput,
  camadas: SubbaseBaseInput
): CompactionResult {
  const layers: CompactionLayer[] = [];
  const equipamentos_set = new Set<string>();

  // Camada 1: Regularização/Melhoramento do Subleito
  if (subleito.melhoramento) {
    const eq: CompactionEquipment = subleito.equipamento_compactacao ?? 'rolo_pe_de_carneiro';
    const gc = subleito.grau_compactacao_alvo ?? 95;
    const esp = subleito.espessura_camada_compactacao ?? 30;
    const ts = tipoSoloSubleito(subleito.tipo_solo);
    layers.push(calcularCamada({
      nome: 'Melhoramento do Subleito',
      material: `${subleito.tipo_solo} (melhorado – CBR mín. ${subleito.cbr_melhorado ?? 6}%)`,
      espessura_total: esp,
      tipo_solo: ts,
      grau_compactacao: gc,
      equipamento: eq,
    }));
    equipamentos_set.add(nomeEquipamento(eq));
  }

  // Camada 2: Regularização do Subleito (sempre)
  {
    const eq: CompactionEquipment = subleito.equipamento_compactacao ?? 'rolo_vibratorio_medio';
    const gc = subleito.grau_compactacao_alvo ?? 95;
    const ts = tipoSoloSubleito(subleito.tipo_solo);
    layers.push(calcularCamada({
      nome: 'Regularização do Subleito',
      material: subleito.tipo_solo,
      espessura_total: 20, // camada de regularização padrão
      tipo_solo: ts,
      grau_compactacao: gc,
      equipamento: eq,
    }));
    equipamentos_set.add(nomeEquipamento(eq));
  }

  // Camada 3: Subbase
  if (camadas.incluir_subbase && camadas.tipo_subbase) {
    const eq: CompactionEquipment = camadas.equipamento_subbase ?? 'rolo_vibratorio_pesado';
    const gc = camadas.grau_compactacao_subbase ?? 97;
    const ts = tipoSoloCompactacao(camadas.tipo_subbase);
    const espessura = camadas.espessura_subbase ?? 20;
    layers.push(calcularCamada({
      nome: 'Subbase',
      material: subbaseMaterialName(camadas.tipo_subbase),
      espessura_total: espessura,
      tipo_solo: ts,
      grau_compactacao: gc,
      equipamento: eq,
    }));
    equipamentos_set.add(nomeEquipamento(eq));
  }

  // Camada 4: Base
  if (camadas.incluir_base && camadas.tipo_base) {
    const eq: CompactionEquipment = camadas.equipamento_base ?? 'rolo_vibratorio_pesado';
    const gc = camadas.grau_compactacao_base ?? 100;
    const ts = tipoSoloCompactacao(camadas.tipo_base);
    const espessura = camadas.espessura_base ?? 15;
    layers.push(calcularCamada({
      nome: 'Base',
      material: baseMaterialName(camadas.tipo_base),
      espessura_total: espessura,
      tipo_solo: ts,
      grau_compactacao: gc,
      equipamento: eq,
    }));
    equipamentos_set.add(nomeEquipamento(eq));
  }

  const obs_gerais = [
    'Verificar umidade de compactação antes de cada camada (w = wótima ± 2%)',
    'Controle tecnológico: 1 ensaio / 500 m² por camada (DNIT 136/2018)',
    'Aguardar 24h entre camadas consecutivas em condições úmidas',
    'Não compactar com chuva intensa ou solo encharcado',
    'Manter proteção da superfície compactada contra ressecamento e tráfego',
    'Ensaios de controle: ABNT NBR 7185 (frasco de areia) ou ASTM D6938 (densímetro nuclear)',
  ];

  return {
    camadas: layers,
    equipamentos_recomendados: Array.from(equipamentos_set),
    observacoes_gerais: obs_gerais,
  };
}

function subbaseMaterialName(tipo: string): string {
  const nomes: Record<string, string> = {
    bgt: 'BGT – Brita Graduada Tratada',
    bgtm: 'BGTM – Brita Graduada Tratada Mista',
    brta: 'BRTA – Brita Run of Quarry',
    solo_cimento: 'Solo-Cimento Estabilizado',
    rachao: 'Rachão (Pedra Irregular)',
    brita_graduada: 'Brita Graduada Simples (BGS)',
  };
  return nomes[tipo] ?? tipo;
}

function baseMaterialName(tipo: string): string {
  const nomes: Record<string, string> = {
    bgtm: 'BGTM – Brita Graduada Tratada Mista',
    brta: 'BRTA – Brita Run of Quarry',
    solo_cimento: 'Solo-Cimento Estabilizado',
    brita_graduada: 'Brita Graduada Simples (BGS)',
    reciclado: 'Material Reciclado (RAP)',
  };
  return nomes[tipo] ?? tipo;
}

export { nomeEquipamento };
