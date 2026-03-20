import { ChevronLeft, RotateCcw, Building2 } from 'lucide-react';
import { PavementType } from '../types';

interface HeaderProps {
  step: string;
  tipo: PavementType;
  onBack: () => void;
  onReset: () => void;
}

const TIPO_LABEL: Record<PavementType, string> = {
  piso: 'Piso Industrial',
  aeroporto: 'Pavimento Aeroportuário',
  rodovia: 'Pavimento Rodoviário (PUC)',
};

export default function Header({ step, tipo, onBack, onReset }: HeaderProps) {
  return (
    <header className="bg-blue-800 text-white shadow-lg no-print">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Building2 size={28} className="text-blue-200" />
          <div>
            <h1 className="text-lg font-bold leading-tight">PavCalc</h1>
            <p className="text-xs text-blue-200 leading-tight">Dimensionamento de Pavimentos Rígidos</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {step !== 'select' && (
            <span className="hidden sm:block text-xs bg-blue-700 px-3 py-1 rounded-full">
              {TIPO_LABEL[tipo]}
            </span>
          )}
          {step !== 'select' && (
            <button onClick={onBack} className="flex items-center gap-1 text-sm text-blue-200 hover:text-white transition-colors">
              <ChevronLeft size={16} /> Voltar
            </button>
          )}
          {step === 'results' && (
            <button onClick={onReset} className="flex items-center gap-1 text-sm text-blue-200 hover:text-white transition-colors">
              <RotateCcw size={14} /> Novo
            </button>
          )}
        </div>
      </div>

      {/* Step indicator */}
      {step !== 'select' && (
        <div className="max-w-7xl mx-auto px-4 pb-2">
          <div className="flex gap-2 text-xs text-blue-300">
            <span className={step === 'inputs' ? 'text-white font-semibold' : ''}>1. Dados de Entrada</span>
            <span>→</span>
            <span className={step === 'results' ? 'text-white font-semibold' : ''}>2. Resultados e Projeto</span>
          </div>
        </div>
      )}
    </header>
  );
}
