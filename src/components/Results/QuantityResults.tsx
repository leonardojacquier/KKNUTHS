import { CalculationResult, ProjectInput } from '../../types';

interface Props { result: CalculationResult; inputs: ProjectInput; }

export default function QuantityResults({ result, inputs }: Props) {
  const q = result.quantidades;
  const c = result.concreto;

  const items = [
    { label: 'Área total de projeto', value: `${q.area_total.toLocaleString('pt-BR')} m²` },
    { label: 'Volume de concreto (placa)', value: `${q.volume_concreto.toFixed(1)} m³` },
    q.volume_base > 0 ? { label: 'Volume da base', value: `${q.volume_base.toFixed(1)} m³` } : null,
    q.volume_subbase > 0 ? { label: 'Volume da subbase', value: `${q.volume_subbase.toFixed(1)} m³` } : null,
    { label: 'Consumo de cimento', value: `${q.massa_cimento.toLocaleString('pt-BR')} kg` },
    { label: 'Consumo de areia', value: `${q.massa_areia.toLocaleString('pt-BR')} t` },
    { label: 'Consumo de brita', value: `${q.massa_brita.toLocaleString('pt-BR')} t` },
    q.massa_fibras > 0 ? { label: 'Consumo de fibras', value: `${q.massa_fibras.toLocaleString('pt-BR')} kg` } : null,
    q.massa_aco_barras > 0 ? { label: 'Aço em barras (temperatura)', value: `${q.massa_aco_barras.toLocaleString('pt-BR')} kg` } : null,
    q.massa_dowels > 0 ? { label: 'Aço em dowels', value: `${q.massa_dowels.toLocaleString('pt-BR')} kg` } : null,
    { label: 'Número de placas', value: `${q.num_placas} und` },
    { label: 'Comprimento de juntas serradas', value: `${q.perimetro_juntas.toFixed(0)} m` },
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <div className="card">
      <h3 className="section-title">Quantitativos de Materiais</h3>
      <p className="text-xs text-gray-400 mb-3">
        Baseado em {inputs.geometria.comprimento_placa}×{inputs.geometria.largura_placa} m de área
      </p>

      <div className="space-y-1">
        {items.map((item, i) => (
          <div key={i} className="result-item">
            <span className="result-label">{item.label}</span>
            <span className="result-value">{item.value}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded text-xs text-amber-700">
        <strong>Obs:</strong> Quantidades estimadas sem perdas. Aplicar coeficientes de perda:
        concreto +5%, areia/brita +10%, cimento ±3%. Verificar especificações do projeto.
      </div>

      <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
        <strong>Traço adotado:</strong> {c.traco_massico}
        <br />
        <strong>Normas:</strong> NBR 12655:2022, NBR 7480, NBR 6118
      </div>
    </div>
  );
}
