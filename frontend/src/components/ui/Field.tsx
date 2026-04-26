import type { ReactNode } from 'react';

export const inputClass =
  'w-full rounded-lg border border-ink-200 bg-cream-50 px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/20';

interface Props {
  label: string;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, hint, children }: Props) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-ink-500">
        {label}
      </span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-ink-500">{hint}</span> : null}
    </label>
  );
}
