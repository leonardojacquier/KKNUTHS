import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

export default function AdditiveResults({ result }: Props) {
  const { aditivos, concreto } = result;
  if (!aditivos || aditivos.aditivos_utilizados.length === 0) return null;

  return (
    <div className="card">
      <h3 className="section-title">Aditivos e Adições Minerais</h3>

      {/* Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-blue-600 font-medium">Redução de Água</p>
          <p className="text-xl font-bold text-blue-700">{aditivos.reducao_agua_total_pct.toFixed(1)}%</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-blue-600 font-medium">Água Efetiva</p>
          <p className="text-xl font-bold text-blue-700">{aditivos.agua_efetiva} L/m³</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-blue-600 font-medium">Aditivos Químicos</p>
          <p className="text-xl font-bold text-blue-700">{aditivos.consumo_total_aditivos.toFixed(1)} kg/m³</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-blue-600 font-medium">Custo Adicional</p>
          <p className="text-sm font-bold text-blue-700">{aditivos.custo_adicional_estimado}</p>
        </div>
      </div>

      {/* Teor de ar (se incorporador) */}
      {concreto.teor_ar && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
          <strong>Incorporador de Ar:</strong> Teor de ar estimado = {concreto.teor_ar.toFixed(1)}%.
          Verificar por pressão (ABNT NBR 9833) ou método gravimétrico.
          Teor recomendado: 4–6% (resistência ao gelo-degelo) | 4–7% (máximo).
        </div>
      )}

      {/* Lista de aditivos */}
      <div className="space-y-3">
        {aditivos.aditivos_utilizados.map((ad, i) => (
          <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-3 py-2 flex items-center justify-between">
              <div>
                <span className="font-semibold text-gray-800">{ad.nome}</span>
                <span className="ml-2 text-xs text-gray-500">{ad.tipo}</span>
              </div>
              <div className="flex gap-3 text-xs">
                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-mono">
                  {ad.dosagem.toFixed(2)} kg/m³
                </span>
                {ad.reducao_agua_pct !== 0 && (
                  <span className={`px-2 py-0.5 rounded font-mono ${ad.reducao_agua_pct > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    Água: {ad.reducao_agua_pct > 0 ? '-' : '+'}{Math.abs(ad.reducao_agua_pct).toFixed(1)}%
                  </span>
                )}
                {ad.aumento_resistencia_pct !== 0 && (
                  <span className={`px-2 py-0.5 rounded font-mono ${ad.aumento_resistencia_pct > 0 ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                    Resist.: {ad.aumento_resistencia_pct > 0 ? '+' : ''}{ad.aumento_resistencia_pct.toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
            <ul className="px-3 py-2 text-xs text-gray-600 space-y-0.5">
              {ad.observacoes.map((obs, j) => (
                <li key={j} className={obs.startsWith('ATENÇÃO') || obs.startsWith('⚠') ? 'text-amber-700 font-medium' : ''}>
                  {obs.startsWith('✓') || obs.startsWith('ℹ') ? obs : `• ${obs}`}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Consumo atualizado */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-xs font-semibold text-gray-600 mb-2">Traço ajustado com aditivos:</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          <div><span className="text-gray-500">Cimento:</span> <strong>{concreto.consumo_cimento} kg/m³</strong></div>
          <div><span className="text-gray-500">Água efetiva:</span> <strong>{concreto.consumo_agua} L/m³</strong></div>
          <div><span className="text-gray-500">a/c real:</span> <strong>{concreto.relacao_agua_cimento.toFixed(3)}</strong></div>
          {concreto.consumo_silica && <div><span className="text-gray-500">Sílica:</span> <strong>{concreto.consumo_silica} kg/m³</strong></div>}
          {concreto.consumo_cinza && <div><span className="text-gray-500">Cinza:</span> <strong>{concreto.consumo_cinza} kg/m³</strong></div>}
          {concreto.consumo_escoria && <div><span className="text-gray-500">Escória:</span> <strong>{concreto.consumo_escoria} kg/m³</strong></div>}
          {concreto.consumo_micro_pp && <div><span className="text-gray-500">Micro-PP:</span> <strong>{concreto.consumo_micro_pp} kg/m³</strong></div>}
        </div>
      </div>

      {/* Alertas dos aditivos */}
      {aditivos.observacoes.length > 0 && (
        <div className="mt-3 space-y-1">
          {aditivos.observacoes.map((obs, i) => (
            <p key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded">
              ⚠ {obs}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
