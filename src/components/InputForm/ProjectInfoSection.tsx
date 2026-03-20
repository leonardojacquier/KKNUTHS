import { ProjectInput } from '../../types';

interface Props { data: ProjectInput; onChange: (p: Partial<ProjectInput>) => void; }

export default function ProjectInfoSection({ data, onChange }: Props) {
  return (
    <div>
      <h2 className="section-title">Informações do Projeto</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">Nome do Projeto</label>
          <input className="input-field" value={data.nome_projeto}
            onChange={e => onChange({ nome_projeto: e.target.value })} />
        </div>
        <div>
          <label className="label">Responsável Técnico</label>
          <input className="input-field" value={data.responsavel}
            onChange={e => onChange({ responsavel: e.target.value })} placeholder="Eng. / CREA" />
        </div>
        <div>
          <label className="label">Localização</label>
          <input className="input-field" value={data.localizacao}
            onChange={e => onChange({ localizacao: e.target.value })} placeholder="Cidade/UF" />
        </div>
        <div>
          <label className="label">Data do Projeto</label>
          <input type="date" className="input-field" value={data.data}
            onChange={e => onChange({ data: e.target.value })} />
        </div>
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
        <h3 className="font-medium text-blue-800 mb-2">Tipo de Pavimento Selecionado</h3>
        <div className="flex gap-3">
          {(['rodovia', 'aeroporto', 'piso'] as const).map(t => (
            <label key={t} className="flex items-center gap-2 cursor-pointer">
              <input type="radio" name="tipo" value={t}
                checked={data.tipo_pavimento === t}
                onChange={() => {}}
                readOnly
                className="text-blue-600" />
              <span className="text-sm capitalize">
                {t === 'rodovia' ? 'Rodovia (PUC)' : t === 'aeroporto' ? 'Aeroporto' : 'Piso Industrial'}
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
