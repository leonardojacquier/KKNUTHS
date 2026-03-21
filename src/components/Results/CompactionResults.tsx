import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

const EQ_ICONS: Record<string, string> = {
  rolo_vibratorio_pesado: '🔵',
  rolo_vibratorio_medio:  '🟢',
  rolo_pneumatico:        '🟡',
  rolo_pe_de_carneiro:    '🟠',
  rolo_liso_estatico:     '⚪',
  placa_vibratoria:       '🔷',
};

const EQ_COLORS: Record<string, string> = {
  rolo_vibratorio_pesado: 'border-blue-300 bg-blue-50',
  rolo_vibratorio_medio:  'border-green-300 bg-green-50',
  rolo_pneumatico:        'border-yellow-300 bg-yellow-50',
  rolo_pe_de_carneiro:    'border-orange-300 bg-orange-50',
  rolo_liso_estatico:     'border-gray-300 bg-gray-50',
  placa_vibratoria:       'border-purple-300 bg-purple-50',
};

export default function CompactionResults({ result }: Props) {
  const { compactacao } = result;
  if (!compactacao || compactacao.camadas.length === 0) return null;

  const total_passadas = compactacao.camadas.reduce((s, c) => s + c.num_passadas_total, 0);

  return (
    <div className="card">
      <h3 className="section-title">Dimensionamento da Compactação</h3>
      <p className="text-xs text-gray-500 mb-4">
        Número de passadas calculado conforme DNIT 136/2018-ES, ABNT NBR 7182 e USACE EM 1110-3-137.
        Verificar por trecho experimental de compactação (obrigatório em obra).
      </p>

      {/* Resumo */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <p className="text-xs text-amber-600 font-medium">Camadas</p>
          <p className="text-2xl font-bold text-amber-700">{compactacao.camadas.length}</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <p className="text-xs text-amber-600 font-medium">Total de Passadas</p>
          <p className="text-2xl font-bold text-amber-700">{total_passadas}</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <p className="text-xs text-amber-600 font-medium">Equipamentos</p>
          <p className="text-sm font-bold text-amber-700">{compactacao.equipamentos_recomendados.length} tipos</p>
        </div>
      </div>

      {/* Camadas */}
      <div className="space-y-4">
        {compactacao.camadas.map((cam, i) => (
          <div key={i} className={`border-2 rounded-lg overflow-hidden ${EQ_COLORS[cam.equipamento] ?? 'border-gray-200 bg-gray-50'}`}>
            {/* Header da camada */}
            <div className="px-4 py-2 flex items-center justify-between border-b border-current border-opacity-20">
              <div className="flex items-center gap-2">
                <span className="text-lg">{EQ_ICONS[cam.equipamento] ?? '⭕'}</span>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{cam.nome}</p>
                  <p className="text-xs text-gray-600">{cam.material}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Grau de Compactação</p>
                <p className="font-bold text-gray-800">{cam.grau_compactacao}% PN</p>
              </div>
            </div>

            {/* Dados da camada */}
            <div className="px-4 py-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                <div className="text-center">
                  <p className="text-xs text-gray-500">Espessura Total</p>
                  <p className="text-lg font-bold text-gray-800">{cam.espessura_total} cm</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500">Subcamadas</p>
                  <p className="text-lg font-bold text-gray-800">{cam.num_subcamadas}</p>
                  <p className="text-xs text-gray-400">{cam.espessura_camada} cm cada</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500">Passadas/Subcamada</p>
                  <p className="text-2xl font-bold text-blue-700">{cam.num_passadas}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500">Total de Passadas</p>
                  <p className="text-2xl font-bold text-blue-700">{cam.num_passadas_total}</p>
                  <p className="text-xs text-gray-400">(todas subcamadas)</p>
                </div>
              </div>

              {/* Equipamento */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-xs text-gray-500">Equipamento: </span>
                  <span className="text-xs font-medium text-gray-700">{cam.equipamento.replace(/_/g, ' ')}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Velocidade: </span>
                  <span className="text-xs font-medium text-gray-700">{cam.velocidade_recomendada} km/h</span>
                </div>
              </div>

              {/* Observações */}
              {cam.observacoes.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {cam.observacoes.slice(0, 4).map((obs, j) => (
                    <p key={j} className={`text-xs ${obs.includes('ATENÇÃO') ? 'text-amber-700 font-medium' : 'text-gray-600'}`}>
                      • {obs}
                    </p>
                  ))}
                  {cam.observacoes.length > 4 && (
                    <p className="text-xs text-gray-400">+ {cam.observacoes.length - 4} observações...</p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Notas gerais */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-xs font-semibold text-gray-600 mb-2">Notas Gerais de Compactação:</p>
        <ul className="space-y-0.5">
          {compactacao.observacoes_gerais.map((obs, i) => (
            <li key={i} className="text-xs text-gray-600">• {obs}</li>
          ))}
        </ul>
      </div>

      {/* Nota legal */}
      <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
        ⚠ <strong>Importante:</strong> O número de passadas é estimativo. Realizar obrigatoriamente
        Trecho Experimental de Compactação conforme DNIT 136/2018-ES para calibrar os parâmetros reais
        de cada obra (equipamento específico, umidade local e material em uso).
      </div>
    </div>
  );
}
