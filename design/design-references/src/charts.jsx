// Hand-drawn style charts. All SVG.
// Rough-ish stroke feel via filters + slight jitter; no libraries.

function roughJitter(points, amp = 0.6) {
  // Add tiny deterministic jitter so strokes don't look machine-perfect.
  return points.map(([x, y], i) => {
    const j = Math.sin(i * 12.9898) * 43758.5453 % 1;
    return [x + (j - 0.5) * amp * 2, y + (Math.cos(i * 7.1) * amp)];
  });
}

function LineChart({ data, width = 520, height = 180, currency = 'USD', theme = 'light' }) {
  const pad = { t: 20, r: 18, b: 28, l: 40 };
  const w = width - pad.l - pad.r, h = height - pad.t - pad.b;
  const maxE = Math.max(...data.map(d => d.expense), 100);
  const maxI = Math.max(...data.map(d => d.income), 100);
  const maxY = Math.max(maxE, maxI) * 1.1;

  const toX = i => pad.l + (i / (data.length - 1)) * w;
  const toY = v => pad.t + h - (v / maxY) * h;

  const expPts = roughJitter(data.map((d, i) => [toX(i), toY(d.expense)]), 0.4);
  const incPts = roughJitter(data.map((d, i) => [toX(i), toY(d.income)]), 0.4);

  const path = pts => pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const areaPath = pts => path(pts) + ` L${pts[pts.length - 1][0]},${pad.t + h} L${pts[0][0]},${pad.t + h} Z`;

  const gridYs = [0, 0.25, 0.5, 0.75, 1].map(f => pad.t + h - f * h);
  const sym = SYM[currency] || '$';

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id="expFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--neg-500)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--neg-500)" stopOpacity="0.02" />
        </linearGradient>
        <linearGradient id="incFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--pos-500)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--pos-500)" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* grid */}
      {gridYs.map((y, i) => (
        <g key={i}>
          <line x1={pad.l} x2={pad.l + w} y1={y} y2={y} stroke="var(--ink-200)" strokeWidth="1" strokeDasharray={i === gridYs.length - 1 ? '' : '3 4'} />
          <text x={pad.l - 8} y={y + 3} fontSize="10" textAnchor="end" fill="var(--ink-400)" fontFamily="var(--font-ui)">
            {sym}{Math.round((maxY * (1 - i * 0.25)) * (FX[currency] || 1))}
          </text>
        </g>
      ))}
      {/* X axis ticks */}
      {data.filter((_, i) => i % Math.ceil(data.length / 6) === 0).map((d, i, arr) => {
        const idx = data.indexOf(d);
        return (
          <text key={idx} x={toX(idx)} y={pad.t + h + 16} fontSize="10" textAnchor="middle" fill="var(--ink-400)" fontFamily="var(--font-ui)">
            {d.day !== undefined ? d.day : d.m}
          </text>
        );
      })}
      {/* expense area + line */}
      <path d={areaPath(expPts)} fill="url(#expFill)" />
      <path d={path(expPts)} fill="none" stroke="var(--neg-500)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      {/* income area + line */}
      <path d={areaPath(incPts)} fill="url(#incFill)" />
      <path d={path(incPts)} fill="none" stroke="var(--pos-500)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="0" />
      {/* highlight spike points */}
      {incPts.map((p, i) => data[i].income > 0 && (
        <circle key={i} cx={p[0]} cy={p[1]} r="3" fill="var(--cream-50)" stroke="var(--pos-500)" strokeWidth="1.5" />
      ))}
    </svg>
  );
}

function BarChart({ data, width = 520, height = 180, currency = 'USD' }) {
  const pad = { t: 16, r: 14, b: 28, l: 44 };
  const w = width - pad.l - pad.r, h = height - pad.t - pad.b;
  const maxY = Math.max(...data.map(d => Math.max(d.expense, d.income))) * 1.1;
  const group = w / data.length;
  const barW = Math.min(14, (group - 8) / 2);
  const toY = v => pad.t + h - (v / maxY) * h;
  const sym = SYM[currency] || '$';

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      {[0, 0.25, 0.5, 0.75, 1].map((f, i) => {
        const y = pad.t + h - f * h;
        return (
          <g key={i}>
            <line x1={pad.l} x2={pad.l + w} y1={y} y2={y} stroke="var(--ink-200)" strokeWidth="1" strokeDasharray={f === 0 ? '' : '3 4'} />
            <text x={pad.l - 8} y={y + 3} fontSize="10" textAnchor="end" fill="var(--ink-400)" fontFamily="var(--font-ui)">
              {sym}{Math.round(maxY * f * (FX[currency] || 1) / 1000)}k
            </text>
          </g>
        );
      })}
      {data.map((d, i) => {
        const gx = pad.l + i * group + group / 2;
        const eY = toY(d.expense), iY = toY(d.income);
        return (
          <g key={i}>
            <rect x={gx - barW - 2} y={iY} width={barW} height={pad.t + h - iY}
              fill="var(--pos-500)" opacity="0.85" rx="2" />
            <rect x={gx + 2} y={eY} width={barW} height={pad.t + h - eY}
              fill="var(--neg-500)" opacity="0.85" rx="2" />
            <text x={gx} y={pad.t + h + 16} fontSize="10" textAnchor="middle" fill="var(--ink-400)" fontFamily="var(--font-ui)">
              {d.m}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Donut for category breakdown
function DonutChart({ data, size = 160, innerRatio = 0.62, currency = 'USD' }) {
  const cx = size / 2, cy = size / 2;
  const r = size / 2 - 6;
  const ir = r * innerRatio;
  const total = data.reduce((a, d) => a + d.amt, 0);
  let ang = -Math.PI / 2;
  const sym = SYM[currency] || '$';

  const slices = data.map(d => {
    const frac = d.amt / total;
    const a0 = ang, a1 = ang + frac * Math.PI * 2;
    ang = a1;
    const large = frac > 0.5 ? 1 : 0;
    const x0 = cx + Math.cos(a0) * r, y0 = cy + Math.sin(a0) * r;
    const x1 = cx + Math.cos(a1) * r, y1 = cy + Math.sin(a1) * r;
    const xi1 = cx + Math.cos(a1) * ir, yi1 = cy + Math.sin(a1) * ir;
    const xi0 = cx + Math.cos(a0) * ir, yi0 = cy + Math.sin(a0) * ir;
    return {
      d: `M${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1} L${xi1},${yi1} A${ir},${ir} 0 ${large} 0 ${xi0},${yi0} Z`,
      fill: (CAT_COLORS[d.cat] || CAT_COLORS.Other).dot,
      cat: d.cat, pct: d.pct, amt: d.amt,
    };
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((s, i) => <path key={i} d={s.d} fill={s.fill} stroke="var(--cream-50)" strokeWidth="2" />)}
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize="11" fill="var(--ink-500)" fontFamily="var(--font-ui)">This month</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fontSize="18" fontWeight="700" fill="var(--ink-900)" fontFamily="var(--font-sans)">
        {sym}{Math.round(total * (FX[currency] || 1)).toLocaleString()}
      </text>
    </svg>
  );
}

Object.assign(window, { LineChart, BarChart, DonutChart });
