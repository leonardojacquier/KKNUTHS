import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

export default function StructureResults({ result }: Props) {
  const { subleito, subbase, base, placa } = result;
  const layers = [
    { label: 'Placa de Concreto', value: `${placa.espessura} cm`, color: 'bg-gray-300', note: `fck ${result.concreto.fck} MPa` },
    base ? { label: `Base – ${base.material}`, value: `${base.espessura} cm`, color: 'bg-yellow-200', note: `CBR ${base.cbr}%` } : null,
    subbase ? { label: `Subbase – ${subbase.material}`, value: `${subbase.espessura} cm`, color: 'bg-orange-100', note: `CBR ${subbase.cbr}%` } : null,
    { label: 'Subleito', value: '—', color: 'bg-amber-50', note: `CBR ${subleito.cbr_projeto}% | k ${subleito.k_value.toFixed(0)} MPa/m` },
  ].filter(Boolean) as { label: string; value: string; color: string; note: string }[];

  return (
    <div className="card">
      <h3 className="section-title">Estrutura do Pavimento</h3>

      <div className="space-y-2 mb-4">
        {layers.map((l, i) => (
          <div key={i} className={`flex justify-between items-center px-4 py-3 rounded-lg ${l.color} border border-gray-200`}>
            <div>
              <p className="font-medium text-sm text-gray-800">{l.label}</p>
              <p className="text-xs text-gray-500">{l.note}</p>
            </div>
            <span className="font-bold text-gray-800 text-lg">{l.value}</span>
          </div>
        ))}
      </div>

      <div className="space-y-1">
        <div className="result-item">
          <span className="result-label">Espessura total da estrutura</span>
          <span className="result-value text-blue-700">
            {placa.espessura + (base?.espessura ?? 0) + (subbase?.espessura ?? 0)} cm
          </span>
        </div>
        <div className="result-item">
          <span className="result-label">Espessura calculada (teórica)</span>
          <span className="result-value">{placa.espessura_calculada} cm</span>
        </div>
        <div className="result-item">
          <span className="result-label">k do subleito</span>
          <span className="result-value">{subleito.k_value.toFixed(1)} MPa/m</span>
        </div>
        <div className="result-item">
          <span className="result-label">k composto (com subbase/base)</span>
          <span className="result-value text-green-700">{subleito.k_corrigido.toFixed(1)} MPa/m</span>
        </div>
        <div className="result-item">
          <span className="result-label">Raio de rigidez relativa ℓ</span>
          <span className="result-value">{placa.raio_rigidez} m</span>
        </div>
        <div className="result-item">
          <span className="result-label">Fator de segurança</span>
          <span className={`result-value ${placa.fator_seguranca >= 1.0 ? 'text-green-700' : 'text-red-600'}`}>
            {placa.fator_seguranca.toFixed(2)}
          </span>
        </div>
      </div>

      {subleito.melhoramento_necessario && (
        <div className="alert-error mt-3 text-xs">
          ⚠️ Melhoramento do subleito necessário: camada de {subleito.espessura_melhoramento} cm
        </div>
      )}
    </div>
  );
}
