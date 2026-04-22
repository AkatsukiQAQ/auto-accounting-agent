// Shared primitives for the MITA Finance prototype
// All components style with the cream/ink tokens defined in styles.css

// Lucide icon paths inlined so the prototype works offline / without ds/ being served
const ICON_DATA = {
  'arrow-up': '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
  'check': '<path d="M20 6 9 17l-5-5"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'chevron-left': '<path d="m15 18-6-6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  'clock': '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  'download': '<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>',
  'ellipsis': '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  'file': '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/>',
  'file-text': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M10 13h4"/><path d="M10 17h4"/><path d="M10 9h1"/>',
  'folder': '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  'image': '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
  'layout-grid': '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
  'link': '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  'list': '<path d="M3 5h.01"/><path d="M3 12h.01"/><path d="M3 19h.01"/><path d="M8 5h13"/><path d="M8 12h13"/><path d="M8 19h13"/>',
  'list-todo': '<rect x="3" y="5" width="6" height="6" rx="1"/><path d="m3 17 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
  'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  'paperclip': '<path d="M13.234 20.252 21 12.3"/><path d="m16 6-8.414 8.586a2 2 0 0 0 0 2.828 2 2 0 0 0 2.828 0l8.414-8.586a4 4 0 0 0 0-5.656 4 4 0 0 0-5.656 0l-8.415 8.585a6 6 0 1 0 8.486 8.486"/>',
  'pencil': '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
  'plus': '<path d="M5 12h14"/><path d="M12 5v14"/>',
  'refresh-ccw': '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  'settings': '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  'sparkles': '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
  'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
  'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
  'x': '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  'user': '<path d="M20 21a8 8 0 1 0-16 0"/><circle cx="12" cy="7" r="5"/>',
  'mail': '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  'eye': '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
};
const Icon = ({ name, size = 16, color = 'currentColor', className = '', style = {} }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    dangerouslySetInnerHTML={{ __html: ICON_DATA[name] || '' }} />
);

// ─── Currency formatting ────────────────────────────────────
const FX = { USD: 1, CNY: 7.12, JPY: 156.4, EUR: 0.92 };
const SYM = { USD: '$', CNY: '¥', JPY: '¥', EUR: '€' };
function fmtMoney(usd, currency = 'USD', opts = {}) {
  const v = usd * (FX[currency] || 1);
  const fractionDigits = currency === 'JPY' ? 0 : (opts.fractionDigits ?? 2);
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits });
  return `${v < 0 ? '−' : ''}${SYM[currency] || ''}${s}`;
}
// Inline component that forces the handwritten "num" font on any number/money string
const Num = ({ children, style = {}, className = '' }) => (
  <span className={`num ${className}`} style={style}>{children}</span>
);

// ─── Button ─────────────────────────────────────────────────
function APButton({ variant = 'primary', size = 'md', children, icon, iconRight, round, disabled, onClick, style = {} }) {
  const sizes = {
    sm: { height: 30, padding: '0 12px', fontSize: 13 },
    md: { height: 38, padding: '0 16px', fontSize: 14 },
    lg: { height: 44, padding: '0 20px', fontSize: 15 },
    icon: { width: 38, height: 38, padding: 0 },
    iconSm: { width: 32, height: 32, padding: 0 },
  };
  const variants = {
    primary:    { background: 'var(--ink-900)', color: 'var(--cream-50)', border: '1px solid var(--ink-900)' },
    accent:     { background: 'var(--accent-amber)', color: '#fff', border: '1px solid var(--accent-amber)' },
    cream:      { background: 'var(--cream-300)', color: 'var(--ink-900)', border: '1px solid var(--cream-400)' },
    secondary:  { background: 'var(--cream-200)', color: 'var(--ink-900)', border: '1px solid var(--ink-200)' },
    outline:    { background: 'var(--cream-50)', color: 'var(--ink-900)', border: '1px solid var(--ink-300)' },
    ghost:      { background: 'transparent', color: 'var(--ink-900)', border: '1px solid transparent' },
    danger:     { background: '#B8563E', color: '#fff', border: '1px solid #B8563E' },
  };
  return (
    <button disabled={disabled} onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7,
      fontFamily: 'var(--font-sans)', fontWeight: 500,
      cursor: disabled ? 'not-allowed' : 'pointer',
      borderRadius: round ? 9999 : 10,
      transition: 'all 150ms var(--ease)',
      opacity: disabled ? 0.45 : 1, whiteSpace: 'nowrap',
      ...sizes[size], ...variants[variant], ...style,
    }}>
      {icon && <Icon name={icon} size={size === 'sm' ? 13 : 15} />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === 'sm' ? 13 : 15} />}
    </button>
  );
}

// ─── Category pill ─────────────────────────────────────────
const CAT_COLORS = {
  Food:       { bg: '#FCE5CE', fg: '#8A4B1C', dot: '#D97706' },
  Transport:  { bg: '#DCE5F3', fg: '#2F4E84', dot: '#3B5EAA' },
  Shopping:   { bg: '#F4DCE8', fg: '#8A3A5F', dot: '#B56576' },
  Bills:      { bg: '#E5E0F3', fg: '#4A3F7A', dot: '#6B5BA8' },
  Entertain:  { bg: '#F9E6BD', fg: '#7A5A1C', dot: '#C99A33' },
  Health:     { bg: '#DDEED6', fg: '#3E5E33', dot: '#6E9455' },
  Income:     { bg: '#D7E8CD', fg: '#3A5A2B', dot: '#4F7B49' },
  Rent:       { bg: '#EEDFC8', fg: '#6E4C24', dot: '#9E6A37' },
  Other:      { bg: '#E9E4D8', fg: '#5E5441', dot: '#8B7E6C' },
};
function CatPill({ cat, size = 'md' }) {
  const c = CAT_COLORS[cat] || CAT_COLORS.Other;
  const sz = size === 'sm' ? { fontSize: 11, padding: '2px 8px' } : { fontSize: 12, padding: '3px 10px' };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, borderRadius: 9999,
      background: c.bg, color: c.fg, fontWeight: 600, ...sz }}>
      <span style={{ width: 6, height: 6, borderRadius: 3, background: c.dot }} />
      {cat}
    </span>
  );
}

// ─── Card ───────────────────────────────────────────────────
function PaperCard({ children, style = {}, padding = 20, onClick, hoverable }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      className="card-paper"
      style={{
        padding, transition: 'all 180ms var(--ease)',
        transform: hoverable && hover ? 'translateY(-2px)' : 'none',
        boxShadow: hoverable && hover ? '0 2px 4px rgba(95,75,40,.06), 0 16px 32px -14px rgba(95,75,40,.2)' : undefined,
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}>
      {children}
    </div>
  );
}

// ─── Sample data ───────────────────────────────────────────
const SAMPLE = {
  // Daily data: 30 days — expense, income in USD
  daily: (() => {
    const out = [];
    const exps = [42, 18, 65, 23, 87, 12, 54, 38, 72, 29, 48, 91, 16, 44, 58, 33, 68, 24, 52, 41, 79, 31, 47, 63, 22, 55, 38, 46, 72, 28];
    const incs = [0, 0, 0, 0, 0, 0, 1850, 0, 0, 0, 0, 0, 0, 0, 180, 0, 0, 0, 0, 0, 1850, 0, 0, 0, 0, 0, 0, 220, 0, 0];
    for (let i = 0; i < 30; i++) out.push({ day: i + 1, expense: exps[i], income: incs[i] });
    return out;
  })(),
  monthly: [
    { m: 'May',  expense: 1820, income: 4200 },
    { m: 'Jun',  expense: 2105, income: 4200 },
    { m: 'Jul',  expense: 2450, income: 4400 },
    { m: 'Aug',  expense: 1990, income: 4200 },
    { m: 'Sep',  expense: 2230, income: 4200 },
    { m: 'Oct',  expense: 2610, income: 4200 },
    { m: 'Nov',  expense: 2840, income: 4350 },
    { m: 'Dec',  expense: 3120, income: 5100 },
    { m: 'Jan',  expense: 1860, income: 4200 },
    { m: 'Feb',  expense: 2240, income: 4200 },
    { m: 'Mar',  expense: 2010, income: 4400 },
    { m: 'Apr',  expense: 1485, income: 4200 },
  ],
  transactions: [
    { id: 't1',  date: 'Apr 21', time: '12:34', merchant: 'Blue Bottle Coffee',  cat: 'Food',      amt: -7.25,   src: 'screenshot', note: 'Oat latte' },
    { id: 't2',  date: 'Apr 21', time: '08:12', merchant: 'Muni Metro',          cat: 'Transport', amt: -2.50,   src: 'screenshot' },
    { id: 't3',  date: 'Apr 20', time: '19:48', merchant: 'Trader Joe\'s',       cat: 'Food',      amt: -56.32,  src: 'manual' },
    { id: 't4',  date: 'Apr 20', time: '14:02', merchant: 'Kinokuniya Books',    cat: 'Shopping',  amt: -42.80,  src: 'screenshot' },
    { id: 't5',  date: 'Apr 19', time: '21:15', merchant: 'Netflix',             cat: 'Entertain', amt: -15.49,  src: 'recurring' },
    { id: 't6',  date: 'Apr 18', time: '09:00', merchant: 'Payroll — Acme Co.',  cat: 'Income',    amt:  2100.00, src: 'bank' },
    { id: 't7',  date: 'Apr 17', time: '13:22', merchant: 'Chipotle',            cat: 'Food',      amt: -14.60,  src: 'screenshot' },
    { id: 't8',  date: 'Apr 16', time: '07:45', merchant: 'Uber',                cat: 'Transport', amt: -18.30,  src: 'screenshot' },
    { id: 't9',  date: 'Apr 15', time: '10:00', merchant: 'PG&E',                cat: 'Bills',     amt: -88.20,  src: 'recurring' },
    { id: 't10', date: 'Apr 14', time: '18:05', merchant: 'Amazon',              cat: 'Shopping',  amt: -63.99,  src: 'screenshot', note: 'Desk lamp' },
    { id: 't11', date: 'Apr 13', time: '11:30', merchant: 'CVS Pharmacy',        cat: 'Health',    amt: -12.50,  src: 'screenshot' },
    { id: 't12', date: 'Apr 12', time: '20:10', merchant: 'Local Ramen',         cat: 'Food',      amt: -22.40,  src: 'manual' },
  ],
  categoryBreakdown: [
    { cat: 'Food',      amt: 412, pct: 28 },
    { cat: 'Rent',      amt: 520, pct: 35 },
    { cat: 'Transport', amt: 148, pct: 10 },
    { cat: 'Shopping',  amt: 186, pct: 12 },
    { cat: 'Bills',     amt: 128, pct: 9  },
    { cat: 'Entertain', amt:  91, pct:  6 },
  ],
  // Agent insights
  insights: [
    { id: 'i1', tone: 'warn',  title: 'Coffee spend up 42%',       body: 'You\'ve spent $68 on coffee this month vs. $48 last month. At this pace, that\'s ~$820/yr.', action: 'Set a $50/mo cap' },
    { id: 'i2', tone: 'good',  title: 'Groceries trending down',   body: 'Trader Joe\'s runs replaced 2 DoorDash orders/wk — saving ~$95/mo.', action: 'Keep it up' },
    { id: 'i3', tone: 'info',  title: 'Unused subscription?',      body: 'Netflix hasn\'t been opened (per your usage) in 21 days. $15.49/mo.', action: 'Review' },
    { id: 'i4', tone: 'info',  title: 'Payday lands Friday',       body: 'Historical pattern: you overspend 18% in the 3 days after payday.', action: 'Auto-transfer $400 to savings?' },
  ],
};

Object.assign(window, { Icon, fmtMoney, SYM, FX, APButton, CatPill, PaperCard, SAMPLE, CAT_COLORS });
