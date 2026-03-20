import { ProjectInput, PavementType } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; tipo: PavementType; }

const SUBBASE_TYPES = [
  { value: 'bgtm', label: 'BGTM – Brita Graduada Tratada Mista' },
  { value: 'bgt', label: 'BGT – Brita Graduada Tratada' },
  { value: 'brta', label: 'BRTA – Brita Run of Quarry' },
  { value: 'solo_cimento', label: 'Solo-Cimento' },
  { value: 'rachao', label: 'Rachão (Pedra Irregular)' },
  { value: 'brita_graduada', label: 'Brita Graduada Simples' },
];

const BASE_TYPES = [
  { value: 'bgtm', label: 'BGTM – Brita Graduada Tratada Mista' },
  { value: 'brta', label: 'BRTA – Brita Run of Quarry' },
  { value: 'solo_cimento', label: 'Solo-Cimento' },
  { value: 'brita_graduada', label: 'Brita Graduada Simples' },
  { value: 'reciclado', label: 'Material Reciclado (RAP)' },
];

export default function LayersSection({ data, onChange, tipo }: Props) {
  const cam = data.camadas;
  function setCam(p: Partial<typeof cam>) { onChange({ camadas: { ...cam, ...p } }); }

  return (
    <div>
      <h2 className="section-title">Camadas Granulares – Subbase e Base</h2>

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
        )}
      </div>

      <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
        <strong>Nota DNIT:</strong> Para N &gt; 10⁷, recomenda-se base de BGTM ou BRTA com espessura mínima de 20 cm.
        Subbase solo-cimento melhora significativamente o k do subleito (fator ≈1.35).
      </div>
    </div>
  );
}
