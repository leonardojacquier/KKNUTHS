import { ProjectInput, PavementType, ReinforcementType, MeshType } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; tipo: PavementType; }

const MESH_OPTIONS: { value: MeshType; label: string }[] = [
  { value: 'Q92',  label: 'Q-92  (∅4.2@150mm – As=0.92 cm²/m) – Lajes leves' },
  { value: 'Q131', label: 'Q-131 (∅4.7@133mm – As=1.31 cm²/m)' },
  { value: 'Q188', label: 'Q-188 (∅5.0@104mm – As=1.88 cm²/m)' },
  { value: 'Q283', label: 'Q-283 (∅6.0@100mm – As=2.83 cm²/m) – Padrão pisos' },
  { value: 'Q335', label: 'Q-335 (∅6.5@100mm – As=3.35 cm²/m) – Pisos médios' },
  { value: 'Q503', label: 'Q-503 (∅8.0@100mm – As=5.03 cm²/m) – Rodovias e aeroportos' },
  { value: 'Q636', label: 'Q-636 (∅9.0@100mm – As=6.36 cm²/m) – Alta resistência' },
];

export default function GeometrySection({ data, onChange, tipo }: Props) {
  const geo = data.geometria;
  function setGeo(p: Partial<typeof geo>) { onChange({ geometria: { ...geo, ...p } }); }

  const num_x = Math.ceil(geo.comprimento_placa / geo.espaco_junta_transversal);
  const num_y = Math.ceil(geo.largura_placa / geo.espaco_junta_longitudinal);
  const num_placas = num_x * num_y;
  const tipo_arm = geo.tipo_armadura ?? 'temperature';

  return (
    <div>
      <h2 className="section-title">Geometria, Juntas e Armadura</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {tipo === 'rodovia' && (
          <>
            <div>
              <label className="label">Largura da Faixa (m)</label>
              <input type="number" className="input-field" step="0.1"
                value={geo.largura_faixa ?? 3.6}
                onChange={e => {
                  const lf = parseFloat(e.target.value);
                  const nf = geo.numero_faixas ?? 2;
                  setGeo({ largura_faixa: lf, largura_placa: lf * nf });
                }} />
            </div>
            <div>
              <label className="label">Número de Faixas</label>
              <input type="number" className="input-field" min="1" max="8"
                value={geo.numero_faixas ?? 2}
                onChange={e => {
                  const nf = parseInt(e.target.value);
                  const lf = geo.largura_faixa ?? 3.6;
                  setGeo({ numero_faixas: nf, largura_placa: lf * nf });
                }} />
            </div>
          </>
        )}
        <div>
          <label className="label">Comprimento Total da Área (m)</label>
          <input type="number" className="input-field" step="1" min="1"
            value={geo.comprimento_placa}
            onChange={e => setGeo({ comprimento_placa: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Largura Total da Área (m)</label>
          <input type="number" className="input-field" step="0.5" min="1"
            value={geo.largura_placa}
            onChange={e => setGeo({ largura_placa: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Espessura da Placa (cm) – opcional</label>
          <input type="number" className="input-field" step="1" min="0"
            value={geo.espessura_placa ?? ''}
            onChange={e => setGeo({ espessura_placa: e.target.value ? parseInt(e.target.value) : undefined })}
            placeholder="Calcular automaticamente" />
        </div>
      </div>

      <h3 className="text-base font-semibold text-gray-700 mb-3 border-b pb-2">Juntas</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="label">Espaçamento de Juntas Transversais (m)</label>
          <input type="number" className="input-field" step="0.5" min="1" max="12"
            value={geo.espaco_junta_transversal}
            onChange={e => setGeo({ espaco_junta_transversal: parseFloat(e.target.value) })} />
          <p className="text-xs text-gray-400 mt-1">
            {tipo === 'piso' ? 'Pisos: 4–8 m' : tipo === 'aeroporto' ? 'Aeroporto: 4,5–7,5 m' : 'Rodovia: 4–6 m'}
          </p>
        </div>
        <div>
          <label className="label">Espaçamento de Juntas Longitudinais (m)</label>
          <input type="number" className="input-field" step="0.5" min="1" max="10"
            value={geo.espaco_junta_longitudinal}
            onChange={e => setGeo({ espaco_junta_longitudinal: parseFloat(e.target.value) })} />
        </div>
      </div>

      {/* Dowels */}
      <div className="p-4 border border-gray-200 rounded-lg mb-4">
        <div className="flex items-center gap-3 mb-3">
          <input type="checkbox" id="dow" className="w-4 h-4 text-blue-600"
            checked={geo.dowels}
            onChange={e => setGeo({ dowels: e.target.checked })} />
          <label htmlFor="dow" className="font-medium text-gray-700">Barras de Transferência (Dowels) – juntas transversais | CA-25 liso</label>
        </div>
        {geo.dowels && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Diâmetro (mm)</label>
              <select className="input-field"
                value={geo.diametro_dowel ?? ''}
                onChange={e => setGeo({ diametro_dowel: e.target.value ? parseInt(e.target.value) : undefined })}>
                <option value="">Automático (baseado em espessura)</option>
                <option value="20">∅ 20 mm</option>
                <option value="25">∅ 25 mm</option>
                <option value="32">∅ 32 mm</option>
                <option value="38">∅ 38 mm</option>
                <option value="45">∅ 45 mm</option>
              </select>
            </div>
            <div>
              <label className="label">Espaçamento (cm)</label>
              <input type="number" className="input-field"
                value={geo.espaco_dowel ?? 30}
                onChange={e => setGeo({ espaco_dowel: parseInt(e.target.value) })} />
            </div>
          </div>
        )}
      </div>

      {/* Tie bars */}
      <div className="p-4 border border-gray-200 rounded-lg mb-4">
        <div className="flex items-center gap-3 mb-3">
          <input type="checkbox" id="tie" className="w-4 h-4 text-blue-600"
            checked={geo.tie_bars}
            onChange={e => setGeo({ tie_bars: e.target.checked })} />
          <label htmlFor="tie" className="font-medium text-gray-700">Barras de Ligação (Tie Bars) – juntas longitudinais | CA-50 nervurado</label>
        </div>
        {geo.tie_bars && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Diâmetro (mm)</label>
              <select className="input-field"
                value={geo.diametro_tie_bar ?? ''}
                onChange={e => setGeo({ diametro_tie_bar: e.target.value ? parseInt(e.target.value) : undefined })}>
                <option value="">Automático</option>
                <option value="12">∅ 12 mm</option>
                <option value="16">∅ 16 mm</option>
                <option value="20">∅ 20 mm</option>
              </select>
            </div>
            <div>
              <label className="label">Espaçamento (cm)</label>
              <input type="number" className="input-field"
                value={geo.espaco_tie_bar ?? 75}
                onChange={e => setGeo({ espaco_tie_bar: parseInt(e.target.value) })} />
            </div>
          </div>
        )}
      </div>

      {/* Armadura da placa */}
      <h3 className="text-base font-semibold text-gray-700 mb-3 border-b pb-2">Armadura da Placa de Concreto</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="label">Tipo de Armadura</label>
          <select className="input-field" value={tipo_arm}
            onChange={e => setGeo({ tipo_armadura: e.target.value as ReinforcementType })}>
            <option value="none">Sem armadura (concreto simples / fibras)</option>
            <option value="temperature">Armadura de temperatura e retração (padrão)</option>
            <option value="mesh">Malha eletrossoldada (tela de aço – CA-60)</option>
            <option value="structural_bars">Armadura estrutural em barras (CA-50)</option>
          </select>
        </div>

        {tipo_arm === 'mesh' && (
          <div>
            <label className="label">Tipo de Malha (ou selecionar automático)</label>
            <select className="input-field"
              value={geo.tipo_malha ?? ''}
              onChange={e => setGeo({ tipo_malha: e.target.value as MeshType || undefined })}>
              <option value="">Automático (calculado pelo sistema)</option>
              {MESH_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
        )}

        {tipo_arm === 'structural_bars' && (
          <div>
            <label className="label">Armadura Estrutural (além da temperatura)</label>
            <div className="flex items-center gap-2 mt-2">
              <input type="checkbox" id="arm_est" className="w-4 h-4 text-blue-600"
                checked={geo.usar_armadura_estrutural ?? false}
                onChange={e => setGeo({ usar_armadura_estrutural: e.target.checked })} />
              <label htmlFor="arm_est" className="text-sm">
                Dimensionar armadura estrutural adicional (ACI 360R / NBR 6118)
              </label>
            </div>
          </div>
        )}
      </div>

      {tipo_arm === 'mesh' && (
        <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-xs text-purple-800 mb-4">
          <strong>Malha Eletrossoldada (CA-60 NBR 7480):</strong> O sistema selecionará automaticamente
          a malha adequada ao As calculado. Folha padrão: 2,45m × 6,10m com 10% de sobra para emendas.
          Verificar disponibilidade regional do fornecedor.
        </div>
      )}

      {tipo_arm === 'structural_bars' && (
        <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg text-xs text-orange-800 mb-4">
          <strong>Armadura Estrutural:</strong> Recomendada para pavimentos de aeroporto e rodovias de
          alta solicitação. Taxa mínima para pisos: 0.25% | Aeroportos: 0.40% (ACI 360R / DNIT).
        </div>
      )}

      <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
        <strong>Resumo da malha:</strong> {num_x} placas × {num_y} placas =
        <strong className="text-blue-700"> {num_placas} placas</strong> |
        Área: {geo.comprimento_placa} × {geo.largura_placa} m =
        <strong> {(geo.comprimento_placa * geo.largura_placa).toFixed(0)} m²</strong>
      </div>
    </div>
  );
}
