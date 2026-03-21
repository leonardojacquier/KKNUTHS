import { CalculationResult, ProjectInput } from '../../types';

interface Props { result: CalculationResult; inputs: ProjectInput; }

export default function QuantityResults({ result, inputs }: Props) {
  const q = result.quantidades;
  const c = result.concreto;

  const items = [
    { label: 'Área total de projeto', value: `${q.area_total.toLocaleString('pt-BR')} m²`, highlight: true },
    { label: 'Volume de concreto (placa)', value: `${q.volume_concreto.toFixed(1)} m³`, highlight: true },
    q.volume_base > 0 ? { label: 'Volume da base', value: `${q.volume_base.toFixed(1)} m³` } : null,
    q.volume_subbase > 0 ? { label: 'Volume da subbase', value: `${q.volume_subbase.toFixed(1)} m³` } : null,
    null, // separator
    { label: 'Consumo de cimento', value: `${q.massa_cimento.toLocaleString('pt-BR')} kg` },
    q.massa_silica ? { label: 'Sílica Ativa', value: `${q.massa_silica.toLocaleString('pt-BR')} kg` } : null,
    q.massa_cinza ? { label: 'Cinza Volante', value: `${q.massa_cinza.toLocaleString('pt-BR')} kg` } : null,
    q.massa_escoria ? { label: 'Escória GGBS', value: `${q.massa_escoria.toLocaleString('pt-BR')} kg` } : null,
    { label: 'Consumo de areia', value: `${q.massa_areia.toLocaleString('pt-BR')} t` },
    { label: 'Consumo de brita', value: `${q.massa_brita.toLocaleString('pt-BR')} t` },
    q.massa_fibras > 0 ? { label: `Fibras (${inputs.concreto.fibra_tipo === 'steel' ? 'aço' : inputs.concreto.fibra_tipo === 'synthetic' ? 'sintética' : 'híbrido'})`, value: `${q.massa_fibras.toLocaleString('pt-BR')} kg` } : null,
    null,
    q.massa_aco_barras > 0 ? { label: 'Aço em barras (temperatura/estrutural)', value: `${q.massa_aco_barras.toLocaleString('pt-BR')} kg` } : null,
    q.massa_malha ? { label: 'Malha eletrossoldada', value: `${q.massa_malha.toLocaleString('pt-BR')} kg` } : null,
    q.massa_dowels > 0 ? { label: 'Aço em dowels (CA-25)', value: `${q.massa_dowels.toLocaleString('pt-BR')} kg` } : null,
    null,
    { label: 'Número de placas', value: `${q.num_placas} und` },
    { label: 'Comprimento de juntas serradas', value: `${q.perimetro_juntas.toFixed(0)} m` },
  ].filter(Boolean);

  // Aço total
  const aco_total = (q.massa_aco_barras || 0) + (q.massa_malha || 0) + (q.massa_dowels || 0);

  return (
    <div className="card">
      <h3 className="section-title">Quantitativos de Materiais</h3>
      <p className="text-xs text-gray-400 mb-3">
        Baseado em {inputs.geometria.comprimento_placa}×{inputs.geometria.largura_placa} m de área
      </p>

      <div className="space-y-0.5">
        {items.map((item, i) => {
          if (item === null) return <div key={i} className="border-t border-gray-100 my-2" />;
          const it = item as { label: string; value: string; highlight?: boolean };
          return (
            <div key={i} className={`result-item ${it.highlight ? 'bg-blue-50 rounded px-2' : ''}`}>
              <span className="result-label">{it.label}</span>
              <span className={`result-value ${it.highlight ? 'text-blue-700 font-bold' : ''}`}>{it.value}</span>
            </div>
          );
        })}
        {aco_total > 0 && (
          <div className="result-item bg-gray-100 rounded px-2 mt-2">
            <span className="result-label font-semibold">Total de aço</span>
            <span className="result-value font-bold">{aco_total.toLocaleString('pt-BR')} kg</span>
          </div>
        )}
      </div>

      <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded text-xs text-amber-700">
        <strong>Obs:</strong> Quantidades sem perdas. Aplicar coeficientes:
        concreto +5% | areia/brita +10% | cimento ±3% | aço +5% (corte e dobra) | malha +10% (emendas).
      </div>

      <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
        <strong>Traço adotado:</strong> {c.traco_massico}
        <br />
        {c.relacao_agua_aglomerante && <><strong>a/(c+poz):</strong> {c.relacao_agua_aglomerante.toFixed(3)} | </>}
        <strong>Normas:</strong> NBR 12655:2022, NBR 7480, NBR 6118
      </div>
    </div>
  );
}
