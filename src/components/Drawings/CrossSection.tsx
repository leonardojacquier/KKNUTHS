import { CalculationResult, ProjectInput } from '../../types';

interface Props {
  result: CalculationResult;
  inputs: ProjectInput;
}

export default function CrossSection({ result, inputs }: Props) {
  const { placa, base, subbase, subleito, armadura } = result;

  // SVG dimensions
  const W = 520;
  const H = 380;
  const margin = { left: 90, right: 20, top: 20, bottom: 50 };
  const drawW = W - margin.left - margin.right;

  // Layer heights (proportional, min 20px each)
  const totalH = placa.espessura + (base?.espessura ?? 0) + (subbase?.espessura ?? 0) + 80; // 80 for subleito
  const drawH = H - margin.top - margin.bottom;
  const scale = drawH / totalH;

  const slabH  = Math.max(placa.espessura * scale, 35);
  const baseH  = base ? Math.max(base.espessura * scale, 18) : 0;
  const sbH    = subbase ? Math.max(subbase.espessura * scale, 18) : 0;
  const soilH  = drawH - slabH - baseH - sbH;

  let y = margin.top;
  const slabY  = y;    y += slabH;
  const baseY  = y;    y += baseH;
  const sbY    = y;    y += sbH;
  const soilY  = y;

  const X = margin.left;

  // Dowel position
  const dowelY = slabY + slabH / 2;

  // Hatching patterns
  const patterns = [
    // Concrete: diagonal lines
    <pattern key="conc" id="hatch-conc" patternUnits="userSpaceOnUse" width="8" height="8">
      <line x1="0" y1="8" x2="8" y2="0" stroke="#94a3b8" strokeWidth="0.8" />
    </pattern>,
    // Base: dotted
    <pattern key="base" id="hatch-base" patternUnits="userSpaceOnUse" width="6" height="6">
      <circle cx="3" cy="3" r="1" fill="#a16207" />
    </pattern>,
    // Subbase: cross
    <pattern key="sb" id="hatch-sb" patternUnits="userSpaceOnUse" width="8" height="8">
      <line x1="0" y1="0" x2="8" y2="8" stroke="#ca8a04" strokeWidth="0.6" />
      <line x1="8" y1="0" x2="0" y2="8" stroke="#ca8a04" strokeWidth="0.6" />
    </pattern>,
    // Soil: random dots
    <pattern key="soil" id="hatch-soil" patternUnits="userSpaceOnUse" width="10" height="10">
      <circle cx="2" cy="3" r="1.5" fill="#92400e" opacity="0.5" />
      <circle cx="7" cy="7" r="1.2" fill="#92400e" opacity="0.4" />
      <circle cx="5" cy="1" r="1" fill="#78350f" opacity="0.3" />
    </pattern>,
  ];

  function Label({ x, y, text, sub, color }: { x: number; y: number; text: string; sub?: string; color?: string }) {
    return (
      <g>
        <text x={x} y={y} fontSize="11" fontWeight="600" fill={color ?? '#374151'} textAnchor="end">{text}</text>
        {sub && <text x={x} y={y + 12} fontSize="9" fill="#6b7280" textAnchor="end">{sub}</text>}
      </g>
    );
  }

  function DimLine({ x1, y1, x2, y2, label }: { x1: number; y1: number; x2: number; y2: number; label: string }) {
    const xd = W - 12;
    return (
      <g>
        <line x1={x2 + drawW} y1={y1} x2={xd} y2={y1} stroke="#94a3b8" strokeWidth="0.5" strokeDasharray="2,2" />
        <line x1={x2 + drawW} y1={y2} x2={xd} y2={y2} stroke="#94a3b8" strokeWidth="0.5" strokeDasharray="2,2" />
        <line x1={xd} y1={y1} x2={xd} y2={y2} stroke="#94a3b8" strokeWidth="1" markerStart="url(#arrow)" markerEnd="url(#arrow)" />
        <text x={xd + 4} y={(y1 + y2) / 2 + 4} fontSize="9" fill="#374151">{label}</text>
      </g>
    );
  }

  // Rebar positions (simplified)
  const hasRebar = armadura.armadura_temperatura && armadura.diametro_barra > 0;
  const rebarY1 = slabY + slabH * 0.3;
  const rebarY2 = slabY + slabH * 0.7;
  const rebarSpacing = 60;
  const rebarCount = Math.floor(drawW / rebarSpacing);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="border border-gray-200 rounded-lg bg-white">
      <defs>
        {patterns}
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" />
        </marker>
      </defs>

      {/* Title */}
      <text x={W / 2} y="14" fontSize="12" fontWeight="700" fill="#1e3a5f" textAnchor="middle">
        SEÇÃO TRANSVERSAL DO PAVIMENTO
      </text>

      {/* === SLAB === */}
      <rect x={X} y={slabY} width={drawW} height={slabH}
        fill="url(#hatch-conc)" stroke="#374151" strokeWidth="1.5" />
      <rect x={X} y={slabY} width={drawW} height={2} fill="#374151" />

      {/* Slab label */}
      <Label x={X - 5} y={slabY + slabH / 2 + 4}
        text={`Concreto C${inputs.concreto.fck}`}
        sub={`h = ${placa.espessura} cm`}
        color="#1e40af" />

      {/* Rebar inside slab */}
      {hasRebar && Array.from({ length: rebarCount }, (_, i) => {
        const rx = X + 20 + i * rebarSpacing;
        return rx < X + drawW - 10 ? (
          <g key={i}>
            <circle cx={rx} cy={rebarY1} r={4} fill="#dc2626" stroke="#991b1b" strokeWidth="0.5" />
            <circle cx={rx} cy={rebarY2} r={4} fill="#dc2626" stroke="#991b1b" strokeWidth="0.5" />
          </g>
        ) : null;
      })}

      {/* Fiber symbol (dots inside slab) */}
      {inputs.concreto.fibra_tipo !== 'none' && !hasRebar && (
        <>
          {Array.from({ length: 12 }, (_, i) => (
            <line key={i}
              x1={X + 15 + (i % 6) * 60 + (i > 5 ? 30 : 0)}
              y1={slabY + (i < 6 ? slabH * 0.35 : slabH * 0.65)}
              x2={X + 25 + (i % 6) * 60 + (i > 5 ? 30 : 0)}
              y2={slabY + (i < 6 ? slabH * 0.45 : slabH * 0.55)}
              stroke="#15803d" strokeWidth="1.5" />
          ))}
          <text x={X + drawW / 2} y={slabY + slabH / 2 + 4}
            fontSize="9" fill="#15803d" textAnchor="middle" fontWeight="600">
            SFRC – {inputs.concreto.fibra_dosagem} kg/m³
          </text>
        </>
      )}

      {/* === BASE === */}
      {base && (
        <>
          <rect x={X} y={baseY} width={drawW} height={baseH}
            fill="url(#hatch-base)" stroke="#92400e" strokeWidth="1" />
          <Label x={X - 5} y={baseY + baseH / 2 + 4}
            text="Base" sub={`h = ${base.espessura} cm`} color="#92400e" />
        </>
      )}

      {/* === SUBBASE === */}
      {subbase && (
        <>
          <rect x={X} y={sbY} width={drawW} height={sbH}
            fill="url(#hatch-sb)" stroke="#ca8a04" strokeWidth="1" />
          <Label x={X - 5} y={sbY + sbH / 2 + 4}
            text="Subbase" sub={`h = ${subbase.espessura} cm`} color="#ca8a04" />
        </>
      )}

      {/* === SOIL === */}
      <rect x={X} y={soilY} width={drawW} height={soilH}
        fill="url(#hatch-soil)" stroke="#78350f" strokeWidth="1" />
      <Label x={X - 5} y={soilY + soilH * 0.4 + 4}
        text="Subleito" sub={`CBR ${subleito.cbr_projeto}%`} color="#78350f" />

      {/* === DOWELS === */}
      {armadura.dowels && armadura.diametro_dowel && (
        <>
          {[0.25, 0.5, 0.75].map((frac, i) => {
            const dx = X + drawW * frac;
            return (
              <g key={i}>
                <line x1={dx - 20} y1={dowelY} x2={dx + 20} y2={dowelY}
                  stroke="#1d4ed8" strokeWidth={armadura.diametro_dowel! / 6} strokeLinecap="round" />
                {i === 1 && (
                  <text x={dx} y={dowelY - 6} fontSize="8" fill="#1d4ed8" textAnchor="middle">
                    Dowel ∅{armadura.diametro_dowel}mm @{armadura.espacamento_dowel}cm
                  </text>
                )}
              </g>
            );
          })}
        </>
      )}

      {/* === JOINT LINES === */}
      <line x1={X + drawW * 0.45} y1={slabY} x2={X + drawW * 0.45} y2={slabY + slabH * 0.7}
        stroke="#374151" strokeWidth="1" strokeDasharray="3,2" />
      <text x={X + drawW * 0.45 + 3} y={slabY + 10} fontSize="8" fill="#374151">Junta</text>

      {/* === DIMENSION LINE === */}
      {/* Total height */}
      <line x1={X + drawW + 5} y1={slabY} x2={X + drawW + 5} y2={soilY}
        stroke="#374151" strokeWidth="1" />
      <line x1={X + drawW + 2} y1={slabY} x2={X + drawW + 8} y2={slabY} stroke="#374151" strokeWidth="1" />
      <line x1={X + drawW + 2} y1={soilY} x2={X + drawW + 8} y2={soilY} stroke="#374151" strokeWidth="1" />
      <text
        x={X + drawW + 16} y={(slabY + soilY) / 2 + 4}
        fontSize="9" fill="#1e3a5f" fontWeight="600"
        transform={`rotate(-90, ${X + drawW + 16}, ${(slabY + soilY) / 2 + 4})`}>
        {placa.espessura + (base?.espessura ?? 0) + (subbase?.espessura ?? 0)} cm total
      </text>

      {/* === LEGEND === */}
      <g transform={`translate(${X}, ${H - 40})`}>
        <text x="0" y="0" fontSize="8" fontWeight="600" fill="#374151">LEGENDA:</text>
        <rect x="0" y="5" width="12" height="8" fill="url(#hatch-conc)" stroke="#374151" strokeWidth="0.5" />
        <text x="15" y="13" fontSize="8" fill="#374151">Concreto</text>
        {base && <>
          <rect x="65" y="5" width="12" height="8" fill="url(#hatch-base)" stroke="#92400e" strokeWidth="0.5" />
          <text x="80" y="13" fontSize="8" fill="#374151">Base</text>
        </>}
        {subbase && <>
          <rect x="105" y="5" width="12" height="8" fill="url(#hatch-sb)" stroke="#ca8a04" strokeWidth="0.5" />
          <text x="120" y="13" fontSize="8" fill="#374151">Subbase</text>
        </>}
        {armadura.dowels && <>
          <line x1="175" y1="9" x2="195" y2="9" stroke="#1d4ed8" strokeWidth="2" />
          <text x="198" y="13" fontSize="8" fill="#374151">Dowel</text>
        </>}
        {hasRebar && <>
          <circle cx="240" cy="9" r="4" fill="#dc2626" />
          <text x="247" y="13" fontSize="8" fill="#374151">Armadura</text>
        </>}
      </g>
    </svg>
  );
}
