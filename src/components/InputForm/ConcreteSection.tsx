import { ProjectInput } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; }

export default function ConcreteSection({ data, onChange }: Props) {
  const conc = data.concreto;
  const ads = conc.aditivos ?? {};
  function setConc(p: Partial<typeof conc>) { onChange({ concreto: { ...conc, ...p } }); }
  function setAds(p: Partial<typeof ads>) { setConc({ aditivos: { ...ads, ...p } }); }

  const mr_est = (0.6 * Math.pow(conc.fck, 2/3)).toFixed(2);
  const tem_aditivos = Object.values(ads).some(v => v === true || (typeof v === 'number' && v > 0));

  return (
    <div>
      <h2 className="section-title">Concreto, Fibras e Aditivos</h2>

      {/* Concreto base */}
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
            <option value="steel">Fibra de Aço (SFRC – fib MC2010)</option>
            <option value="synthetic">Macro-Fibra Sintética (PP/PVA – TR34)</option>
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
              {conc.fibra_tipo === 'steel' ? 'Aço: 20-60 kg/m³ | Aeroporto: 35-50 kg/m³' : 'Macro-sintética: 3-8 kg/m³ (estrutural)'}
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
                <option value="50">50 mm (Padrão – esbeltez 50)</option>
                <option value="60">60 mm (Padrão – esbeltez 60)</option>
                <option value="65">65 mm</option>
              </select>
            </div>
            <div>
              <label className="label">Diâmetro da Fibra (mm)</label>
              <select className="input-field"
                value={conc.fibra_diametro ?? 1.0}
                onChange={e => setConc({ fibra_diametro: parseFloat(e.target.value) })}>
                <option value="0.5">0,50 mm (esbeltez máxima)</option>
                <option value="0.75">0,75 mm</option>
                <option value="0.9">0,90 mm</option>
                <option value="1.0">1,00 mm (Padrão)</option>
                <option value="1.05">1,05 mm</option>
              </select>
            </div>
          </>
        )}
      </div>
      {conc.fibra_tipo !== 'none' && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800 mb-6">
          <strong>Dimensionamento estrutural:</strong> A dosagem mínima será calculada automaticamente
          conforme fib MC2010 (aço) ou TR34 (sintética). Esbeltez L/d ≥ 60 recomendada.
          O sistema indicará a Classe de Desempenho alcançada e se pode substituir a armadura de temperatura.
        </div>
      )}

      {/* Aditivos */}
      <h3 className="text-base font-semibold text-gray-700 mb-3 border-b pb-2">
        Aditivos Químicos e Adições Minerais
        {tem_aditivos && <span className="ml-2 text-xs text-blue-600 font-normal">(aditivos ativos)</span>}
      </h3>

      {/* Redutores de água */}
      <div className="mb-4">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Redutores de Água / Plastificantes</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="plas" className="w-4 h-4 text-blue-600"
                checked={ads.plastificante ?? false}
                onChange={e => setAds({ plastificante: e.target.checked })} />
              <label htmlFor="plas" className="text-sm font-medium">Plastificante (ASTM C494 Tipo A)</label>
            </div>
            {ads.plastificante && (
              <div>
                <label className="label text-xs">Dosagem (% cimento)</label>
                <input type="number" className="input-field" step="0.05" min="0.1" max="0.8"
                  value={ads.plastificante_dosagem ?? 0.3}
                  onChange={e => setAds({ plastificante_dosagem: parseFloat(e.target.value) })} />
                <p className="text-xs text-gray-400">Reduz água 5-10% | 0.2-0.5%</p>
              </div>
            )}
          </div>
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="sp" className="w-4 h-4 text-blue-600"
                checked={ads.superplastificante ?? false}
                onChange={e => setAds({ superplastificante: e.target.checked })} />
              <label htmlFor="sp" className="text-sm font-medium">Superplastificante (ASTM C494 Tipo F/G)</label>
            </div>
            {ads.superplastificante && (
              <div>
                <label className="label text-xs">Dosagem (% cimento)</label>
                <input type="number" className="input-field" step="0.1" min="0.3" max="3.0"
                  value={ads.superplastificante_dosagem ?? 1.0}
                  onChange={e => setAds({ superplastificante_dosagem: parseFloat(e.target.value) })} />
                <p className="text-xs text-gray-400">Reduz água 12-30% | 0.5-2.0%</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modificadores de pega */}
      <div className="mb-4">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Modificadores de Pega</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="ret" className="w-4 h-4 text-blue-600"
                checked={ads.retardador ?? false}
                onChange={e => setAds({ retardador: e.target.checked })} />
              <label htmlFor="ret" className="text-sm font-medium">Retardador de Pega (Tipo B/D)</label>
            </div>
            {ads.retardador && (
              <div>
                <label className="label text-xs">Dosagem (% cimento)</label>
                <input type="number" className="input-field" step="0.05" min="0.1" max="0.8"
                  value={ads.retardador_dosagem ?? 0.3}
                  onChange={e => setAds({ retardador_dosagem: parseFloat(e.target.value) })} />
                <p className="text-xs text-gray-400">Clima quente, grandes áreas | 0.2-0.5%</p>
              </div>
            )}
          </div>
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="ace" className="w-4 h-4 text-blue-600"
                checked={ads.acelerador ?? false}
                onChange={e => setAds({ acelerador: e.target.checked })} />
              <label htmlFor="ace" className="text-sm font-medium">Acelerador de Pega (Tipo C/E)</label>
            </div>
            {ads.acelerador && (
              <div>
                <label className="label text-xs">Dosagem (% cimento)</label>
                <input type="number" className="input-field" step="0.1" min="0.5" max="3.0"
                  value={ads.acelerador_dosagem ?? 1.0}
                  onChange={e => setAds({ acelerador_dosagem: parseFloat(e.target.value) })} />
                <p className="text-xs text-gray-400">Clima frio, liberação rápida | 0.5-2.0%</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Incorporador de ar */}
      <div className="mb-4">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Incorporador de Ar</p>
        <div className="p-3 border rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <input type="checkbox" id="iar" className="w-4 h-4 text-blue-600"
              checked={ads.incorporador_ar ?? false}
              onChange={e => setAds({ incorporador_ar: e.target.checked })} />
            <label htmlFor="iar" className="text-sm font-medium">Incorporador de Ar (ASTM C260)</label>
          </div>
          {ads.incorporador_ar && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label text-xs">Dosagem (% cimento)</label>
                <input type="number" className="input-field" step="0.01" min="0.02" max="0.3"
                  value={ads.incorporador_ar_dosagem ?? 0.1}
                  onChange={e => setAds({ incorporador_ar_dosagem: parseFloat(e.target.value) })} />
              </div>
              <p className="text-xs text-gray-400 self-end pb-2">
                Gelo-degelo, sais | Teor ar: 4-7% | 0.05-0.2%
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Adições minerais */}
      <div className="mb-4">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Adições Minerais (Substituição ao Cimento)</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="sil" className="w-4 h-4 text-blue-600"
                checked={ads.silica_ativa ?? false}
                onChange={e => setAds({ silica_ativa: e.target.checked })} />
              <label htmlFor="sil" className="text-sm font-medium">Sílica Ativa</label>
            </div>
            {ads.silica_ativa && (
              <div>
                <label className="label text-xs">Teor (% subst.)</label>
                <input type="number" className="input-field" step="1" min="5" max="15"
                  value={ads.silica_ativa_teor ?? 8}
                  onChange={e => setAds({ silica_ativa_teor: parseInt(e.target.value) })} />
                <p className="text-xs text-gray-400">5-15% | Alta resist. e durabilidade</p>
              </div>
            )}
          </div>
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="cv" className="w-4 h-4 text-blue-600"
                checked={ads.cinza_volante ?? false}
                onChange={e => setAds({ cinza_volante: e.target.checked })} />
              <label htmlFor="cv" className="text-sm font-medium">Cinza Volante (Fly Ash)</label>
            </div>
            {ads.cinza_volante && (
              <div>
                <label className="label text-xs">Teor (% subst.)</label>
                <input type="number" className="input-field" step="5" min="10" max="35"
                  value={ads.cinza_volante_teor ?? 20}
                  onChange={e => setAds({ cinza_volante_teor: parseInt(e.target.value) })} />
                <p className="text-xs text-gray-400">15-30% | Econ. cimento, calor reduzido</p>
              </div>
            )}
          </div>
          <div className="p-3 border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input type="checkbox" id="esc" className="w-4 h-4 text-blue-600"
                checked={ads.escoria ?? false}
                onChange={e => setAds({ escoria: e.target.checked })} />
              <label htmlFor="esc" className="text-sm font-medium">Escória de Alto Forno (GGBS)</label>
            </div>
            {ads.escoria && (
              <div>
                <label className="label text-xs">Teor (% subst.)</label>
                <input type="number" className="input-field" step="5" min="20" max="70"
                  value={ads.escoria_teor ?? 40}
                  onChange={e => setAds({ escoria_teor: parseInt(e.target.value) })} />
                <p className="text-xs text-gray-400">30-60% | Resist. sulfatos, eco</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Micro-fibra PP */}
      <div className="mb-6">
        <div className="p-3 border rounded-lg">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="mpp" className="w-4 h-4 text-blue-600"
              checked={ads.micro_fibra_pp ?? false}
              onChange={e => setAds({ micro_fibra_pp: e.target.checked })} />
            <div>
              <label htmlFor="mpp" className="text-sm font-medium">Micro-fibra de PP (anti-fissuração plástica)</label>
              <p className="text-xs text-gray-400">0,9 kg/m³ fixo | Controle de retração plástica nas primeiras horas</p>
            </div>
          </div>
        </div>
      </div>

      {tem_aditivos && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
          <strong>Nota:</strong> Os efeitos dos aditivos (redução de água, aumento de resistência, teor de ar)
          serão calculados e exibidos nos resultados. Compatibilidade entre aditivos deve ser verificada
          com o fornecedor e por ensaios de dosagem (NBR 12820).
        </div>
      )}
    </div>
  );
}
