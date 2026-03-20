import { CalculationResult, ProjectInput } from '../../types';

interface Props {
  result: CalculationResult;
  inputs: ProjectInput;
}

export default function PlanView({ result, inputs }: Props) {
  const { armadura } = result;
  const geo = inputs.geometria;

  const W = 520;
  const H = 360;
  const margin = { left: 60, right: 30, top: 30, bottom: 50 };
  const drawW = W - margin.left - margin.right;
  const drawH = H - margin.top - margin.bottom;
  const X0 = margin.left;
  const Y0 = margin.top;

  // Scale
  const scaleX = drawW / geo.comprimento_placa;
  const scaleY = drawH / geo.largura_placa;

  // Joints in X (transversal)
  const juncoes_x: number[] = [];
  let cx = geo.espaco_junta_transversal;
  while (cx < geo.comprimento_placa) {
    juncoes_x.push(cx);
    cx += geo.espaco_junta_transversal;
  }

  // Joints in Y (longitudinal)
  const juncoes_y: number[] = [];
  let cy = geo.espaco_junta_longitudinal;
  while (cy < geo.largura_placa) {
    juncoes_y.push(cy);
    cy += geo.espaco_junta_longitudinal;
  }

  const num_juntas_x = juncoes_x.length;
  const num_juntas_y = juncoes_y.length;
  const num_placas_x = num_juntas_x + 1;
  const num_placas_y = num_juntas_y + 1;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="border border-gray-200 rounded-lg bg-white">
      <defs>
        <pattern id="grid-bg" patternUnits="userSpaceOnUse" width="20" height="20">
          <path d="M20,0 L0,0 0,20" fill="none" stroke="#f3f4f6" strokeWidth="0.5" />
        </pattern>
      </defs>

      {/* Background grid */}
      <rect x={X0} y={Y0} width={drawW} height={drawH} fill="url(#grid-bg)" />

      {/* Title */}
      <text x={W / 2} y="18" fontSize="11" fontWeight="700" fill="#1e3a5f" textAnchor="middle">
        VISTA EM PLANTA – LAYOUT DE JUNTAS
      </text>

      {/* Outer border */}
      <rect x={X0} y={Y0} width={drawW} height={drawH}
        fill="#e8ecf3" stroke="#374151" strokeWidth="2" />

      {/* Slab fill (alternate colors for visibility) */}
      {Array.from({ length: num_placas_x }, (_, i) =>
        Array.from({ length: num_placas_y }, (_, j) => {
          const x1 = X0 + (i === 0 ? 0 : juncoes_x[i - 1]) * scaleX;
          const x2 = X0 + (i < num_juntas_x ? juncoes_x[i] : geo.comprimento_placa) * scaleX;
          const y1 = Y0 + (j === 0 ? 0 : juncoes_y[j - 1]) * scaleY;
          const y2 = Y0 + (j < num_juntas_y ? juncoes_y[j] : geo.largura_placa) * scaleY;
          const isEven = (i + j) % 2 === 0;
          return (
            <rect key={`${i}-${j}`} x={x1} y={y1} width={x2 - x1} height={y2 - y1}
              fill={isEven ? '#dbeafe' : '#e0e7ff'} stroke="none" />
          );
        })
      )}

      {/* Transversal joints (vertical lines) */}
      {juncoes_x.map((xv, i) => {
        const px = X0 + xv * scaleX;
        const isContraction = true;
        return (
          <g key={`tx-${i}`}>
            <line x1={px} y1={Y0} x2={px} y2={Y0 + drawH}
              stroke={isContraction ? '#1d4ed8' : '#dc2626'} strokeWidth="1.5"
              strokeDasharray={isContraction ? 'none' : '4,2'} />
          </g>
        );
      })}

      {/* Longitudinal joints (horizontal lines) */}
      {juncoes_y.map((yv, i) => {
        const py = Y0 + yv * scaleY;
        return (
          <line key={`ty-${i}`} x1={X0} y1={py} x2={X0 + drawW} y2={py}
            stroke="#7c3aed" strokeWidth="1.5" />
        );
      })}

      {/* Dowels on transversal joints */}
      {armadura.dowels && juncoes_x.slice(0, Math.min(juncoes_x.length, 5)).map((xv, i) => {
        const px = X0 + xv * scaleX;
        const spacing_px = (armadura.espacamento_dowel ?? 30) / 100 * scaleY;
        const numDow = Math.min(Math.floor(drawH / spacing_px), 8);
        return Array.from({ length: numDow }, (_, j) => {
          const dy = Y0 + (j + 0.5) * (drawH / numDow);
          return (
            <circle key={`dow-${i}-${j}`} cx={px} cy={dy} r={3}
              fill="#1d4ed8" stroke="white" strokeWidth="1" />
          );
        });
      })}

      {/* Tie bars on longitudinal joints */}
      {armadura.tie_bars && juncoes_y.slice(0, Math.min(juncoes_y.length, 4)).map((yv, i) => {
        const py = Y0 + yv * scaleY;
        const spacing_px = (armadura.espacamento_tie_bar ?? 75) / 100 * scaleX;
        const numTie = Math.min(Math.floor(drawW / spacing_px), 8);
        return Array.from({ length: numTie }, (_, j) => {
          const tx = X0 + (j + 0.5) * (drawW / numTie);
          return (
            <rect key={`tie-${i}-${j}`} x={tx - 3} y={py - 1} width={6} height={3}
              fill="#7c3aed" />
          );
        });
      })}

      {/* Dimension arrows */}
      {/* Width (X) */}
      <line x1={X0} y1={Y0 + drawH + 15} x2={X0 + drawW} y2={Y0 + drawH + 15} stroke="#374151" strokeWidth="1" markerEnd="url(#arrowBlack)" />
      <text x={(X0 + X0 + drawW) / 2} y={Y0 + drawH + 30} fontSize="10" fill="#374151" textAnchor="middle" fontWeight="600">
        {geo.comprimento_placa} m ({num_placas_x} placas × {geo.espaco_junta_transversal} m)
      </text>

      {/* Height (Y) */}
      <line x1={X0 - 15} y1={Y0} x2={X0 - 15} y2={Y0 + drawH} stroke="#374151" strokeWidth="1" />
      <text x={X0 - 25} y={Y0 + drawH / 2} fontSize="10" fill="#374151" textAnchor="middle" fontWeight="600"
        transform={`rotate(-90, ${X0 - 25}, ${Y0 + drawH / 2})`}>
        {geo.largura_placa} m ({num_placas_y} × {geo.espaco_junta_longitudinal} m)
      </text>

      {/* Label first slab */}
      <text x={X0 + 5} y={Y0 + 16} fontSize="9" fill="#374151">
        {geo.espaco_junta_transversal}×{geo.espaco_junta_longitudinal}m
      </text>

      {/* Arrow marker */}
      <defs>
        <marker id="arrowBlack" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L0,8 L8,4 z" fill="#374151" />
        </marker>
      </defs>

      {/* Legend */}
      <g transform={`translate(${X0}, ${H - 38})`}>
        <line x1="0" y1="6" x2="18" y2="6" stroke="#1d4ed8" strokeWidth="2" />
        <text x="22" y="10" fontSize="8" fill="#374151">Junta Transv.</text>
        <line x1="90" y1="6" x2="108" y2="6" stroke="#7c3aed" strokeWidth="2" />
        <text x="112" y="10" fontSize="8" fill="#374151">Junta Long.</text>
        {armadura.dowels && <>
          <circle cx="185" cy="6" r="4" fill="#1d4ed8" />
          <text x="192" y="10" fontSize="8" fill="#374151">Dowel</text>
        </>}
        {armadura.tie_bars && <>
          <rect x="230" y="3" width="10" height="5" fill="#7c3aed" />
          <text x="244" y="10" fontSize="8" fill="#374151">Tie Bar</text>
        </>}
        <text x="300" y="10" fontSize="8" fill="#374151" fontWeight="600">
          Total: {num_placas_x * num_placas_y} placas
        </text>
      </g>
    </svg>
  );
}
