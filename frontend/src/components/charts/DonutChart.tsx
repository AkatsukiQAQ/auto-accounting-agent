// Hand-rolled SVG donut — port of design/design-references/src/charts.jsx DonutChart.
// Reads category dot colors from CSS theme tokens (--color-cat-*-dot).

interface Slice {
  slug: string;     // category slug (e.g. "food") — used for color lookup
  label: string;    // human label
  value: number;    // numeric weight
}

interface Props {
  data: Slice[];
  size?: number;
  innerRatio?: number;
  centerPrimary?: string;   // big number in the middle
  centerSecondary?: string; // line above (e.g. "This month")
}

const SEED_DOT_COLORS: Record<string, string> = {
  food: 'var(--color-cat-food-dot)',
  transport: 'var(--color-cat-transport-dot)',
  shopping: 'var(--color-cat-shopping-dot)',
  bills: 'var(--color-cat-bills-dot)',
  entertain: 'var(--color-cat-entertain-dot)',
  health: 'var(--color-cat-health-dot)',
  income: 'var(--color-cat-income-dot)',
  rent: 'var(--color-cat-rent-dot)',
  other: 'var(--color-cat-other-dot)',
};

export function DonutChart({
  data,
  size = 160,
  innerRatio = 0.62,
  centerPrimary,
  centerSecondary = 'This month',
}: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 6;
  const ir = r * innerRatio;
  const total = data.reduce((a, d) => a + d.value, 0);

  if (total <= 0) {
    return (
      <div
        style={{ width: size, height: size }}
        className="flex flex-col items-center justify-center text-xs text-ink-500"
      >
        <div>{centerSecondary}</div>
        <div>—</div>
      </div>
    );
  }

  let ang = -Math.PI / 2;
  const slices = data.map((d) => {
    const frac = d.value / total;
    const a0 = ang;
    const a1 = ang + frac * Math.PI * 2;
    ang = a1;
    const large = frac > 0.5 ? 1 : 0;
    const x0 = cx + Math.cos(a0) * r;
    const y0 = cy + Math.sin(a0) * r;
    const x1 = cx + Math.cos(a1) * r;
    const y1 = cy + Math.sin(a1) * r;
    const xi1 = cx + Math.cos(a1) * ir;
    const yi1 = cy + Math.sin(a1) * ir;
    const xi0 = cx + Math.cos(a0) * ir;
    const yi0 = cy + Math.sin(a0) * ir;
    return {
      path: `M${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1} L${xi1},${yi1} A${ir},${ir} 0 ${large} 0 ${xi0},${yi0} Z`,
      fill: SEED_DOT_COLORS[d.slug] ?? 'var(--color-ink-500)',
      label: d.label,
    };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Category donut chart"
    >
      {slices.map((s, i) => (
        <path
          key={i}
          d={s.path}
          fill={s.fill}
          stroke="var(--color-cream-50)"
          strokeWidth="2"
        >
          <title>{s.label}</title>
        </path>
      ))}
      <text
        x={cx}
        y={cy - 4}
        textAnchor="middle"
        fontSize="11"
        fill="var(--color-ink-500)"
      >
        {centerSecondary}
      </text>
      {centerPrimary !== undefined && (
        <text
          x={cx}
          y={cy + 14}
          textAnchor="middle"
          fontSize="16"
          fontWeight="700"
          fill="var(--color-ink-900)"
        >
          {centerPrimary}
        </text>
      )}
    </svg>
  );
}
