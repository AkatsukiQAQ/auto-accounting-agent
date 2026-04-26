import type { ReactNode } from 'react';

type Tone = 'error' | 'info' | 'success' | 'warning';

interface Props {
  tone?: Tone;
  children: ReactNode;
}

const TONE: Record<Tone, string> = {
  error: 'bg-neg-50 text-neg-500 border-neg-500/30',
  info: 'bg-cream-100 text-ink-700 border-ink-200',
  success: 'bg-pos-50 text-pos-500 border-pos-500/30',
  warning: 'bg-cream-100 text-warn-500 border-warn-500/30',
};

export function Alert({ tone = 'info', children }: Props) {
  return (
    <div className={['rounded-lg border px-3 py-2 text-sm', TONE[tone]].join(' ')}>
      {children}
    </div>
  );
}
