import { ProjectInput, PavementType } from '../types';

export function defaultInputs(tipo: PavementType): ProjectInput {
  const base: ProjectInput = {
    nome_projeto: 'Projeto de Pavimento',
    responsavel: '',
    data: new Date().toISOString().split('T')[0],
    localizacao: '',
    tipo_pavimento: tipo,
    trafico: {},
    subleito: {
      cbr: 8,
      tipo_solo: 'Argila arenosa',
    },
    camadas: {
      incluir_subbase: true,
      tipo_subbase: 'bgtm',
      incluir_base: false,
    },
    concreto: {
      fck: 35,
      tipo_cimento: 'CP-V-ARI',
      diametro_agregado: 19,
      tipo_agregado: 'basalto',
      abatimento: 80,
      classe_agressividade: 'II',
      fibra_tipo: 'none',
    },
    geometria: {
      comprimento_placa: 100,
      largura_placa: 100,
      espaco_junta_transversal: 5,
      espaco_junta_longitudinal: 3.75,
      dowels: true,
      tie_bars: true,
    },
  };

  if (tipo === 'rodovia') {
    base.trafico = {
      n_equivalente: 5,      // x10^6
      periodo_projeto: 20,
    };
    base.concreto.fck = 35;
    base.camadas.incluir_base = true;
    base.camadas.tipo_base = 'bgtm';
    base.geometria.largura_faixa = 3.6;
    base.geometria.numero_faixas = 2;
    base.geometria.comprimento_placa = 200;
    base.geometria.largura_placa = 7.2;
    base.geometria.espaco_junta_transversal = 4.5;
    base.geometria.espaco_junta_longitudinal = 3.6;
  }

  if (tipo === 'aeroporto') {
    base.trafico = {
      aeronave_critica: 'Boeing 737-800',
      max_peso_decolagem: 790,   // kN
      operacoes_anuais: 30000,
      num_rodas: 4,
      carga_roda: 150,           // kN
      pressao_pneu: 1.2,         // MPa
      periodo_projeto: 20,
      tipo_pista: 'pista_principal',
    };
    base.concreto.fck = 40;
    base.camadas.incluir_subbase = true;
    base.camadas.tipo_subbase = 'solo_cimento';
    base.camadas.incluir_base = true;
    base.camadas.tipo_base = 'brta';
    base.geometria.comprimento_placa = 1000;
    base.geometria.largura_placa = 45;
    base.geometria.espaco_junta_transversal = 5;
    base.geometria.espaco_junta_longitudinal = 4.5;
  }

  if (tipo === 'piso') {
    base.trafico = {
      carga_concentrada: 80,     // kN
      carga_distribuida: 20,     // kN/m²
      carga_empilhadeira: 100,   // kN
      distancia_rodas: 1.2,      // m
      area_contato: 600,         // cm²
    };
    base.concreto.fck = 35;
    base.concreto.fibra_tipo = 'steel';
    base.concreto.fibra_dosagem = 30;
    base.concreto.fibra_comprimento = 50;
    base.concreto.fibra_diametro = 1.0;
    base.camadas.incluir_base = true;
    base.camadas.tipo_base = 'brita_graduada';
    base.geometria.comprimento_placa = 50;
    base.geometria.largura_placa = 50;
    base.geometria.espaco_junta_transversal = 6;
    base.geometria.espaco_junta_longitudinal = 6;
    base.geometria.dowels = false;
    base.geometria.tie_bars = false;
  }

  return base;
}
