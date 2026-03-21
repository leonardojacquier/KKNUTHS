import { CalculationResult, ProjectInput } from '../../types';

interface Props { result: CalculationResult; inputs: ProjectInput; }

const TIPO_FULL: Record<string, string> = {
  piso: 'Piso Industrial / Piso de Concreto',
  aeroporto: 'Pavimento Aeroportuário de Concreto',
  rodovia: 'Pavimento Rodoviário de Concreto (PCC)',
};

const NORMAS: Record<string, string[]> = {
  piso: ['ABNT NBR 6118:2023', 'ACI 360R-10', 'TR34 4ª Ed. (Concrete Society)', 'fib MC2010', 'ABNT NBR 15530:2007'],
  aeroporto: ['FAA AC 150/5320-6H', 'ICAO Doc 9157-AN/901', 'ABNT NBR 6118:2023', 'ACI 330.2R', 'DNIT 005/2003-ME'],
  rodovia: ['DNIT 005/2003-PRO', 'DNIT 136/2018-ES', 'DNIT 141/2018-ES', 'PCA (1984)', 'ABNT NBR 6118:2023'],
};

export default function DetailedProject({ result, inputs }: Props) {
  const tipo = inputs.tipo_pavimento;
  const geo = inputs.geometria;
  const conc = inputs.concreto;

  const totalH = (result.subbase?.espessura ?? 0) + (result.base?.espessura ?? 0) + result.placa.espessura;

  // Sequência executiva
  const sequencia = buildSequencia(tipo, inputs, result);

  // Especificações de cura
  const curaConcrete = buildCura(tipo, conc.fck);

  // Controle tecnológico
  const controle = buildControle(tipo);

  return (
    <div className="card">
      <h3 className="section-title">Projeto Detalhado – Memorial Descritivo</h3>

      {/* Identificação */}
      <div className="bg-blue-700 text-white rounded-lg p-4 mb-6">
        <h4 className="font-bold text-lg">{inputs.nome_projeto || 'Projeto sem nome'}</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-sm">
          <div><p className="text-blue-200 text-xs">Tipo</p><p className="font-medium">{TIPO_FULL[tipo]}</p></div>
          <div><p className="text-blue-200 text-xs">Local</p><p className="font-medium">{inputs.localizacao || '–'}</p></div>
          <div><p className="text-blue-200 text-xs">Responsável</p><p className="font-medium">{inputs.responsavel || '–'}</p></div>
          <div><p className="text-blue-200 text-xs">Data</p><p className="font-medium">{inputs.data}</p></div>
        </div>
      </div>

      {/* Resumo da estrutura */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">1. Estrutura do Pavimento</h4>
        <div className="space-y-2">
          {result.subbase && (
            <div className="flex items-center gap-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
              <div className="w-8 text-center font-bold text-yellow-700 text-sm">{result.subbase.espessura} cm</div>
              <div>
                <p className="text-sm font-medium text-gray-700">Subbase – {result.subbase.material}</p>
                <p className="text-xs text-gray-500">CBR ≥ {result.subbase.cbr}% | k contribuído: {result.subbase.k_contribuido?.toFixed(1)} MPa/m</p>
              </div>
            </div>
          )}
          {result.base && (
            <div className="flex items-center gap-3 p-2 bg-orange-50 border border-orange-200 rounded">
              <div className="w-8 text-center font-bold text-orange-700 text-sm">{result.base.espessura} cm</div>
              <div>
                <p className="text-sm font-medium text-gray-700">Base – {result.base.material}</p>
                <p className="text-xs text-gray-500">CBR ≥ {result.base.cbr}% | k contribuído: {result.base.k_contribuido?.toFixed(1)} MPa/m</p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-3 p-2 bg-blue-50 border border-blue-200 rounded">
            <div className="w-8 text-center font-bold text-blue-700 text-sm">{result.placa.espessura} cm</div>
            <div>
              <p className="text-sm font-medium text-gray-700">Placa de Concreto – C{conc.fck} | {conc.tipo_cimento}</p>
              <p className="text-xs text-gray-500">
                MR = {result.concreto.fct_flex} MPa | Ec = {result.concreto.modulo_elasticidade} GPa |
                a/c = {result.concreto.relacao_agua_cimento.toFixed(3)} | Slump = {result.concreto.slump} mm
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-2 bg-gray-100 rounded">
            <div className="w-8 text-center font-bold text-gray-700 text-sm">{totalH}</div>
            <p className="text-sm font-bold text-gray-700">Espessura Total do Pavimento</p>
          </div>
        </div>
      </div>

      {/* Traço do concreto detalhado */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">2. Dosagem do Concreto (NBR 12655:2022)</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          {[
            { label: 'Cimento', val: `${result.concreto.consumo_cimento} kg/m³`, sub: conc.tipo_cimento },
            { label: 'Água', val: `${result.concreto.consumo_agua} L/m³`, sub: `a/c = ${result.concreto.relacao_agua_cimento.toFixed(3)}` },
            { label: 'Areia', val: `${result.concreto.consumo_areia} kg/m³`, sub: 'Areia quartzosa lavada' },
            { label: 'Brita', val: `${result.concreto.consumo_brita} kg/m³`, sub: `TMA ${conc.diametro_agregado}mm | ${conc.tipo_agregado}` },
          ].map((item, i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">{item.label}</p>
              <p className="font-bold text-gray-800">{item.val}</p>
              <p className="text-xs text-gray-400">{item.sub}</p>
            </div>
          ))}
        </div>
        {result.fibras && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            <div className="bg-green-50 rounded-lg p-3">
              <p className="text-xs text-green-600">Fibras ({result.fibras.tipo === 'steel' ? 'Aço' : 'Sintética'})</p>
              <p className="font-bold text-green-800">{result.fibras.dosagem.toFixed(1)} kg/m³</p>
              {result.fibras.comprimento && <p className="text-xs text-green-600">{result.fibras.comprimento}mm × ∅{result.fibras.diametro}mm | L/d={result.fibras.esbeltez?.toFixed(0)}</p>}
            </div>
            {result.fibras.classe_desempenho && (
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs text-green-600">Classe de Desempenho (fib MC2010)</p>
                <p className="font-bold text-green-800 text-xl">{result.fibras.classe_desempenho}</p>
                <p className="text-xs text-green-600">fR1={result.fibras.fR1?.toFixed(2)} | fR3={result.fibras.fR3?.toFixed(2)} MPa</p>
              </div>
            )}
            {result.fibras.substitui_armadura_temperatura && (
              <div className="bg-green-50 rounded-lg p-3 col-span-1">
                <p className="text-xs text-green-600">Substituição Armadura Temp.</p>
                <p className="font-bold text-green-800">✓ Atende TR34</p>
                <p className="text-xs text-green-600">Pode dispensar barras de temperatura</p>
              </div>
            )}
          </div>
        )}
        {result.concreto.consumo_silica && (
          <div className="p-2 bg-gray-50 rounded text-xs text-gray-600">
            Adições: {result.concreto.consumo_silica && `Sílica Ativa: ${result.concreto.consumo_silica} kg/m³`}
            {result.concreto.consumo_cinza && ` | Cinza Volante: ${result.concreto.consumo_cinza} kg/m³`}
            {result.concreto.consumo_escoria && ` | Escória GGBS: ${result.concreto.consumo_escoria} kg/m³`}
          </div>
        )}
        <div className="p-2 bg-gray-50 rounded text-xs mt-2">
          <strong>Traço mássico:</strong> {result.concreto.traco_massico}
          <span className="mx-3">|</span>
          <strong>Traço volumétrico:</strong> {result.concreto.traco_volumetrico}
        </div>
      </div>

      {/* Armadura */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">3. Armadura e Reforço</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {result.armadura.armadura_temperatura && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="font-medium text-gray-700 mb-1">
                {result.armadura.tipo === 'mesh' ? 'Malha Eletrossoldada' : 'Armadura de Temperatura/Retração'}
              </p>
              {result.armadura.malha ? (
                <div className="text-xs space-y-0.5 text-gray-600">
                  <p>Tela: <strong>{result.armadura.malha.tipo_malha}</strong> – ∅{result.armadura.malha.diametro_fio}@{result.armadura.malha.espacamento}mm</p>
                  <p>As fornecida: <strong>{(result.armadura.malha.as_fornecida / 100).toFixed(2)} cm²/m</strong></p>
                  <p>As requerida: <strong>{(result.armadura.malha.as_requerida / 100).toFixed(2)} cm²/m</strong></p>
                  <p>Peso: <strong>{result.armadura.malha.peso_por_m2.toFixed(2)} kg/m²</strong></p>
                  <p>Folha padrão: {result.armadura.malha.dimensoes_padrao}</p>
                  <p>Folhas estimadas: {result.armadura.malha.folhas_por_placa}</p>
                </div>
              ) : (
                <div className="text-xs space-y-0.5 text-gray-600">
                  <p>Bitola: <strong>∅{result.armadura.diametro_barra} mm | CA-50</strong></p>
                  <p>Espaçamento: <strong>{result.armadura.espacamento} cm (nas 2 direções)</strong></p>
                  <p>Taxa: <strong>{result.armadura.taxa_armadura.toFixed(3)}% | As = {result.armadura.as_calculado.toFixed(2)} cm²/m</strong></p>
                  <p>Posição: Metade superior da placa (≥ 5cm cobrimento)</p>
                </div>
              )}
            </div>
          )}
          {result.armadura.armadura_estrutural && result.armadura.as_estrutural && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="font-medium text-gray-700 mb-1">Armadura Estrutural</p>
              <div className="text-xs space-y-0.5 text-gray-600">
                <p>Bitola: <strong>∅{result.armadura.diametro_estrutural} mm | CA-50</strong></p>
                <p>Espaçamento: <strong>{result.armadura.espacamento_estrutural} cm</strong></p>
                <p>As estrutural: <strong>{result.armadura.as_estrutural.toFixed(2)} cm²/m</strong></p>
              </div>
            </div>
          )}
          {result.armadura.dowels && (
            <div className="p-3 bg-blue-50 rounded-lg">
              <p className="font-medium text-gray-700 mb-1">Barras de Transferência (Dowels)</p>
              <div className="text-xs space-y-0.5 text-gray-600">
                <p>∅{result.armadura.diametro_dowel} mm | CA-25 liso | c={result.armadura.espacamento_dowel} cm</p>
                <p>Comprimento: {result.armadura.comprimento_dowel} mm | Posição: meia-altura</p>
                <p>Encaixe: metade engastada, metade graxada (deslizante)</p>
              </div>
            </div>
          )}
          {result.armadura.tie_bars && (
            <div className="p-3 bg-purple-50 rounded-lg">
              <p className="font-medium text-gray-700 mb-1">Barras de Ligação (Tie Bars)</p>
              <div className="text-xs space-y-0.5 text-gray-600">
                <p>∅{result.armadura.diametro_tie_bar} mm | CA-50 nervurado | c={result.armadura.espacamento_tie_bar} cm</p>
                <p>Comprimento: {result.armadura.comprimento_tie_bar} mm | Totalmente aderido</p>
                <p>Posição: meia-altura da junta longitudinal</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sequência executiva */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">4. Sequência Executiva</h4>
        <ol className="space-y-2">
          {sequencia.map((item, i) => (
            <li key={i} className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full text-xs flex items-center justify-center font-bold">
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-medium text-gray-700">{item.titulo}</p>
                {item.detalhe && <p className="text-xs text-gray-500 mt-0.5">{item.detalhe}</p>}
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Especificações de cura */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">5. Especificação de Cura do Concreto</h4>
        <div className="space-y-2">
          {curaConcrete.map((item, i) => (
            <div key={i} className="flex gap-2 text-sm">
              <span className="text-blue-500 flex-shrink-0">▸</span>
              <div>
                <span className="font-medium text-gray-700">{item.titulo}: </span>
                <span className="text-gray-600">{item.detalhe}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Controle tecnológico */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-700 mb-3 border-b pb-1">6. Controle Tecnológico e Ensaios</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {controle.map((item, i) => (
            <div key={i} className="p-3 bg-gray-50 rounded-lg text-xs">
              <p className="font-semibold text-gray-700">{item.tipo}</p>
              <p className="text-gray-600">{item.descricao}</p>
              <p className="text-gray-400 mt-0.5">{item.norma}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Normas aplicáveis */}
      <div>
        <h4 className="font-semibold text-gray-700 mb-2 border-b pb-1">7. Normas e Referências Técnicas</h4>
        <div className="flex flex-wrap gap-2">
          {NORMAS[tipo]?.map((n, i) => (
            <span key={i} className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded">{n}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------
// Helpers
// ---------------------

function buildSequencia(tipo: string, inputs: ProjectInput, result: CalculationResult) {
  const base = [
    { titulo: 'Levantamento topográfico e marcação de eixos', detalhe: 'Nível de precisão ≤ 5 mm/10 m. Definição de cotas de projeto e greide.' },
    { titulo: 'Remoção de vegetação e limpeza da área', detalhe: 'Retirada de camadas orgânicas (min. 15 cm). Disposição adequada de material orgânico.' },
    { titulo: 'Regularização do subleito', detalhe: `Escavação ou aterro conforme perfil de projeto. Compactar a ${inputs.subleito.grau_compactacao_alvo ?? 95}% Proctor Normal com ${(inputs.subleito.equipamento_compactacao ?? 'rolo vibratório').replace(/_/g, ' ')}.` },
  ];

  if (inputs.camadas.incluir_subbase) {
    base.push({
      titulo: `Execução da Subbase – ${(inputs.camadas.tipo_subbase ?? 'BGTM').replace(/_/g, ' ')}`,
      detalhe: `Espalhamento em camada(s) de ${result.compactacao?.camadas.find(c => c.nome === 'Subbase')?.espessura_camada ?? 20} cm. ` +
        `Compactar a ${inputs.camadas.grau_compactacao_subbase ?? 97}% PN. ` +
        `Controle: 1 ensaio por 500 m² (frasco de areia ou densímetro nuclear).`,
    });
  }

  if (inputs.camadas.incluir_base) {
    base.push({
      titulo: `Execução da Base – ${(inputs.camadas.tipo_base ?? 'BGTM').replace(/_/g, ' ')}`,
      detalhe: `Espalhamento uniforme, espessura total ${result.base?.espessura ?? 15} cm. ` +
        `Compactar a ${inputs.camadas.grau_compactacao_base ?? 100}% PN. Aguardar 72h antes da concretagem.`,
    });
  }

  base.push(
    { titulo: 'Instalação de formas', detalhe: 'Formas metálicas ou de madeira. Nivelar e fixar conforme seção transversal. Aplicar desmoldante nas formas. Linha d\'água máx. 3 mm em régua de 3 m.' },
    { titulo: 'Posicionamento de armadura e dowels', detalhe: `Dowels ∅${result.armadura.diametro_dowel ?? '–'} mm a cada ${result.armadura.espacamento_dowel ?? '–'} cm. ` +
      `${result.armadura.armadura_temperatura ? `Armadura ∅${result.armadura.diametro_barra} mm @${result.armadura.espacamento} cm (2 direções).` : 'Fibras: distribuídas no traço.'}` }
  );

  if (tipo === 'piso') {
    base.push(
      { titulo: 'Concretagem do piso', detalhe: 'Lançamento direto com bomba ou calha. Adensamento com régua vibradora e vibrador de imersão nas bordas. Execução por faixas alternadas ou monolítico.' },
      { titulo: 'Acabamento superficial', detalhe: 'Desempeno mecânico (helicóptero) após início de pega. Acabamento final conforme especificação: F-number (ASTM E1155) ou tolerância por régua.' }
    );
  } else if (tipo === 'aeroporto') {
    base.push(
      { titulo: 'Concretagem com pavimentadora de forma deslizante', detalhe: 'Slipform paver. Controle automático de espessura e nível. Velocidade: 1-3 m/min. Acabamento com texturizador e burlador.' },
      { titulo: 'Texturização e ranhuramento', detalhe: 'Ranhurado transversal (grooving) para drenagem e aderência. Profundidade 3-4 mm, espaçamento 20 mm (FAA AC 150/5370-10).' }
    );
  } else {
    base.push(
      { titulo: 'Concretagem com pavimentadora ou distribuição manual', detalhe: 'Adensamento com vibrador de imersão e régua vibratória. Acabamento com sarrafo e desempenadeira de magnesium.' }
    );
  }

  base.push(
    { titulo: 'Aplicação de cura', detalhe: buildCuraSummary(tipo, inputs.concreto.fck) },
    { titulo: 'Serragem de juntas', detalhe: `Serragem em até 6-18h após concretagem (antes da fissuração por retração). Profundidade: h/3 a h/4 = ${Math.round(result.placa.espessura / 3)}-${Math.round(result.placa.espessura / 4)} cm. Largura: 3-5 mm.` },
    { titulo: 'Selagem de juntas', detalhe: 'Limpeza das juntas com jato de ar. Aplicação de primer e selante elastomérico (poliuretano ou silicone – ASTM D 5893). Aguardar mín. 7 dias.' },
    { titulo: 'Abertura ao tráfego', detalhe: tipo === 'aeroporto' ? 'Mínimo 90% fck em ensaio de compressão (ABNT NBR 5739). Período típico: 14-28 dias.' : 'Mínimo 70% fck (7 dias) para tráfego leve; 100% (28 dias) para tráfego pesado.' }
  );

  return base;
}

function buildCura(tipo: string, fck: number) {
  return [
    {
      titulo: 'Cura química (imediata)',
      detalhe: `Aplicar membrana de cura (ASTM C309 Tipo 2) imediatamente após acabamento. Taxa: 5-6 m²/L. Aplicar em 2 mãos cruzadas.`,
    },
    {
      titulo: 'Cura úmida complementar',
      detalhe: `${fck >= 40 || tipo === 'aeroporto' ? '14' : '7'} dias mínimos. Manta de juta ou polietileno molhado. Verificar temperatura superficial (mín. 10°C, máx. 40°C).`,
    },
    {
      titulo: 'Período de cura acelerada (se necessário)',
      detalhe: 'Lona de polietileno + água morna (40-60°C) por 24-48h para ganho rápido de resistência. Usar com CP-V-ARI.',
    },
    {
      titulo: 'Proteção contra vento e sol',
      detalhe: 'Aplicar barreiras contra vento nos primeiros 30 min após acabamento. Velocidade > 15 km/h exige proteção adicional. Risco alto de fissuração plástica.',
    },
    {
      titulo: 'Controle de retração',
      detalhe: 'Micro-fibra PP (0,9 kg/m³) reduz fissuração plástica. Não substituir por aspersão de água prematura que dilui a superfície.',
    },
  ];
}

function buildCuraSummary(tipo: string, fck: number): string {
  const dias = fck >= 40 || tipo === 'aeroporto' ? '14' : '7';
  return `Membrana de cura (ASTM C309) imediatamente após acabamento + cura úmida por ${dias} dias mínimos. Proteger contra vento e sol intenso.`;
}

function buildControle(tipo: string) {
  const ensaios = [
    {
      tipo: 'Resistência à Compressão (CP cilíndrico)',
      descricao: '3 CPs por betonada. Rompimento: 7, 28 e 63 dias. Aceitar se f_cm ≥ fck + 1.65σ.',
      norma: 'ABNT NBR 5739 | ABNT NBR 12655',
    },
    {
      tipo: 'Módulo de Ruptura (Flexo-tração)',
      descricao: 'Viga 15×15×50 cm. Carga em 3 pontos ou 4 pontos. mínimo 3 vigas por lote.',
      norma: 'ABNT NBR 12142 | ASTM C78',
    },
    {
      tipo: 'Consistência (Slump)',
      descricao: 'Aferição a cada betonada. Tolerância: ±25 mm do slump de projeto.',
      norma: 'ABNT NBR NM 67 | ASTM C143',
    },
    {
      tipo: 'Espessura da Placa',
      descricao: 'Furos de sondagem ou medição em forma antes de fechar. Tolerância: -5 mm.',
      norma: 'ASTM D5361 | DNIT-ES 141/2018',
    },
  ];

  if (tipo === 'aeroporto' || tipo === 'rodovia') {
    ensaios.push({
      tipo: 'Regularidade Superficial (IRI)',
      descricao: 'IRI ≤ 2.5 m/km (rodovia) | IRI ≤ 1.5 m/km (aeroporto). Medição com perfilômetro laser.',
      norma: 'DNIT 182/2018-IE | FAA AC 150/5370-11',
    });
  }

  if (tipo === 'piso') {
    ensaios.push({
      tipo: 'Planeza superficial (F-number ou régua)',
      descricao: 'FF ≥ 50 / FL ≥ 35 (pisos críticos) ou régua de 3 m: max 3 mm. Medir em 24-48h.',
      norma: 'ASTM E1155 | ACI 117',
    });
  }

  ensaios.push(
    {
      tipo: 'Compactação das camadas',
      descricao: 'Grau de compactação por frasco de areia ou densímetro nuclear. 1 ensaio / 500 m².',
      norma: 'ABNT NBR 7185 | ASTM D6938',
    },
    {
      tipo: 'CBR das camadas',
      descricao: 'CBR de campo (DCP) ou laboratório. Verificar CBR mínimo de projeto para cada camada.',
      norma: 'ABNT NBR 9895 | ASTM D4429',
    }
  );

  return ensaios;
}
