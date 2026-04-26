import { catBgClass, catDotClass } from '@/lib/cats';

interface Props {
  slug: string;
  label?: string;
  size?: 'sm' | 'md';
}

export function CatPill({ slug, label, size = 'md' }: Props) {
  const text = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full font-semibold text-ink-700',
        catBgClass(slug),
        text,
      ].join(' ')}
    >
      <span className={['inline-block h-1.5 w-1.5 rounded-full', catDotClass(slug)].join(' ')} />
      {label ?? slug}
    </span>
  );
}
