import { catBgClass, catDotClass } from '@/lib/cats';

interface Props {
  slug: string;
  label?: string;
  size?: 'sm' | 'md';
  icon?: string | null;
  imageUrl?: string | null;
}

const DEFAULT_ICONS: Record<string, string> = {
  food: '🍜', transport: '🚃', shopping: '🛍️', bills: '🧾', entertain: '🎮',
  health: '✚', income: '¥', rent: '⌂', other: '•', transfer: '↔',
};

export function CatPill({ slug, label, size = 'md', icon, imageUrl }: Props) {
  const text = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full font-semibold text-ink-700',
        catBgClass(slug),
        text,
      ].join(' ')}
    >
      {imageUrl ? <img src={imageUrl} alt="" className="size-3 rounded-sm object-cover" />
        : <span aria-hidden="true" className={['inline-grid size-3 place-items-center text-[10px]', icon || DEFAULT_ICONS[slug] ? '' : catDotClass(slug)].join(' ')}>{icon || DEFAULT_ICONS[slug] || '•'}</span>}
      {label ?? slug}
    </span>
  );
}
