// Default-seed slugs the backend ships. Used as fallback when a category
// hasn't been customized. The DB is the SSOT — these are visual hints only.
export const SEED_SLUGS = [
  'food',
  'transport',
  'shopping',
  'bills',
  'entertain',
  'health',
  'income',
  'rent',
  'other',
] as const;

export type SeedSlug = (typeof SEED_SLUGS)[number];

/** Tailwind class for category background color (read from theme tokens). */
export function catBgClass(slug: string): string {
  if ((SEED_SLUGS as readonly string[]).includes(slug)) {
    return `bg-cat-${slug}`;
  }
  return 'bg-cream-200';
}

/** Tailwind class for category dot/accent color. */
export function catDotClass(slug: string): string {
  if ((SEED_SLUGS as readonly string[]).includes(slug)) {
    return `bg-cat-${slug}-dot`;
  }
  return 'bg-ink-500';
}
