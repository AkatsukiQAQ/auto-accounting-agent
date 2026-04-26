import type { HTMLAttributes, ReactNode } from 'react';

interface Props extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Adds the prototype's hover-lift effect (only useful on clickable cards). */
  hoverable?: boolean;
}

export function PaperCard({ children, hoverable, className, ...rest }: Props) {
  return (
    <div
      {...rest}
      className={[
        // .card-paper from index.css gives the warm brown shadow + 14px radius
        // + cream-50 surface that matches the prototype.
        'card-paper p-5',
        hoverable
          ? 'cursor-pointer transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md'
          : '',
        className ?? '',
      ].join(' ')}
    >
      {children}
    </div>
  );
}
