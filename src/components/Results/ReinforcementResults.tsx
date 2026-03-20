import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

export default function ReinforcementResults({ result }: Props) {
  const a = result.armadura;

  return (
    <div className="card">
      <h3 className="section-title">Armadura e Detalhes de Juntas</h3>

      {/* Armadura de temperatura */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Armadura de Temperatura/Retração</h4>
        {a.armadura_temperatura ? (
          <div className="space-y-1">
            <div className="result-item">
              <span className="result-label">Bitola das barras</span>
              <span className="result-value">∅ {a.diametro_barra} mm (CA-50)</span>
            </div>
            <div className="result-item">
              <span className="result-label">Espaçamento</span>
              <span className="result-value">{a.espacamento} cm (nas 2 direções)</span>
            </div>
            <div className="result-item">
              <span className="result-label">Taxa de armadura</span>
              <span className="result-value">{a.taxa_armadura.toFixed(3)}%</span>
            </div>
            <div className="result-item">
              <span className="result-label">As calculado</span>
              <span className="result-value">{a.as_calculado} cm²/m</span>
            </div>
          </div>
        ) : (
          <div className="p-3 bg-gray-50 rounded text-sm text-gray-500">
            Pavimento de concreto simples (sem armadura de temperatura)
            {result.concreto.consumo_fibras ? ' – reforço por fibras.' : '.'}
          </div>
        )}
      </div>

      {/* Dowels */}
      {a.dowels && (
        <div className="mb-4 p-3 border border-gray-200 rounded-lg">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Barras de Transferência (Dowels)</h4>
          <p className="text-xs text-gray-500 mb-2">Juntas transversais de contração – liso, engaxetado</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Diâmetro</span>
              <span className="font-semibold">∅ {a.diametro_dowel} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Comprimento</span>
              <span className="font-semibold">{a.comprimento_dowel} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Espaçamento</span>
              <span className="font-semibold">{a.espacamento_dowel} cm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Aço</span>
              <span className="font-semibold">CA-25 (liso)</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Posicionar na meia-altura da placa. Metade do comprimento engaxetada (deslizante).
          </p>
        </div>
      )}

      {/* Tie bars */}
      {a.tie_bars && (
        <div className="p-3 border border-gray-200 rounded-lg">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Barras de Ligação (Tie Bars)</h4>
          <p className="text-xs text-gray-500 mb-2">Juntas longitudinais – nervurado, solidário</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Diâmetro</span>
              <span className="font-semibold">∅ {a.diametro_tie_bar} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Comprimento</span>
              <span className="font-semibold">{a.comprimento_tie_bar} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Espaçamento</span>
              <span className="font-semibold">{a.espacamento_tie_bar} cm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Aço</span>
              <span className="font-semibold">CA-50 (nervurado)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
