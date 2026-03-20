import { ProjectInput } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; }

export default function ConcreteSection({ data, onChange }: Props) {
  const conc = data.concreto;
  function setConc(p: Partial<typeof conc>) { onChange({ concreto: { ...conc, ...p } }); }

  const mr_est = (0.6 * Math.pow(conc.fck, 2/3)).toFixed(2);

  return (
    <div>
      <h2 className="section-title">Concreto e Fibras</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="label">fck do Concreto (MPa)</label>
          <input type="number" className="input-field" step="1" min="20" max="80"
            value={conc.fck}
            onChange={e => setConc({ fck: parseInt(e.target.value) })} />
          <p className="text-xs text-gray-400 mt-1">MR estimado: {mr_est} MPa</p>
        </div>
        <div>
          <label className="label">Tipo de Cimento</label>
          <select className="input-field" value={conc.tipo_cimento}
            onChange={e => setConc({ tipo_cimento: e.target.value as any })}>
            <option value="CP-V-ARI">CP-V-ARI (alta resistência inicial)</option>
            <option value="CP-II-F">CP-II-F (filler)</option>
            <option value="CP-II-E">CP-II-E (escória)</option>
            <option value="CP-II-Z">CP-II-Z (pozolana)</option>
            <option value="CP-III">CP-III (alto forno)</option>
            <option value="CP-IV">CP-IV (pozolânico)</option>
            <option value="CP-I">CP-I (comum)</option>
          </select>
        </div>
        <div>
          <label className="label">Classe de Agressividade (NBR 6118)</label>
          <select className="input-field" value={conc.classe_agressividade}
            onChange={e => setConc({ classe_agressividade: e.target.value as any })}>
            <option value="I">Classe I – Rural, seco (a/c ≤0.65)</option>
            <option value="II">Classe II – Urbano moderado (a/c ≤0.60)</option>
            <option value="III">Classe III – Agressivo, marinho (a/c ≤0.55)</option>
            <option value="IV">Classe IV – Muito agressivo (a/c ≤0.45)</option>
          </select>
        </div>
        <div>
          <label className="label">TMA – Diâmetro Máximo Agregado (mm)</label>
          <select className="input-field" value={conc.diametro_agregado}
            onChange={e => setConc({ diametro_agregado: parseInt(e.target.value) })}>
            <option value="9.5">9,5 mm (pedra 1)</option>
            <option value="12.5">12,5 mm</option>
            <option value="19">19 mm (pedra 1/2) – Recomendado</option>
            <option value="25">25 mm (pedra 1)</option>
            <option value="38">38 mm (pedra 2)</option>
          </select>
        </div>
        <div>
          <label className="label">Tipo de Agregado Graúdo</label>
          <select className="input-field" value={conc.tipo_agregado}
            onChange={e => setConc({ tipo_agregado: e.target.value as any })}>
            <option value="basalto">Basalto (2900-3100 kg/m³)</option>
            <option value="granito">Granito (2600-2700 kg/m³)</option>
            <option value="calcario">Calcário (2600-2750 kg/m³)</option>
            <option value="seixo">Seixo Rolado (2550-2650 kg/m³)</option>
          </select>
        </div>
        <div>
          <label className="label">Abatimento / Slump (mm)</label>
          <input type="number" className="input-field" step="10" min="30" max="200"
            value={conc.abatimento}
            onChange={e => setConc({ abatimento: parseInt(e.target.value) })} />
          <p className="text-xs text-gray-400 mt-1">Para pavimentos: 40–100 mm</p>
        </div>
      </div>

      {/* Fibras */}
      <h3 className="text-base font-semibold text-gray-700 mb-3 border-b pb-2">Reforço com Fibras</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="label">Tipo de Fibra</label>
          <select className="input-field" value={conc.fibra_tipo}
            onChange={e => setConc({ fibra_tipo: e.target.value as any })}>
            <option value="none">Sem fibras</option>
            <option value="steel">Fibra de Aço (SFRC)</option>
            <option value="synthetic">Fibra Sintética (Macro-PP/PVA)</option>
            <option value="both">Fibra de Aço + Sintética (híbrido)</option>
          </select>
        </div>
        {conc.fibra_tipo !== 'none' && (
          <div>
            <label className="label">Dosagem de Fibra (kg/m³)</label>
            <input type="number" className="input-field" step="1" min="0"
              value={conc.fibra_dosagem ?? (conc.fibra_tipo === 'synthetic' ? 4 : 25)}
              onChange={e => setConc({ fibra_dosagem: parseFloat(e.target.value) })} />
            <p className="text-xs text-gray-400 mt-1">
              {conc.fibra_tipo === 'steel' ? 'Fibra aço: 20-50 kg/m³' : 'Macro-sintética: 3-8 kg/m³'}
            </p>
          </div>
        )}
        {(conc.fibra_tipo === 'steel' || conc.fibra_tipo === 'both') && (
          <>
            <div>
              <label className="label">Comprimento da Fibra (mm)</label>
              <select className="input-field"
                value={conc.fibra_comprimento ?? 50}
                onChange={e => setConc({ fibra_comprimento: parseInt(e.target.value) })}>
                <option value="30">30 mm</option>
                <option value="35">35 mm</option>
                <option value="50">50 mm (Padrão)</option>
                <option value="60">60 mm</option>
                <option value="65">65 mm</option>
              </select>
            </div>
            <div>
              <label className="label">Diâmetro da Fibra (mm)</label>
              <select className="input-field"
                value={conc.fibra_diametro ?? 1.0}
                onChange={e => setConc({ fibra_diametro: parseFloat(e.target.value) })}>
                <option value="0.5">0,50 mm (esbeltez alta)</option>
                <option value="0.75">0,75 mm</option>
                <option value="0.9">0,90 mm</option>
                <option value="1.0">1,00 mm (Padrão)</option>
                <option value="1.05">1,05 mm</option>
              </select>
            </div>
          </>
        )}
      </div>

      {conc.fibra_tipo === 'steel' && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">
          <strong>NBR 15530 / fib MC2010:</strong> Fibra de aço conformada (hook-end ou crimped).
          Esbeltez L/d ≥ 60 recomendada. Classe de resistência residual a verificar por ensaio (EN 14651).
        </div>
      )}
    </div>
  );
}
