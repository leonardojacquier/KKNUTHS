import { CalculationResult, ProjectInput } from '../../types';
import StructureResults from './StructureResults';
import ConcreteResults from './ConcreteResults';
import ReinforcementResults from './ReinforcementResults';
import QuantityResults from './QuantityResults';
import AdditiveResults from './AdditiveResults';
import CompactionResults from './CompactionResults';
import DetailedProject from './DetailedProject';
import CrossSection from '../Drawings/CrossSection';
import PlanView from '../Drawings/PlanView';
import { Printer } from 'lucide-react';
import { useState } from 'react';

interface Props {
  result: CalculationResult;
  inputs: ProjectInput;
  onBack: () => void;
  onReset: () => void;
}

const TIPO_LABEL: Record<string, string> = {
  piso: 'Piso Industrial',
  aeroporto: 'Pavimento Aeroportuário',
  rodovia: 'Pavimento Rodoviário (PCC)',
};

type Tab = 'resumo' | 'estrutura' | 'concreto' | 'armadura' | 'compactacao' | 'projeto';

export default function ResultsPanel({ result, inputs, onBack, onReset }: Props) {
  const { alertas } = result;
  const [tab, setTab] = useState<Tab>('resumo');

  function handlePrint() { window.print(); }

  const totalH =
    (result.subbase?.espessura ?? 0) +
    (result.base?.espessura ?? 0) +
    result.placa.espessura;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'resumo', label: 'Resumo' },
    { id: 'estrutura', label: 'Estrutura' },
    { id: 'concreto', label: 'Concreto' },
    { id: 'armadura', label: 'Armadura / Fibras' },
    { id: 'compactacao', label: 'Compactação' },
    { id: 'projeto', label: 'Projeto Detalhado' },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header / Actions */}
      <div className="flex flex-wrap items-center justify-between mb-6 gap-3 no-print">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Resultados do Dimensionamento</h2>
          <p className="text-gray-500 text-sm">
            {TIPO_LABEL[inputs.tipo_pavimento]} · {inputs.nome_projeto} · {inputs.data}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handlePrint} className="btn-secondary flex items-center gap-2">
            <Printer size={16} /> Imprimir / PDF
          </button>
          <button onClick={onBack} className="btn-secondary">← Editar</button>
          <button onClick={onReset} className="btn-primary">Novo Projeto</button>
        </div>
      </div>

      {/* Alerts */}
      {alertas.length > 0 && (
        <div className="mb-6 space-y-2">
          {alertas.map((a, i) => (
            <div key={i} className={
              a.startsWith('ATENÇÃO') || a.startsWith('Erro') ? 'alert-error' :
              a.startsWith('ℹ') ? 'alert-info' :
              'alert-warning'
            }>
              {a.startsWith('ℹ') ? a : `⚠️ ${a}`}
            </div>
          ))}
        </div>
      )}

      {/* Summary card */}
      <div className="card mb-6 bg-blue-700 text-white">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <p className="text-blue-200 text-xs mb-1">Espessura da Placa</p>
            <p className="text-3xl font-bold">{result.placa.espessura} cm</p>
          </div>
          <div className="text-center">
            <p className="text-blue-200 text-xs mb-1">Espessura Total</p>
            <p className="text-3xl font-bold">{totalH} cm</p>
          </div>
          <div className="text-center">
            <p className="text-blue-200 text-xs mb-1">Concreto</p>
            <p className="text-3xl font-bold">C{inputs.concreto.fck}</p>
          </div>
          <div className="text-center">
            <p className="text-blue-200 text-xs mb-1">Fator de Segurança</p>
            <p className={`text-3xl font-bold ${result.placa.fator_seguranca < 1.0 ? 'text-red-300' : 'text-green-300'}`}>
              {result.placa.fator_seguranca.toFixed(2)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-blue-200 text-xs mb-1">
              {result.fibras ? 'Classe Fibra' : 'Armadura'}
            </p>
            <p className="text-xl font-bold">
              {result.fibras?.classe_desempenho
                ? `Classe ${result.fibras.classe_desempenho}`
                : result.armadura.malha
                  ? result.armadura.malha.tipo_malha
                  : result.armadura.armadura_temperatura
                    ? `∅${result.armadura.diametro_barra}@${result.armadura.espacamento}`
                    : 'Simples'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 mb-6 no-print border-b border-gray-200 pb-0">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
              tab === t.id
                ? 'border-blue-600 text-blue-700 bg-blue-50'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {t.label}
            {t.id === 'compactacao' && result.compactacao && (
              <span className="ml-1.5 bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {result.compactacao.camadas.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'resumo' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h3 className="section-title">Seção Transversal</h3>
              <CrossSection result={result} inputs={inputs} />
            </div>
            <div className="card">
              <h3 className="section-title">Vista em Planta – Layout de Juntas</h3>
              <PlanView result={result} inputs={inputs} />
            </div>
          </div>

          {/* Method notes */}
          <div className="card bg-gray-50">
            <h3 className="section-title">Notas de Cálculo</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
              <div>
                <p className="font-medium text-gray-700 mb-1">Método de Dimensionamento</p>
                <p>{result.placa.metodo}</p>
                <p className="font-mono text-xs bg-gray-100 px-2 py-1 rounded mt-1">{result.placa.equacao}</p>
              </div>
              <div>
                <p className="font-medium text-gray-700 mb-1">Parâmetros de Suporte</p>
                <p>CBR subleito: {result.subleito.cbr_projeto}%</p>
                <p>k subleito: {result.subleito.k_value.toFixed(1)} MPa/m</p>
                <p>k final (com camadas): {result.subleito.k_corrigido.toFixed(1)} MPa/m</p>
                <p>Raio de rigidez ℓ: {result.placa.raio_rigidez} m</p>
              </div>
              <div>
                <p className="font-medium text-gray-700 mb-1">Tensões de Projeto</p>
                <p>Tensão crítica: {result.placa.tensao_critica} MPa</p>
                <p>MR (flexo-tração): {result.concreto.fct_flex} MPa</p>
                <p>Tensão admissível: {result.placa.tensao_admissivel} MPa</p>
              </div>
              <div>
                <p className="font-medium text-gray-700 mb-1">Resistências do Concreto</p>
                <p>fck: {result.concreto.fck} MPa | fcj: {result.concreto.fcj} MPa</p>
                <p>fct (tração): {(result.concreto.fct_sp).toFixed(2)} MPa</p>
                <p>fct,f (flexo-tração): {result.concreto.fct_flex} MPa</p>
                <p>Ec: {result.concreto.modulo_elasticidade} GPa</p>
                {result.fibras && <p>Fibra {result.fibras.tipo}: {result.fibras.dosagem.toFixed(1)} kg/m³ | Classe {result.fibras.classe_desempenho}</p>}
              </div>
            </div>
          </div>
        </>
      )}

      {tab === 'estrutura' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <StructureResults result={result} />
          <QuantityResults result={result} inputs={inputs} />
        </div>
      )}

      {tab === 'concreto' && (
        <div className="space-y-6">
          <ConcreteResults result={result} />
          {result.aditivos && result.aditivos.aditivos_utilizados.length > 0 && (
            <AdditiveResults result={result} />
          )}
        </div>
      )}

      {tab === 'armadura' && (
        <ReinforcementResults result={result} />
      )}

      {tab === 'compactacao' && (
        <CompactionResults result={result} />
      )}

      {tab === 'projeto' && (
        <DetailedProject result={result} inputs={inputs} />
      )}
    </div>
  );
}
