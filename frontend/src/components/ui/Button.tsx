import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

type Variant = 'primary' | 'outline' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

const VARIANT: Record<Variant, string> = {
  primary:
    'bg-ink-900 text-cream-50 hover:bg-ink-700 disabled:bg-ink-200 disabled:text-ink-500',
  outline:
    'bg-transparent text-ink-900 border border-ink-200 hover:bg-cream-100 disabled:text-ink-500',
  ghost:
    'bg-transparent text-ink-700 hover:bg-cream-100 disabled:text-ink-200',
  danger:
    'bg-neg-500 text-cream-50 hover:bg-red-700 disabled:bg-ink-200 disabled:text-ink-500',
};

const SIZE: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-5 text-base',
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'primary', size = 'md', className, leadingIcon, trailingIcon, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      {...rest}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-ink-900/30',
        'disabled:cursor-not-allowed',
        VARIANT[variant],
        SIZE[size],
        className ?? '',
      ].join(' ')}
    >
      {leadingIcon}
      {children}
      {trailingIcon}
    </button>
  );
});
