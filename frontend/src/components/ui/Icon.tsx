// Minimal SVG icon set — handpicked subset of the prototype's primitives.jsx Icon.
// Only Phase-1 needs are inlined; new icons added on demand.

type IconName =
  | 'home'
  | 'list'
  | 'upload'
  | 'tag'
  | 'settings'
  | 'plus'
  | 'edit'
  | 'trash'
  | 'check'
  | 'x'
  | 'chevronRight'
  | 'image'
  | 'search'
  | 'alert';

const PATHS: Record<IconName, string> = {
  home: 'M3 12l9-9 9 9M5 10v10h14V10',
  list: 'M3 6h18M3 12h18M3 18h18',
  upload: 'M12 4v12M6 10l6-6 6 6M4 20h16',
  tag: 'M20 12l-8 8-9-9V4h7l10 8zM7 7h.01',
  settings: 'M12 8a4 4 0 100 8 4 4 0 000-8zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3h0a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8v0a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
  plus: 'M12 5v14M5 12h14',
  edit: 'M11 4H4v16h16v-7M18.5 2.5a2.121 2.121 0 113 3L12 15l-4 1 1-4 9.5-9.5z',
  trash: 'M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z',
  check: 'M20 6L9 17l-5-5',
  x: 'M18 6L6 18M6 6l12 12',
  chevronRight: 'M9 18l6-6-6-6',
  image: 'M21 19V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2zM8 13l3 3 5-7 5 6',
  search: 'M11 19a8 8 0 100-16 8 8 0 000 16zm10 2l-4.35-4.35',
  alert: 'M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z',
};

interface Props {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}

export function Icon({ name, size = 18, className, strokeWidth = 2 }: Props) {
  const d = PATHS[name];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export type { IconName };
