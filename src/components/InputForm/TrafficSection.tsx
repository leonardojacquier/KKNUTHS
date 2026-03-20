import { ProjectInput, PavementType } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; tipo: PavementType; }

export default function TrafficSection({ data, onChange, tipo }: Props) {
  const traf = data.trafico;
  function setTraf(p: Partial<typeof traf>) {
    onChange({ trafico: { ...traf, ...p } });
  }

  if (tipo === 'rodovia') return (
    <div>
      <h2 className="section-title">Dados de Tráfego – Rodovia</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">N equivalente (×10⁶ eixos padrão)</label>
          <input type="number" className="input-field" step="0.1" min="0.01"
            value={traf.n_equivalente ?? 5}
            onChange={e => setTraf({ n_equivalente: parseFloat(e.target.value) })} />
          <p className="text-xs text-gray-400 mt-1">Número N de repetições do eixo padrão DNIT (80 kN)</p>
        </div>
        <div>
          <label className="label">Período de Projeto (anos)</label>
          <input type="number" className="input-field" min="5" max="50"
            value={traf.periodo_projeto ?? 20}
            onChange={e => setTraf({ periodo_projeto: parseInt(e.target.value) })} />
        </div>
      </div>
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
        <strong>Referência:</strong> O número N deve ser calculado conforme DNIT 005/2003-PRO.
        Para rodovias novas, usar N estimado com base no VMD (Volume Médio Diário) e FE (Fator de Eixo).
      </div>
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Faixas de N para referência:</h4>
        <div className="grid grid-cols-2 gap-1 text-xs text-gray-600">
          <span>N &lt; 10⁵ → Tráfego Leve (FS 1.30)</span>
          <span>N = 10⁶ → Tráfego Médio (FS 1.35)</span>
          <span>N = 10⁷ → Tráfego Pesado (FS 1.50)</span>
          <span>N &gt; 5×10⁷ → Tráfego Muito Pesado (FS 1.65)</span>
        </div>
      </div>
    </div>
  );

  if (tipo === 'aeroporto') return (
    <div>
      <h2 className="section-title">Dados de Tráfego – Aeroporto</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">Aeronave Crítica</label>
          <select className="input-field"
            value={traf.aeronave_critica ?? 'Boeing 737-800'}
            onChange={e => {
              const presets: Record<string, Partial<typeof traf>> = {
                'Boeing 737-800': { max_peso_decolagem: 790, carga_roda: 150, pressao_pneu: 1.2, num_rodas: 4 },
                'Airbus A320': { max_peso_decolagem: 780, carga_roda: 145, pressao_pneu: 1.15, num_rodas: 4 },
                'Boeing 777-300ER': { max_peso_decolagem: 3520, carga_roda: 280, pressao_pneu: 1.5, num_rodas: 12 },
                'Airbus A380': { max_peso_decolagem: 5750, carga_roda: 320, pressao_pneu: 1.47, num_rodas: 20 },
                'ATR-72': { max_peso_decolagem: 230, carga_roda: 55, pressao_pneu: 0.8, num_rodas: 4 },
                'Cessna Citation': { max_peso_decolagem: 73, carga_roda: 18, pressao_pneu: 0.6, num_rodas: 4 },
              };
              const p = presets[e.target.value] ?? {};
              setTraf({ aeronave_critica: e.target.value, ...p });
            }}>
            <option>Boeing 737-800</option>
            <option>Airbus A320</option>
            <option>Boeing 777-300ER</option>
            <option>Airbus A380</option>
            <option>ATR-72</option>
            <option>Cessna Citation</option>
          </select>
        </div>
        <div>
          <label className="label">MTOW – Peso Máximo de Decolagem (kN)</label>
          <input type="number" className="input-field"
            value={traf.max_peso_decolagem ?? 790}
            onChange={e => setTraf({ max_peso_decolagem: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Carga por Roda (kN)</label>
          <input type="number" className="input-field"
            value={traf.carga_roda ?? 150}
            onChange={e => setTraf({ carga_roda: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Pressão dos Pneus (MPa)</label>
          <input type="number" className="input-field" step="0.05"
            value={traf.pressao_pneu ?? 1.2}
            onChange={e => setTraf({ pressao_pneu: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Operações Anuais (movimentos)</label>
          <input type="number" className="input-field"
            value={traf.operacoes_anuais ?? 30000}
            onChange={e => setTraf({ operacoes_anuais: parseInt(e.target.value) })} />
        </div>
        <div>
          <label className="label">Período de Projeto (anos)</label>
          <input type="number" className="input-field" min="10" max="40"
            value={traf.periodo_projeto ?? 20}
            onChange={e => setTraf({ periodo_projeto: parseInt(e.target.value) })} />
        </div>
        <div>
          <label className="label">Tipo de Área</label>
          <select className="input-field"
            value={traf.tipo_pista ?? 'pista_principal'}
            onChange={e => setTraf({ tipo_pista: e.target.value as any })}>
            <option value="pista_principal">Pista Principal (RWY)</option>
            <option value="taxiway">Via de Táxi (TWY)</option>
            <option value="apron">Pátio de Aeronaves (Apron)</option>
          </select>
        </div>
      </div>
    </div>
  );

  // Piso industrial
  return (
    <div>
      <h2 className="section-title">Cargas de Projeto – Piso Industrial</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">Carga Concentrada (kN)</label>
          <input type="number" className="input-field"
            value={traf.carga_concentrada ?? 80}
            onChange={e => setTraf({ carga_concentrada: parseFloat(e.target.value) })} />
          <p className="text-xs text-gray-400 mt-1">Ex: pés de racks, pilares de estruturas</p>
        </div>
        <div>
          <label className="label">Carga Distribuída (kN/m²)</label>
          <input type="number" className="input-field"
            value={traf.carga_distribuida ?? 20}
            onChange={e => setTraf({ carga_distribuida: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Carga por Roda da Empilhadeira (kN)</label>
          <input type="number" className="input-field"
            value={traf.carga_empilhadeira ?? 100}
            onChange={e => setTraf({ carga_empilhadeira: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Distância entre Rodas Dianteiras (m)</label>
          <input type="number" className="input-field" step="0.1"
            value={traf.distancia_rodas ?? 1.2}
            onChange={e => setTraf({ distancia_rodas: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="label">Área de Contato por Roda (cm²)</label>
          <input type="number" className="input-field"
            value={traf.area_contato ?? 600}
            onChange={e => setTraf({ area_contato: parseFloat(e.target.value) })} />
        </div>
      </div>
      <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-800">
        <strong>Referência TR34:</strong> A carga crítica de projeto é a maior entre carga concentrada e carga por roda da empilhadeira.
        Para racks drive-in: considerar carga da estante na carga concentrada.
      </div>
    </div>
  );
}
