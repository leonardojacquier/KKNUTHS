export type PavementType = 'piso' | 'aeroporto' | 'rodovia';

export type FiberType = 'none' | 'steel' | 'synthetic' | 'both';

export type CementType = 'CP-I' | 'CP-II-E' | 'CP-II-F' | 'CP-II-Z' | 'CP-III' | 'CP-IV' | 'CP-V-ARI';

export type SubbaseType = 'bgt' | 'bgtm' | 'brta' | 'solo_cimento' | 'rachao' | 'brita_graduada';

export type BaseType = 'bgtm' | 'brta' | 'solo_cimento' | 'brita_graduada' | 'reciclado';

export type JointType = 'expansion' | 'contraction' | 'construction';

// ---- Input Types ----

export interface TrafficInput {
  // Rodovia (DNIT)
  n_equivalente?: number;        // Número N de eixos equivalentes (10⁶)
  periodo_projeto?: number;      // Anos de projeto
  fator_veiculo?: number;        // Fator veículo (FV)
  tma?: number;                  // TMA - Tensão média na argamassa

  // Aeroporto (ICAO/FAA)
  aeronave_critica?: string;     // Aeronave critica
  max_peso_decolagem?: number;   // MTOW (kN)
  operacoes_anuais?: number;     // Operações anuais
  num_rodas?: number;            // Número de rodas do trem de pouso
  carga_roda?: number;           // Carga por roda (kN)
  pressao_pneu?: number;         // Pressão dos pneus (MPa)
  tipo_pista?: 'pista_principal' | 'taxiway' | 'apron';

  // Piso industrial
  carga_concentrada?: number;    // Carga concentrada (kN)
  carga_distribuida?: number;    // Carga distribuída (kN/m²)
  carga_empilhadeira?: number;   // Carga empilhadeira (kN)
  distancia_rodas?: number;      // Distância entre rodas da empilhadeira (m)
  area_contato?: number;         // Área de contato da roda (cm²)
}

export interface SubgradeInput {
  cbr: number;                   // CBR do subleito (%)
  k_direto?: number;             // Módulo de reação k direto (MPa/m), se conhecido
  tipo_solo: string;             // Classificação do solo
  umedade_otima?: number;        // Umidade ótima (%)
  densidade_max?: number;        // Densidade seca máxima (kg/m³)
  melhoramento?: boolean;        // Requer melhoramento do subleito
  cbr_melhorado?: number;        // CBR após melhoramento
}

export interface SubbaseBaseInput {
  incluir_subbase: boolean;
  tipo_subbase?: SubbaseType;
  espessura_subbase?: number;    // cm (deixar 0 para calcular)
  cbr_subbase?: number;          // CBR da subbase (%)

  incluir_base: boolean;
  tipo_base?: BaseType;
  espessura_base?: number;       // cm (deixar 0 para calcular)
  cbr_base?: number;             // CBR da base (%)
  resistencia_base?: number;     // Para solo-cimento: resistência (MPa)
}

export interface ConcreteInput {
  fck: number;                   // Resistência característica (MPa)
  fck_flex?: number;             // Resistência à flexão (MPa) - se conhecido
  tipo_cimento: CementType;
  diametro_agregado: number;     // Diâmetro máximo do agregado (mm)
  tipo_agregado: 'basalto' | 'granito' | 'calcario' | 'seixo';
  abatimento: number;            // Abatimento (mm)
  classe_agressividade: 'I' | 'II' | 'III' | 'IV';
  fibra_tipo: FiberType;
  fibra_dosagem?: number;        // kg/m³ ou % para sintética
  fibra_comprimento?: number;    // mm (fibra de aço)
  fibra_diametro?: number;       // mm (fibra de aço)
}

export interface GeometryInput {
  comprimento_placa: number;     // m
  largura_placa: number;         // m
  largura_faixa?: number;        // m (para rodovias)
  numero_faixas?: number;
  espessura_placa?: number;      // cm (deixar 0 para calcular)
  acostamento?: boolean;
  largura_acostamento?: number;  // m
  // Juntas
  espaco_junta_transversal: number; // m
  espaco_junta_longitudinal: number;// m
  dowels: boolean;               // Barras de transferência
  diametro_dowel?: number;       // mm
  espaco_dowel?: number;         // cm
  tie_bars: boolean;             // Barras de ligação
  diametro_tie_bar?: number;     // mm
  espaco_tie_bar?: number;       // cm
}

export interface ProjectInput {
  nome_projeto: string;
  responsavel: string;
  data: string;
  localizacao: string;
  tipo_pavimento: PavementType;
  trafico: TrafficInput;
  subleito: SubgradeInput;
  camadas: SubbaseBaseInput;
  concreto: ConcreteInput;
  geometria: GeometryInput;
}

// ---- Output / Results Types ----

export interface SubgradeResult {
  cbr_projeto: number;
  k_value: number;              // MPa/m
  k_corrigido: number;          // MPa/m (com subbase)
  classificacao: string;
  melhoramento_necessario: boolean;
  espessura_melhoramento?: number; // cm
}

export interface LayerResult {
  material: string;
  espessura: number;            // cm
  cbr: number;
  k_contribuido?: number;       // MPa/m
  volume_por_m2: number;        // m³/m²
}

export interface SlabResult {
  espessura: number;            // cm (arredondada para comercial)
  espessura_calculada: number;  // cm (teórica)
  tensao_critica: number;       // MPa
  tensao_admissivel: number;    // MPa
  fator_seguranca: number;
  raio_rigidez: number;         // m
  metodo: string;
  equacao: string;
}

export interface ConcreteMixResult {
  fck: number;                  // MPa
  fcj: number;                  // MPa (fck + desvio)
  fct_flex: number;             // MPa (resistência à flexo-tração)
  fct_sp: number;               // MPa (resistência à tração por compressão diametral)
  resistencia_trecagem: number; // MPa
  relacao_agua_cimento: number; // a/c
  consumo_cimento: number;      // kg/m³
  consumo_agua: number;         // L/m³
  consumo_areia: number;        // kg/m³ (ou L/m³)
  consumo_brita: number;        // kg/m³ (ou L/m³)
  consumo_fibras?: number;      // kg/m³
  traco_massico: string;        // "1 : x : y (a/c = z)"
  traco_volumetrico: string;
  classe_resistencia: string;   // Ex: C30
  modulo_elasticidade: number;  // GPa
  slump: number;                // mm
}

export interface FiberResult {
  tipo: FiberType;
  dosagem: number;              // kg/m³
  comprimento?: number;         // mm
  diametro?: number;            // mm
  esbeltez?: number;            // L/d
  resistencia_trecagem?: number;// MPa
  modelo_calculo: string;
  distribuicao: string;
  observacoes: string[];
}

export interface ReinforcementResult {
  armadura_temperatura: boolean;
  diametro_barra: number;       // mm
  espacamento: number;          // cm
  taxa_armadura: number;        // %
  as_calculado: number;         // cm²/m
  // Dowels
  dowels: boolean;
  diametro_dowel?: number;      // mm
  comprimento_dowel?: number;   // mm
  espacamento_dowel?: number;   // cm
  // Tie bars
  tie_bars: boolean;
  diametro_tie_bar?: number;    // mm
  comprimento_tie_bar?: number; // mm
  espacamento_tie_bar?: number; // cm
}

export interface QuantityResult {
  area_total: number;           // m²
  volume_concreto: number;      // m³
  volume_subbase: number;       // m³
  volume_base: number;          // m³
  massa_cimento: number;        // kg
  massa_areia: number;          // kg (t)
  massa_brita: number;          // kg (t)
  massa_fibras: number;         // kg
  massa_aco_barras: number;     // kg
  massa_dowels: number;         // kg
  num_placas: number;
  perimetro_juntas: number;     // m
}

export interface CalculationResult {
  subleito: SubgradeResult;
  subbase?: LayerResult;
  base?: LayerResult;
  placa: SlabResult;
  concreto: ConcreteMixResult;
  fibras?: FiberResult;
  armadura: ReinforcementResult;
  quantidades: QuantityResult;
  alertas: string[];
  ok: boolean;
}
