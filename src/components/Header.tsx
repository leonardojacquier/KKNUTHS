import { ChevronLeft, RotateCcw } from 'lucide-react';
import { PavementType } from '../types';

// ---- Logo GNH (SVG inline) ----
function LogoGNH({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 80" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Globe circle */}
      <circle cx="38" cy="44" r="30" stroke="#1B2A5E" strokeWidth="3.5" fill="none"/>
      {/* Latitude lines */}
      <ellipse cx="38" cy="44" rx="18" ry="30" stroke="#1B2A5E" strokeWidth="2" fill="none"/>
      <line x1="8" y1="44" x2="68" y2="44" stroke="#1B2A5E" strokeWidth="2"/>
      <line x1="11" y1="30" x2="65" y2="30" stroke="#1B2A5E" strokeWidth="1.5"/>
      <line x1="11" y1="58" x2="65" y2="58" stroke="#1B2A5E" strokeWidth="1.5"/>
      {/* Orange arc on top */}
      <path d="M 14 18 Q 38 4 62 18" stroke="#F26D21" strokeWidth="6" fill="none" strokeLinecap="round"/>
      {/* GNH text */}
      <text x="82" y="56" fontFamily="Arial, sans-serif" fontWeight="900" fontSize="30" fill="#1B2A5E" letterSpacing="1">GNH</text>
    </svg>
  );
}

// ---- Logo Titan Ingeniería (SVG inline) ----
function LogoTitan({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 130" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Gear outer shape */}
      <path d="M60 5 L67 2 L70 9 L78 8 L79 16 L87 17 L86 25 L93 28 L90 36 L96 41 L91 48 L95 55 L88 59 L89 67 L82 69 L80 77 L73 76 L68 83 L61 80 L54 83 L49 76 L42 77 L40 69 L33 67 L34 59 L27 55 L31 48 L26 41 L32 36 L29 28 L36 25 L35 17 L43 16 L44 8 L52 9 L55 2 Z"
        fill="#1a1a1a" />
      {/* Inner gear circle cut */}
      <circle cx="60" cy="42" r="38" fill="#1a1a1a"/>
      {/* Pavement stones background */}
      <circle cx="60" cy="42" r="33" fill="#333"/>
      {/* Orange stone top-right */}
      <path d="M60 14 L80 20 L82 38 L68 40 L58 28 Z" fill="#F26D21"/>
      {/* Black stone left */}
      <path d="M30 30 L56 28 L58 48 L36 52 L28 42 Z" fill="#1a1a1a"/>
      {/* Orange stone bottom-center */}
      <path d="M58 48 L82 44 L80 62 L62 68 L52 58 Z" fill="#F26D21"/>
      {/* Black stone bottom-left */}
      <path d="M30 50 L54 52 L52 70 L36 72 L26 62 Z" fill="#1a1a1a"/>
      {/* White joints */}
      <line x1="58" y1="14" x2="52" y2="72" stroke="white" strokeWidth="2"/>
      <line x1="28" y1="38" x2="84" y2="40" stroke="white" strokeWidth="2"/>
      <line x1="30" y1="54" x2="84" y2="50" stroke="white" strokeWidth="2"/>
      {/* Text TITAN INGENIERÍA */}
      <text x="60" y="105" fontFamily="Arial, sans-serif" fontWeight="900" fontSize="12" fill="#1a1a1a" textAnchor="middle" letterSpacing="0.5">TITAN</text>
      <text x="60" y="120" fontFamily="Arial, sans-serif" fontWeight="700" fontSize="9.5" fill="#1a1a1a" textAnchor="middle" letterSpacing="0.5">INGENIERÍA</text>
    </svg>
  );
}

interface HeaderProps {
  step: string;
  tipo: PavementType;
  onBack: () => void;
  onReset: () => void;
}

const TIPO_LABEL: Record<PavementType, string> = {
  piso: 'Piso Industrial',
  aeroporto: 'Pavimento Aeroportuário',
  rodovia: 'Pavimento Rodoviário (PCC)',
};

export default function Header({ step, tipo, onBack, onReset }: HeaderProps) {
  return (
    <header className="bg-[#1B2A5E] text-white shadow-lg no-print">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Left: logos + app name */}
        <div className="flex items-center gap-4">
          {/* Titan logo */}
          <LogoTitan className="h-12 w-auto" />
          {/* App name */}
          <div className="border-l border-white/20 pl-4">
            <h1 className="text-xl font-black leading-tight tracking-wide text-white">
              TITAN<span className="text-[#F26D21]">CALC</span>
            </h1>
            <p className="text-xs text-blue-200 leading-tight">Dimensionamento de Pavimentos Rígidos</p>
          </div>
        </div>

        {/* Right: GNH logo + nav */}
        <div className="flex items-center gap-4">
          <LogoGNH className="h-10 w-auto hidden sm:block" />
          <div className="flex items-center gap-3">
            {step !== 'select' && (
              <span className="hidden md:block text-xs bg-white/10 px-3 py-1 rounded-full">
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
