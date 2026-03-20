import { useState } from 'react';
import { ProjectInput, PavementType } from '../../types';
import ProjectInfoSection from './ProjectInfoSection';
import TrafficSection from './TrafficSection';
import SubgradeSection from './SubgradeSection';
import LayersSection from './LayersSection';
import ConcreteSection from './ConcreteSection';
import GeometrySection from './GeometrySection';

interface InputFormProps {
  tipo: PavementType;
  initialData: ProjectInput;
  onSubmit: (data: ProjectInput) => void;
  onBack: () => void;
}

const SECTIONS = ['Projeto', 'Tráfego', 'Subleito', 'Camadas', 'Concreto', 'Geometria'];

export default function InputForm({ tipo, initialData, onSubmit, onBack }: InputFormProps) {
  const [data, setData] = useState<ProjectInput>(initialData);
  const [activeSection, setActiveSection] = useState(0);

  function update(partial: Partial<ProjectInput>) {
    setData(prev => ({ ...prev, ...partial }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(data);
  }

  const sections = [
    <ProjectInfoSection key="proj" data={data} onChange={update} />,
    <TrafficSection key="traf" data={data} onChange={update} tipo={tipo} />,
    <SubgradeSection key="sub" data={data} onChange={update} />,
    <LayersSection key="lay" data={data} onChange={update} tipo={tipo} />,
    <ConcreteSection key="conc" data={data} onChange={update} />,
    <GeometrySection key="geo" data={data} onChange={update} tipo={tipo} />,
  ];

  return (
    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
      {/* Section tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1 no-print">
        {SECTIONS.map((s, i) => (
          <button
            key={s}
            type="button"
            onClick={() => setActiveSection(i)}
            className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              i === activeSection
                ? 'bg-blue-700 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {i + 1}. {s}
          </button>
        ))}
      </div>

      {/* Active section */}
      <div className="card mb-6">
        {sections[activeSection]}
      </div>

      {/* Navigation */}
      <div className="flex justify-between no-print">
        <div>
          {activeSection > 0 && (
            <button type="button" className="btn-secondary" onClick={() => setActiveSection(s => s - 1)}>
              ← Anterior
            </button>
          )}
          {activeSection === 0 && (
            <button type="button" className="btn-secondary" onClick={onBack}>
              ← Tipo
            </button>
          )}
        </div>
        <div className="flex gap-3">
          {activeSection < SECTIONS.length - 1 ? (
            <button type="button" className="btn-primary" onClick={() => setActiveSection(s => s + 1)}>
              Próximo →
            </button>
          ) : (
            <button type="submit" className="btn-primary bg-green-700 hover:bg-green-800">
              🔢 Calcular Pavimento
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
