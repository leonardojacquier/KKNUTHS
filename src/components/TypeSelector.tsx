import { PavementType } from '../types';

interface TypeSelectorProps {
  onSelect: (t: PavementType) => void;
}

const TYPES = [
  {
    id: 'rodovia' as PavementType,
    title: 'Pavimento Rodoviário',
    subtitle: 'PUC – Pavimento de Uso Comum',
    description: 'Rodovias, vias urbanas, estacionamentos e pátios de veículos. Método DNIT baseado em Westergaard / PCA.',
    icon: '🛣️',
    tags: ['DNIT', 'Westergaard', 'PCA 1984', 'NBR 12655'],
    color: 'blue',
  },
  {
    id: 'aeroporto' as PavementType,
    title: 'Pavimento Aeroportuário',
    subtitle: 'Pistas, taxiways e pátios',
    description: 'Pavimentos para aeronaves civis e militares. Método FAA AC 150/5320-6 com verificação ICAO.',
    icon: '✈️',
    tags: ['FAA', 'ICAO', 'AC 150/5320-6', 'Westergaard'],
    color: 'indigo',
  },
  {
    id: 'piso' as PavementType,
    title: 'Piso Industrial',
    subtitle: 'Galpões, armazéns e plantas industriais',
    description: 'Pisos para empilhadeiras, racks, cargas uniformes e concentradas. Métodos TR34 e ACI 360R.',
    icon: '🏭',
    tags: ['TR34', 'ACI 360R', 'SFRC', 'Fibras'],
    color: 'orange',
  },
];

const COLOR_MAP: Record<string, string> = {
  blue: 'border-blue-200 hover:border-blue-500 hover:bg-blue-50',
  indigo: 'border-indigo-200 hover:border-indigo-500 hover:bg-indigo-50',
  orange: 'border-orange-200 hover:border-orange-500 hover:bg-orange-50',
};

const TAG_COLOR: Record<string, string> = {
  blue: 'bg-blue-100 text-blue-700',
  indigo: 'bg-indigo-100 text-indigo-700',
  orange: 'bg-orange-100 text-orange-700',
};

const BTN_COLOR: Record<string, string> = {
  blue: 'bg-blue-700 hover:bg-blue-800',
  indigo: 'bg-indigo-700 hover:bg-indigo-800',
  orange: 'bg-orange-600 hover:bg-orange-700',
};

export default function TypeSelector({ onSelect }: TypeSelectorProps) {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-3xl font-bold text-gray-800 mb-2">
          TITAN<span className="text-orange-500">CALC</span> – Selecione o Tipo de Pavimento
        </h2>
        <p className="text-gray-500 text-lg">
          Sistema completo de dimensionamento de pavimentos rígidos de concreto
        </p>
        <p className="text-xs text-gray-400 mt-1">Titan Ingeniería · GNH | Fibras · Aditivos · Compactação · Projeto Detalhado</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {TYPES.map((t) => (
          <div
            key={t.id}
            className={`card cursor-pointer border-2 transition-all ${COLOR_MAP[t.color]}`}
            onClick={() => onSelect(t.id)}
          >
            <div className="text-5xl mb-4">{t.icon}</div>
            <h3 className="text-xl font-bold text-gray-800 mb-1">{t.title}</h3>
            <p className="text-sm text-gray-500 font-medium mb-3">{t.subtitle}</p>
            <p className="text-sm text-gray-600 mb-5 min-h-[60px]">{t.description}</p>
            <div className="flex flex-wrap gap-1.5 mb-5">
              {t.tags.map((tag) => (
                <span key={tag} className={`badge ${TAG_COLOR[t.color]}`}>{tag}</span>
              ))}
            </div>
            <button
              className={`w-full text-white py-2.5 rounded-lg font-medium transition-colors ${BTN_COLOR[t.color]}`}
              onClick={() => onSelect(t.id)}
            >
              Calcular →
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 card bg-gray-50">
        <h4 className="font-semibold text-gray-700 mb-3">Normas e Referências Utilizadas</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-gray-600">
          <div>
            <p className="font-medium text-gray-700">Dimensionamento</p>
            <p>DNIT 005/2003-PRO</p>
            <p>Westergaard (1939)</p>
            <p>PCA (1984)</p>
            <p>FAA AC 150/5320-6</p>
            <p>TR34 / ACI 360R</p>
          </div>
          <div>
            <p className="font-medium text-gray-700">Concreto</p>
            <p>ABNT NBR 12655</p>
            <p>ABNT NBR 6118</p>
            <p>ABNT NBR 7480</p>
            <p>ACI 318</p>
          </div>
          <div>
            <p className="font-medium text-gray-700">Fibras</p>
            <p>ABNT NBR 15530</p>
            <p>fib Model Code 2010</p>
            <p>ACI 544.1R</p>
            <p>ASTM C1609</p>
          </div>
          <div>
            <p className="font-medium text-gray-700">Juntas</p>
            <p>PCA – Joint Design</p>
            <p>DNIT 047/2004</p>
            <p>ACI 360R-10</p>
            <p>ICAO Doc 9157</p>
          </div>
        </div>
      </div>
    </div>
  );
}
