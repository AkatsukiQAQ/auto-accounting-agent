import type { ReactNode } from 'react';

interface Props {
  /** Small all-caps tag above the title — context like "import" or "records". */
  eyebrow: string;
  /** Display title rendered in Fraunces serif. */
  title: string;
  /** Right-aligned action area (button cluster, etc.). */
  actions?: ReactNode;
  /** Optional one-line description under the title. */
  hint?: string;
}

export function PageHeader({ eyebrow, title, actions, hint }: Props) {
  return (
    <div className="mb-2 flex flex-wrap items-end justify-between gap-3">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">
          {eyebrow}
        </div>
        <h1 className="serif mt-0.5 text-3xl font-medium tracking-tight text-ink-900">
          {title}
        </h1>
        {hint ? <p className="mt-1 text-sm text-ink-500">{hint}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
