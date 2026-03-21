import { useState } from 'react';
import { ProjectInput, CalculationResult, PavementType } from './types';
import { calcularPavimento } from './calculations';
import Header from './components/Header';
import TypeSelector from './components/TypeSelector';
import InputForm from './components/InputForm';
import ResultsPanel from './components/Results';
import { defaultInputs } from './utils/defaults';

type AppStep = 'select' | 'inputs' | 'results';

export default function App() {
  const [step, setStep] = useState<AppStep>('select');
  const [tipo, setTipo] = useState<PavementType>('rodovia');
  const [inputs, setInputs] = useState<ProjectInput>(defaultInputs('rodovia'));
  const [result, setResult] = useState<CalculationResult | null>(null);

  function handleSelectType(t: PavementType) {
    setTipo(t);
    setInputs(defaultInputs(t));
    setStep('inputs');
  }

  function handleCalculate(data: ProjectInput) {
    const res = calcularPavimento(data);
    setResult(res);
    setInputs(data);
    setStep('results');
  }

  function handleBack() {
    if (step === 'results') setStep('inputs');
    else if (step === 'inputs') setStep('select');
  }

  function handleReset() {
    setStep('select');
    setResult(null);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header step={step} tipo={tipo} onBack={handleBack} onReset={handleReset} />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {step === 'select' && (
          <TypeSelector onSelect={handleSelectType} />
        )}
        {step === 'inputs' && (
          <InputForm
            tipo={tipo}
            initialData={inputs}
            onSubmit={handleCalculate}
            onBack={() => setStep('select')}
          />
        )}
        {step === 'results' && result && (
          <ResultsPanel
            result={result}
            inputs={inputs}
            onBack={() => setStep('inputs')}
            onReset={handleReset}
          />
        )}
      </main>

      <footer className="text-center text-xs text-gray-400 py-4 border-t border-gray-200">
        <span className="font-semibold text-gray-500">TITAN<span className="text-orange-500">CALC</span></span> v2.0 –
        Dimensionamento de Pavimentos Rígidos de Concreto |
        DNIT · FAA · TR34 · fib MC2010 · NBR 12655 · NBR 6118
        <br />
        <span className="text-gray-400">Titan Ingeniería · GNH</span>
      </footer>
    </div>
  );
}
