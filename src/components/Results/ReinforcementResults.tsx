import { CalculationResult } from '../../types';

interface Props { result: CalculationResult; }

export default function ReinforcementResults({ result }: Props) {
  const a = result.armadura;
  const f = result.fibras;

  return (
    <div className="card">
      <h3 className="section-title">Armadura, Fibras e Detalhes de Juntas</h3>

      {/* Fibras */}
      {f && (
        <div className="mb-4 p-3 border border-green-200 rounded-lg bg-green-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Reforço com Fibras – {f.tipo === 'steel' ? 'Fibra de Aço (SFRC)' : f.tipo === 'synthetic' ? 'Macro-Fibra Sintética' : 'Fibra Híbrida'}
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-2">
            <div className="bg-white p-2 rounded">
              <span className="text-gray-500 block text-xs">Dosagem</span>
              <span className="font-semibold text-green-700">{f.dosagem.toFixed(1)} kg/m³</span>
            </div>
            {f.comprimento && (
              <div className="bg-white p-2 rounded">
                <span className="text-gray-500 block text-xs">Geometria</span>
                <span className="font-semibold">{f.comprimento}mm × ∅{f.diametro}mm</span>
                <span className="text-xs text-gray-400"> L/d={f.esbeltez?.toFixed(0)}</span>
              </div>
            )}
            {f.fR1 !== undefined && (
              <div className="bg-white p-2 rounded">
                <span className="text-gray-500 block text-xs">fR1 / fR3</span>
                <span className="font-semibold">{f.fR1.toFixed(2)} / {f.fR3?.toFixed(2)} MPa</span>
              </div>
            )}
            {f.classe_desempenho && (
              <div className="bg-white p-2 rounded col-span-2">
                <span className="text-gray-500 block text-xs">Classe de Desempenho (fib MC2010)</span>
                <span className="font-bold text-green-700 text-base">{f.classe_desempenho}</span>
                <span className="text-xs text-gray-500 ml-2">{f.modelo_calculo}</span>
              </div>
            )}
          </div>
          {f.substitui_armadura_temperatura && (
            <p className="text-xs text-green-700 bg-white px-2 py-1 rounded border border-green-200">
              ✓ Dosagem atende critério TR34 – pode dispensar armadura de temperatura convencional
            </p>
          )}
          <div className="mt-2 text-xs text-gray-600 space-y-0.5">
            {f.observacoes.slice(0, 4).map((obs, i) => (
              <p key={i} className={obs.startsWith('⚠') ? 'text-amber-700' : obs.startsWith('✓') ? 'text-green-700' : ''}>
                {obs}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Armadura de temperatura / malha */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">
          {a.tipo === 'mesh' ? 'Malha Eletrossoldada (CA-60 / NBR 7480)' : 'Armadura de Temperatura/Retração'}
        </h4>
        {a.armadura_temperatura ? (
          <div>
            {a.malha ? (
              /* Malha eletrossoldada */
              <div className="space-y-1">
                <div className="result-item">
                  <span className="result-label">Tipo de Malha</span>
                  <span className="result-value font-bold">{a.malha.tipo_malha} (∅{a.malha.diametro_fio}@{a.malha.espacamento}mm)</span>
                </div>
                <div className="result-item">
                  <span className="result-label">As fornecida / requerida</span>
                  <span className="result-value">{(a.malha.as_fornecida/100).toFixed(2)} / {(a.malha.as_requerida/100).toFixed(2)} cm²/m</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Peso da malha</span>
                  <span className="result-value">{a.malha.peso_por_m2.toFixed(2)} kg/m²</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Folha padrão / Qtd estimada</span>
                  <span className="result-value">{a.malha.dimensoes_padrao} | {a.malha.folhas_por_placa} folhas (+10% emendas)</span>
                </div>
              </div>
            ) : (
              /* Barras individuais */
              <div className="space-y-1">
                <div className="result-item">
                  <span className="result-label">Bitola das barras</span>
                  <span className="result-value">∅ {a.diametro_barra} mm (CA-50)</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Espaçamento</span>
                  <span className="result-value">{a.espacamento} cm (nas 2 direções)</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Taxa de armadura</span>
                  <span className="result-value">{a.taxa_armadura.toFixed(3)}%</span>
                </div>
                <div className="result-item">
                  <span className="result-label">As calculado</span>
                  <span className="result-value">{a.as_calculado} cm²/m</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-3 bg-gray-50 rounded text-sm text-gray-500">
            {f?.substitui_armadura_temperatura
              ? '✓ Fibras atendem critério TR34 – armadura de temperatura dispensada'
              : 'Pavimento de concreto simples (sem armadura de temperatura)'}
            {result.concreto.consumo_fibras ? ' – reforço por fibras.' : '.'}
          </div>
        )}
      </div>

      {/* Armadura estrutural adicional */}
      {a.armadura_estrutural && a.as_estrutural && (
        <div className="mb-4 p-3 border border-orange-200 rounded-lg bg-orange-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Armadura Estrutural (CA-50)</h4>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="bg-white p-2 rounded">
              <span className="text-gray-500 block text-xs">Bitola</span>
              <span className="font-semibold">∅ {a.diametro_estrutural} mm</span>
            </div>
            <div className="bg-white p-2 rounded">
              <span className="text-gray-500 block text-xs">Espaçamento</span>
              <span className="font-semibold">{a.espacamento_estrutural} cm</span>
            </div>
            <div className="bg-white p-2 rounded">
              <span className="text-gray-500 block text-xs">As estrutural</span>
              <span className="font-semibold">{a.as_estrutural.toFixed(2)} cm²/m</span>
            </div>
          </div>
        </div>
      )}

      {/* Dowels */}
      {a.dowels && (
        <div className="mb-4 p-3 border border-blue-200 rounded-lg">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Barras de Transferência (Dowels) – CA-25 Liso</h4>
          <p className="text-xs text-gray-500 mb-2">Juntas transversais de contração – engaxetados</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Diâmetro</span>
              <span className="font-semibold">∅ {a.diametro_dowel} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Comprimento</span>
              <span className="font-semibold">{a.comprimento_dowel} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Espaçamento</span>
              <span className="font-semibold">{a.espacamento_dowel} cm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Posição</span>
              <span className="font-semibold">Meia-altura (h/2)</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Metade do comprimento engaxetada (deslizante) – permitir expansão/contração da junta.
            Aplicar graxa anti-aderente na metade livre. Encamisar ou usar capa deslizante.
          </p>
        </div>
      )}

      {/* Tie bars */}
      {a.tie_bars && (
        <div className="p-3 border border-purple-200 rounded-lg">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Barras de Ligação (Tie Bars) – CA-50 Nervurado</h4>
          <p className="text-xs text-gray-500 mb-2">Juntas longitudinais – solidárias (não deslizante)</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Diâmetro</span>
              <span className="font-semibold">∅ {a.diametro_tie_bar} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Comprimento</span>
              <span className="font-semibold">{a.comprimento_tie_bar} mm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Espaçamento</span>
              <span className="font-semibold">{a.espacamento_tie_bar} cm</span>
            </div>
            <div className="bg-gray-50 p-2 rounded">
              <span className="text-gray-500 block text-xs">Aço / Posição</span>
              <span className="font-semibold">CA-50 | Meia-altura</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
