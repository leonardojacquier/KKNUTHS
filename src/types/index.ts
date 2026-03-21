export type PavementType = 'piso' | 'aeroporto' | 'rodovia';

export type FiberType = 'none' | 'steel' | 'synthetic' | 'both';

export type CementType = 'CP-I' | 'CP-II-E' | 'CP-II-F' | 'CP-II-Z' | 'CP-III' | 'CP-IV' | 'CP-V-ARI';

export type SubbaseType = 'bgt' | 'bgtm' | 'brta' | 'solo_cimento' | 'rachao' | 'brita_graduada';

export type BaseType = 'bgtm' | 'brta' | 'solo_cimento' | 'brita_graduada' | 'reciclado';

export type JointType = 'expansion' | 'contraction' | 'construction';

export type ReinforcementType = 'none' | 'temperature' | 'structural_bars' | 'mesh';

export type MeshType =
  | 'Q92'    // ø4.2@150mm → As=92 mm²/m
  | 'Q131'   // ø4.7@133mm → As=131 mm²/m
  | 'Q188'   // ø5.0@104mm → As=188 mm²/m
  | 'Q283'   // ø6.0@100mm → As=283 mm²/m
  | 'Q335'   // ø6.5@100mm → As=335 mm²/m
  | 'Q503'   // ø8.0@100mm → As=503 mm²/m
  | 'Q636';  // ø9.0@100mm → As=636 mm²/m

export type CompactionEquipment =
  | 'rolo_vibratorio_pesado'   // >15t vibratory
  | 'rolo_vibratorio_medio'    // 10-15t vibratory
  | 'rolo_pneumatico'          // pneumatic rubber-tire
  | 'rolo_pe_de_carneiro'      // sheep-foot (cohesive)
  | 'rolo_liso_estatico'       // static smooth drum
  | 'placa_vibratoria';        // plate compactor (small areas)

// ---- Additives ----
export interface AdditiveInput {
  plastificante?: boolean;
  plastificante_dosagem?: number;       // % sobre cimento
  superplastificante?: boolean;
  superplastificante_dosagem?: number;  // % sobre cimento
  retardador?: boolean;
  retardador_dosagem?: number;
  acelerador?: boolean;
  acelerador_dosagem?: number;
  incorporador_ar?: boolean;
  incorporador_ar_dosagem?: number;
  silica_ativa?: boolean;
  silica_ativa_teor?: number;           // % substituição
  cinza_volante?: boolean;
  cinza_volante_teor?: number;          // % substituição
  escoria?: boolean;
  escoria_teor?: number;                // % substituição
  micro_fibra_pp?: boolean;             // anti-fissuração plástica
}

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
  // Compaction
  grau_compactacao_alvo?: number;      // % Proctor (95, 97, 100)
  equipamento_compactacao?: CompactionEquipment;
  espessura_camada_compactacao?: number; // cm por camada
}

export interface SubbaseBaseInput {
  incluir_subbase: boolean;
  tipo_subbase?: SubbaseType;
  espessura_subbase?: number;    // cm (deixar 0 para calcular)
  cbr_subbase?: number;          // CBR da subbase (%)
  grau_compactacao_subbase?: number;      // % Proctor
  equipamento_subbase?: CompactionEquipment;

  incluir_base: boolean;
  tipo_base?: BaseType;
  espessura_base?: number;       // cm (deixar 0 para calcular)
  cbr_base?: number;             // CBR da base (%)
  resistencia_base?: number;     // Para solo-cimento: resistência (MPa)
  grau_compactacao_base?: number;
  equipamento_base?: CompactionEquipment;
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
  aditivos?: AdditiveInput;      // Aditivos químicos e minerais
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
  // Armadura
  tipo_armadura?: ReinforcementType;
  tipo_malha?: MeshType;         // Se usar malha eletrossoldada
  usar_armadura_estrutural?: boolean; // Armadura estrutural além de temperatura
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

export interface AdditiveEffect {
  nome: string;
  tipo: string;                 // ASTM C494 type etc
  dosagem: number;              // kg/m³ ou % cimento
  reducao_agua_pct: number;     // % redução de água
  aumento_resistencia_pct: number; // % aumento resistência
  observacoes: string[];
}

export interface AdditiveResult {
  aditivos_utilizados: AdditiveEffect[];
  reducao_agua_total_pct: number;
  agua_efetiva: number;         // L/m³ após aditivos
  consumo_total_aditivos: number; // kg/m³
  custo_adicional_estimado: string;
  observacoes: string[];
}

export interface ConcreteMixResult {
  fck: number;                  // MPa
  fcj: number;                  // MPa (fck + desvio)
  fck_efetivo?: number;         // MPa com adições minerais
  fct_flex: number;             // MPa (resistência à flexo-tração)
  fct_sp: number;               // MPa (resistência à tração por compressão diametral)
  resistencia_trecagem: number; // MPa
  relacao_agua_cimento: number; // a/c
  relacao_agua_aglomerante?: number; // a/(c+pozolana)
  consumo_cimento: number;      // kg/m³
  consumo_agua: number;         // L/m³
  consumo_areia: number;        // kg/m³ (ou L/m³)
  consumo_brita: number;        // kg/m³ (ou L/m³)
  consumo_fibras?: number;      // kg/m³
  consumo_silica?: number;      // kg/m³
  consumo_cinza?: number;       // kg/m³
  consumo_escoria?: number;     // kg/m³
  consumo_micro_pp?: number;    // kg/m³
  traco_massico: string;        // "1 : x : y (a/c = z)"
  traco_volumetrico: string;
  classe_resistencia: string;   // Ex: C30
  modulo_elasticidade: number;  // GPa
  slump: number;                // mm
  teor_ar?: number;             // % (se incorporador de ar)
}

export interface FiberPerformanceClass {
  classe: string;               // ex: '1a', '2b', '3', etc.
  fR1_min: number;              // MPa (resistência residual a 0.5mm)
  fR3_min: number;              // MPa (resistência residual a 2.5mm)
  descricao: string;
}

export interface FiberResult {
  tipo: FiberType;
  dosagem: number;              // kg/m³
  comprimento?: number;         // mm
  diametro?: number;            // mm
  esbeltez?: number;            // L/d
  resistencia_trecagem?: number;// MPa
  fR1?: number;                 // MPa resistência residual fissura 0.5mm
  fR3?: number;                 // MPa resistência residual fissura 2.5mm
  classe_desempenho?: string;   // Classe fib MC2010 alcançada
  substitui_armadura_temperatura?: boolean;
  modelo_calculo: string;
  distribuicao: string;
  observacoes: string[];
}

export interface MeshResult {
  tipo_malha: MeshType;
  diametro_fio: number;         // mm
  espacamento: number;          // mm
  as_fornecida: number;         // mm²/m por direção
  as_requerida: number;         // mm²/m
  peso_por_m2: number;          // kg/m²
  dimensoes_padrao: string;     // ex: "2.45m × 6.10m"
  folhas_por_placa: number;
}

export interface ReinforcementResult {
  tipo: ReinforcementType;
  armadura_temperatura: boolean;
  diametro_barra: number;       // mm
  espacamento: number;          // cm
  taxa_armadura: number;        // %
  as_calculado: number;         // cm²/m
  malha?: MeshResult;
  // Armadura estrutural
  armadura_estrutural?: boolean;
  as_estrutural?: number;       // cm²/m
  diametro_estrutural?: number; // mm
  espacamento_estrutural?: number; // cm
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

export interface CompactionLayer {
  nome: string;
  material: string;
  espessura_total: number;       // cm
  espessura_camada: number;      // cm por subcamada
  num_subcamadas: number;
  equipamento: CompactionEquipment;
  grau_compactacao: number;      // % Proctor Normal
  num_passadas: number;          // por subcamada
  num_passadas_total: number;    // total
  velocidade_recomendada: number; // km/h
  observacoes: string[];
}

export interface CompactionResult {
  camadas: CompactionLayer[];
  equipamentos_recomendados: string[];
  observacoes_gerais: string[];
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
  massa_malha?: number;         // kg
  massa_dowels: number;         // kg
  massa_silica?: number;        // kg
  massa_cinza?: number;         // kg
  massa_escoria?: number;       // kg
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
  aditivos?: AdditiveResult;
  armadura: ReinforcementResult;
  compactacao?: CompactionResult;
  quantidades: QuantityResult;
  alertas: string[];
  ok: boolean;
}
