import { ProjectInput } from '../../types';
import { cbrToK, classificarSubleito } from '../../calculations/subgrade';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; }

const SOLOS = [
  'Areia grossa limpa', 'Areia fina limpa', 'Areia argilosa', 'Argila arenosa',
  'Argila siltosa', 'Argila pura', 'Silte arenoso', 'Solo orgânico', 'Pedregulho',
];

export default function SubgradeSection({ data, onChange }: Props) {
  const sub = data.subleito;
  function setSub(p: Partial<typeof sub>) { onChange({ subleito: { ...sub, ...p } }); }

  const k = cbrToK(sub.cbr);
  const classif = classificarSubleito(sub.cbr);

  return (
    <div>
      <h2 className="section-title">Dados do Subleito</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">CBR do Subleito (%)</label>
          <input type="number" className="input-field" step="0.5" min="0.5" max="100"
            value={sub.cbr}
            onChange={e => setSub({ cbr: parseFloat(e.target.value) })} />
          <div className="mt-2 p-2 bg-gray-50 rounded text-xs space-y-1">
            <p className="text-gray-600">k estimado: <strong className="text-blue-700">{k.toFixed(1)} MPa/m</strong></p>
            <p className={`font-medium ${sub.cbr < 2 ? 'text-red-600' : sub.cbr < 5 ? 'text-orange-600' : 'text-green-700'}`}>
              {classif}
            </p>
          </div>
        </div>
        <div>
          <label className="label">k Direto (MPa/m) – opcional</label>
          <input type="number" className="input-field" step="5" min="0"
            value={sub.k_direto ?? ''}
            onChange={e => setSub({ k_direto: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="Deixar em branco para usar CBR" />
          <p className="text-xs text-gray-400 mt-1">Se disponível de ensaio de placa</p>
        </div>
        <div>
          <label className="label">Tipo de Solo (classificação)</label>
          <select className="input-field" value={sub.tipo_solo}
            onChange={e => setSub({ tipo_solo: e.target.value })}>
            {SOLOS.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Umidade Ótima (%)</label>
          <input type="number" className="input-field" step="0.5"
            value={sub.umedade_otima ?? ''}
            onChange={e => setSub({ umedade_otima: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="Opcional" />
        </div>
        <div>
          <label className="label">Densidade Seca Máxima (kg/m³)</label>
          <input type="number" className="input-field"
            value={sub.densidade_max ?? ''}
            onChange={e => setSub({ densidade_max: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="Opcional" />
        </div>
        <div className="flex items-center gap-3 pt-6">
          <input type="checkbox" id="melhora" className="w-4 h-4 text-blue-600"
            checked={sub.melhoramento ?? false}
            onChange={e => setSub({ melhoramento: e.target.checked })} />
          <label htmlFor="melhora" className="text-sm font-medium text-gray-700">
            Melhoramento do subleito previsto
          </label>
        </div>
        {sub.melhoramento && (
          <div>
            <label className="label">CBR após Melhoramento (%)</label>
            <input type="number" className="input-field" step="1"
              value={sub.cbr_melhorado ?? 5}
              onChange={e => setSub({ cbr_melhorado: parseFloat(e.target.value) })} />
          </div>
        )}
      </div>

      {sub.cbr < 2 && (
        <div className="alert-error mt-4">
          ⚠️ CBR muito baixo – melhoramento obrigatório por estabilização, troca de solo ou reforço do subleito (camada de regularização).
        </div>
      )}

      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Tabela de referência CBR × k (MPa/m)</h4>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs text-gray-600">
          {[2, 5, 10, 15, 20, 30, 40, 50].map(c => (
            <div key={c} className="text-center">
              <span className="block font-medium">{c}%</span>
              <span className="text-blue-600">{cbrToK(c).toFixed(0)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
