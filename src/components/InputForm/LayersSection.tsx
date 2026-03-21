import { ProjectInput, PavementType, CompactionEquipment } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; tipo: PavementType; }

const SUBBASE_TYPES = [
  { value: 'bgtm', label: 'BGTM – Brita Graduada Tratada Mista' },
  { value: 'bgt', label: 'BGT – Brita Graduada Tratada' },
  { value: 'brta', label: 'BRTA – Brita Run of Quarry' },
  { value: 'solo_cimento', label: 'Solo-Cimento Estabilizado' },
  { value: 'rachao', label: 'Rachão (Pedra Irregular)' },
  { value: 'brita_graduada', label: 'Brita Graduada Simples (BGS)' },
];

const BASE_TYPES = [
  { value: 'bgtm', label: 'BGTM – Brita Graduada Tratada Mista' },
  { value: 'brta', label: 'BRTA – Brita Run of Quarry' },
  { value: 'solo_cimento', label: 'Solo-Cimento Estabilizado' },
  { value: 'brita_graduada', label: 'Brita Graduada Simples (BGS)' },
  { value: 'reciclado', label: 'Material Reciclado (RAP)' },
];

const EQUIPAMENTOS: { value: CompactionEquipment; label: string }[] = [
  { value: 'rolo_vibratorio_pesado',  label: 'Rolo Vibratório Pesado (>15t) – Recomendado granular' },
  { value: 'rolo_vibratorio_medio',   label: 'Rolo Vibratório Médio (10-15t)' },
  { value: 'rolo_pneumatico',         label: 'Rolo Pneumático (20-30t)' },
  { value: 'rolo_pe_de_carneiro',     label: 'Rolo Pé-de-Carneiro – Recomendado coesivo' },
  { value: 'rolo_liso_estatico',      label: 'Rolo Liso Estático' },
  { value: 'placa_vibratoria',        label: 'Placa Vibratória (áreas restritas)' },
];

export default function LayersSection({ data, onChange, tipo }: Props) {
  const cam = data.camadas;
  const sub = data.subleito;
  function setCam(p: Partial<typeof cam>) { onChange({ camadas: { ...cam, ...p } }); }
  function setSub(p: Partial<typeof sub>) { onChange({ subleito: { ...sub, ...p } }); }

  return (
    <div>
      <h2 className="section-title">Camadas Granulares – Subbase e Base</h2>

      {/* Subleito – compactação */}
      <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-amber-50">
        <h3 className="font-semibold text-gray-700 mb-3">Compactação do Subleito</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Grau de Compactação Alvo</label>
            <select className="input-field"
              value={sub.grau_compactacao_alvo ?? 95}
              onChange={e => setSub({ grau_compactacao_alvo: parseInt(e.target.value) })}>
              <option value="95">95% Proctor Normal (padrão)</option>
              <option value="97">97% Proctor Normal</option>
              <option value="100">100% Proctor Normal (máximo)</option>
            </select>
          </div>
          <div>
            <label className="label">Equipamento de Compactação</label>
            <select className="input-field"
              value={sub.equipamento_compactacao ?? 'rolo_vibratorio_medio'}
              onChange={e => setSub({ equipamento_compactacao: e.target.value as CompactionEquipment })}>
              {EQUIPAMENTOS.map(eq => <option key={eq.value} value={eq.value}>{eq.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Espessura da Subcamada (cm)</label>
            <input type="number" className="input-field" step="5" min="10" max="40"
              value={sub.espessura_camada_compactacao ?? 20}
              onChange={e => setSub({ espessura_camada_compactacao: parseInt(e.target.value) })} />
            <p className="text-xs text-gray-400 mt-1">Espessura máxima por camada de compactação</p>
          </div>
        </div>
      </div>

      {/* SUBBASE */}
      <div className="mb-6 p-4 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3 mb-4">
          <input type="checkbox" id="sb" className="w-4 h-4 text-blue-600"
            checked={cam.incluir_subbase}
            onChange={e => setCam({ incluir_subbase: e.target.checked })} />
          <label htmlFor="sb" className="font-semibold text-gray-700">Subbase</label>
          {!cam.incluir_subbase && <span className="text-xs text-gray-400">(não incluída)</span>}
        </div>

        {cam.incluir_subbase && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="md:col-span-2">
                <label className="label">Tipo de Material</label>
                <select className="input-field"
                  value={cam.tipo_subbase ?? 'bgtm'}
                  onChange={e => setCam({ tipo_subbase: e.target.value as any })}>
                  {SUBBASE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Espessura (cm)</label>
                <input type="number" className="input-field" step="5" min="0"
                  value={cam.espessura_subbase ?? ''}
                  onChange={e => setCam({ espessura_subbase: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto" />
                <p className="text-xs text-gray-400 mt-1">Deixar em branco para calcular</p>
              </div>
              <div>
                <label className="label">CBR da Subbase (%)</label>
                <input type="number" className="input-field" step="5"
                  value={cam.cbr_subbase ?? ''}
                  onChange={e => setCam({ cbr_subbase: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto" />
              </div>
            </div>
            {/* Compactação da subbase */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-50 p-3 rounded-lg">
              <div>
                <label className="label text-xs">Grau de Compactação da Subbase</label>
                <select className="input-field"
                  value={cam.grau_compactacao_subbase ?? 97}
                  onChange={e => setCam({ grau_compactacao_subbase: parseInt(e.target.value) })}>
                  <option value="95">95% Proctor Normal</option>
                  <option value="97">97% Proctor Normal (padrão)</option>
                  <option value="100">100% Proctor Normal</option>
                </select>
              </div>
              <div>
                <label className="label text-xs">Equipamento de Compactação</label>
                <select className="input-field"
                  value={cam.equipamento_subbase ?? 'rolo_vibratorio_pesado'}
                  onChange={e => setCam({ equipamento_subbase: e.target.value as CompactionEquipment })}>
                  {EQUIPAMENTOS.map(eq => <option key={eq.value} value={eq.value}>{eq.label}</option>)}
                </select>
              </div>
            </div>
          </>
        )}
      </div>

      {/* BASE */}
      <div className="mb-4 p-4 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-3 mb-4">
          <input type="checkbox" id="ba" className="w-4 h-4 text-blue-600"
            checked={cam.incluir_base}
            onChange={e => setCam({ incluir_base: e.target.checked })} />
          <label htmlFor="ba" className="font-semibold text-gray-700">Base</label>
          {!cam.incluir_base && <span className="text-xs text-gray-400">(não incluída)</span>}
        </div>

        {cam.incluir_base && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="md:col-span-2">
                <label className="label">Tipo de Material</label>
                <select className="input-field"
                  value={cam.tipo_base ?? 'bgtm'}
                  onChange={e => setCam({ tipo_base: e.target.value as any })}>
                  {BASE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Espessura (cm)</label>
                <input type="number" className="input-field" step="5" min="0"
                  value={cam.espessura_base ?? ''}
                  onChange={e => setCam({ espessura_base: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto" />
              </div>
              <div>
                <label className="label">CBR da Base (%)</label>
                <input type="number" className="input-field" step="5"
                  value={cam.cbr_base ?? ''}
                  onChange={e => setCam({ cbr_base: e.target.value ? parseInt(e.target.value) : undefined })}
                  placeholder="Auto" />
              </div>
            </div>
            {/* Compactação da base */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-50 p-3 rounded-lg">
              <div>
                <label className="label text-xs">Grau de Compactação da Base</label>
                <select className="input-field"
                  value={cam.grau_compactacao_base ?? 100}
                  onChange={e => setCam({ grau_compactacao_base: parseInt(e.target.value) })}>
                  <option value="95">95% Proctor Normal</option>
                  <option value="97">97% Proctor Normal</option>
                  <option value="100">100% Proctor Normal (padrão base)</option>
                </select>
              </div>
              <div>
                <label className="label text-xs">Equipamento de Compactação</label>
                <select className="input-field"
                  value={cam.equipamento_base ?? 'rolo_vibratorio_pesado'}
                  onChange={e => setCam({ equipamento_base: e.target.value as CompactionEquipment })}>
                  {EQUIPAMENTOS.map(eq => <option key={eq.value} value={eq.value}>{eq.label}</option>)}
                </select>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
        <strong>Nota DNIT:</strong> Para N &gt; 10⁷, recomenda-se base de BGTM ou BRTA com espessura
        mínima de 20 cm. Subbase solo-cimento melhora significativamente o k do subleito (fator ≈1.35).
        O sistema calculará automaticamente o número de passadas de rolo necessário para cada camada
        com base no material, equipamento e grau de compactação.
      </div>
    </div>
  );
}
