// Hand-rolled SVG line chart — port of design/design-references/src/charts.jsx LineChart.
// Tweaked: single series (expense), no jitter (cleaner Phase-1 look),
// Tailwind theme tokens via currentColor so callers can recolor.

interface DataPoint {
  label: string; // x-axis tick label
  value: number; // y value (in major units, e.g. 12.34)
}

interface Props {
  data: DataPoint[];
  width?: number;
  height?: number;
  currencySymbol?: string;
}

export function LineChart({ data, width = 520, height = 180, currencySymbol = '$' }: Props) {
  const pad = { t: 16, r: 16, b: 28, l: 48 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;

  if (data.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-xs text-ink-500"
      >
        No data yet
      </div>
    );
  }

  const maxY = Math.max(...data.map((d) => d.value), 1) * 1.1;
  const toX = (i: number) =>
    pad.l + (data.length === 1 ? w / 2 : (i / (data.length - 1)) * w);
  const toY = (v: number) => pad.t + h - (v / maxY) * h;

  const points = data.map((d, i) => [toX(i), toY(d.value)] as const);
  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
    .join(' ');
  const areaPath =
    linePath +
    ` L${points[points.length - 1][0]},${pad.t + h} L${points[0][0]},${pad.t + h} Z`;

  const gridYs = [0, 0.25, 0.5, 0.75, 1].map((f) => pad.t + h - f * h);

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Line chart"
    >
      <defs>
        <linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-neg-500)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--color-neg-500)" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* grid + y labels */}
      {gridYs.map((y, i) => (
        <g key={i}>
          <line
            x1={pad.l}
            x2={pad.l + w}
            y1={y}
            y2={y}
            stroke="var(--color-ink-200)"
            strokeWidth="1"
            strokeDasharray={i === gridYs.length - 1 ? '' : '3 4'}
          />
          <text
            x={pad.l - 8}
            y={y + 3}
            fontSize="10"
            textAnchor="end"
            fill="var(--color-ink-500)"
          >
            {currencySymbol}
            {Math.round(maxY * (1 - i * 0.25)).toLocaleString()}
          </text>
        </g>
      ))}

      {/* x ticks */}
      {data.map((d, i) => (
        <text
          key={i}
          x={toX(i)}
          y={pad.t + h + 16}
          fontSize="10"
          textAnchor="middle"
          fill="var(--color-ink-500)"
        >
          {d.label}
        </text>
      ))}

      {/* area + line */}
      <path d={areaPath} fill="url(#lineFill)" />
      <path
        d={linePath}
        fill="none"
        stroke="var(--color-neg-500)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p[0]}
          cy={p[1]}
          r="3"
          fill="var(--color-cream-50)"
          stroke="var(--color-neg-500)"
          strokeWidth="1.5"
        />
      ))}
    </svg>
  );
}
