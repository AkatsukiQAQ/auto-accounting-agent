// Money formatting — pulled from design/design-references/src/primitives.jsx

const SYM: Record<string, string> = {
  USD: '$',
  CNY: '¥',
  JPY: '¥',
  EUR: '€',
  GBP: '£',
  HKD: 'HK$',
  KRW: '₩',
};

/** Format a signed cents amount as `$12.34` / `¥725` (JPY has no minor unit). */
export function fmtMoney(amountCents: number, currency: string): string {
  const symbol = SYM[currency] ?? currency + ' ';
  const sign = amountCents < 0 ? '-' : '';
  const abs = Math.abs(amountCents);
  if (currency === 'JPY' || currency === 'KRW') {
    // Whole-yen display; the cents storage convention still applies.
    return `${sign}${symbol}${Math.round(abs / 100).toLocaleString()}`;
  }
  const major = Math.floor(abs / 100);
  const minor = String(abs % 100).padStart(2, '0');
  return `${sign}${symbol}${major.toLocaleString()}.${minor}`;
}

/** Returns "+" or "-" or "" for stylistic prefixes. */
export function signOf(amountCents: number): '+' | '-' | '' {
  if (amountCents > 0) return '+';
  if (amountCents < 0) return '-';
  return '';
}

export { SYM };
