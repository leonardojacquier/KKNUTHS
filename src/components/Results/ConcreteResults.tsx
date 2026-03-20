import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

export default function ConcreteResults({ result }: Props) {
  const c = result.concreto;
  const f = result.fibras;

  return (
    <div className="card">
      <h3 className="section-title">Traço do Concreto</h3>

      <div className="p-3 bg-blue-50 rounded-lg border border-blue-100 mb-4">
        <p className="text-xs text-blue-600 font-medium mb-1">Traço em Massa (1 : A : B)</p>
        <p className="font-mono font-bold text-blue-800">{c.traco_massico}</p>
        <p className="text-xs text-blue-500 mt-1">{c.traco_volumetrico}</p>
      </div>

      <div className="space-y-1 mb-4">
        <div className="result-item">
          <span className="result-label">Classe de resistência</span>
          <span className="result-value">{c.classe_resistencia} (fck = {c.fck} MPa)</span>
        </div>
        <div className="result-item">
          <span className="result-label">Resistência de dosagem (fcj)</span>
          <span className="result-value">{c.fcj} MPa</span>
        </div>
        <div className="result-item">
          <span className="result-label">Resistência à flexo-tração (MR)</span>
          <span className="result-value text-orange-600">{c.fct_flex} MPa</span>
        </div>
        <div className="result-item">
          <span className="result-label">Relação água/cimento (a/c)</span>
          <span className="result-value">{c.relacao_agua_cimento}</span>
        </div>
        <div className="result-item">
          <span className="result-label">Módulo de elasticidade (Ec)</span>
          <span className="result-value">{c.modulo_elasticidade} GPa</span>
        </div>
      </div>

      <h4 className="text-sm font-semibold text-gray-700 mb-2">Consumos por m³</h4>
      <div className="grid grid-cols-2 gap-2 text-sm mb-4">
        {[
          ['Cimento', `${c.consumo_cimento} kg`],
          ['Água', `${c.consumo_agua} L`],
          ['Areia', `${c.consumo_areia} kg`],
          ['Brita', `${c.consumo_brita} kg`],
          ...(c.consumo_fibras ? [['Fibras', `${c.consumo_fibras} kg`]] : []),
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between bg-gray-50 px-3 py-2 rounded">
            <span className="text-gray-500">{k}</span>
            <span className="font-semibold">{v}</span>
          </div>
        ))}
      </div>

      {/* Fibras */}
      {f && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2 border-t pt-2">Reforço com Fibras</h4>
          <div className="space-y-1">
            {f.tipo === 'steel' || f.tipo === 'both' ? (
              <>
                <div className="result-item">
                  <span className="result-label">Tipo</span>
                  <span className="result-value">Fibra de Aço (SFRC)</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Geometria</span>
                  <span className="result-value">{f.comprimento}mm × ∅{f.diametro}mm (L/d={f.esbeltez?.toFixed(0)})</span>
                </div>
              </>
            ) : (
              <div className="result-item">
                <span className="result-label">Tipo</span>
                <span className="result-value">Macro-fibra Sintética (PP/PVA)</span>
              </div>
            )}
            <div className="result-item">
              <span className="result-label">Dosagem</span>
              <span className="result-value text-green-700">{f.dosagem} kg/m³</span>
            </div>
            {f.resistencia_trecagem && (
              <div className="result-item">
                <span className="result-label">fR1 (resistência pós-fissuração)</span>
                <span className="result-value">{f.resistencia_trecagem} MPa</span>
              </div>
            )}
            <div className="result-item">
              <span className="result-label">Distribuição</span>
              <span className="result-value text-xs text-right max-w-[200px]">{f.distribuicao}</span>
            </div>
          </div>
          {f.observacoes.length > 0 && (
            <div className="mt-2 p-2 bg-green-50 rounded text-xs text-green-700 space-y-1">
              {f.observacoes.map((o, i) => <p key={i}>• {o}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
