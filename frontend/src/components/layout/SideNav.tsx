import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from '@/components/ui/Icon';
// Brand icon — UI uses the small `logo.png` (~280 KB) optimized for sidebar
// display. The full-resolution archival copy is at `logo_raw.png` next to it,
// not bundled. Replace `logo.png` to swap; keep `logo_raw.png` as archive.
import logoUrl from '@/assets/logo.png';

interface Item {
  to: string;
  label: string;
  icon: IconName;
  /** When true, render as a non-clickable preview (Phase 2/3 items). */
  upcoming?: boolean;
}

const ITEMS: Item[] = [
  { to: '/', label: 'Dashboard', icon: 'home' },
  { to: '/records', label: 'Records', icon: 'list' },
  { to: '/import', label: 'Import', icon: 'upload' },
  // Phase 2 entries — visible but disabled so the roadmap is visually present.
  { to: '/review', label: 'Review', icon: 'alert', upcoming: true },
  { to: '/accounts', label: 'Accounts', icon: 'tag', upcoming: true },
  { to: '/recurring', label: 'Recurring', icon: 'list', upcoming: true },
  { to: '/budget', label: 'Budget & Goals', icon: 'check', upcoming: true },
  { to: '/categories', label: 'Categories', icon: 'tag' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
];

export function SideNav() {
  return (
    <nav className="flex flex-row items-center gap-1 border-b border-cream-200 p-2 md:h-full md:w-60 md:flex-col md:items-stretch md:border-b-0 md:border-r md:p-4">
      {/* Brand block — transparent logo on the page background, no tile. */}
      <div className="hidden items-center gap-3 px-1 md:mb-6 md:flex">
        <img
          src={logoUrl}
          alt="MITA"
          className="h-12 w-12 flex-shrink-0 object-contain"
        />
        <div className="mt-1 min-w-0">
          <div className="hand text-xl leading-[1.05] text-ink-900">MITA Finance</div>
          <div className="-mt-0.5 text-[10px] font-semibold uppercase leading-tight tracking-[0.12em] text-ink-500">
            Your finance assistant
          </div>
        </div>
      </div>

      {/* Nav list — horizontal on small screens, vertical on md+. */}
      <div className="flex w-full flex-row gap-1 overflow-x-auto md:flex-col">
        {ITEMS.map((item) =>
          item.upcoming ? (
            <span
              key={item.to}
              title="Coming in a later phase"
              className="flex flex-shrink-0 cursor-default items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-ink-400 md:gap-3"
            >
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
              <span className="ml-auto hidden rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500 md:inline">
                Soon
              </span>
            </span>
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors md:gap-3',
                  isActive
                    ? // Yellow paper highlight + ink text — matches the prototype's
                      // active state (NOT ink-on-cream inverse).
                      'bg-cream-300 text-ink-900'
                    : 'text-ink-700 hover:bg-cream-200/60',
                ].join(' ')
              }
            >
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
            </NavLink>
          ),
        )}
      </div>

      {/* Bottom collapse stub — wired to nothing for Phase 1, just visual. */}
      <button
        type="button"
        aria-label="Collapse sidebar"
        className="mt-auto hidden items-center gap-2 rounded-lg border border-cream-200 px-3 py-2 text-xs text-ink-500 hover:bg-cream-100 md:flex"
      >
        <Icon name="chevronRight" size={12} className="rotate-180" />
        <span>Collapse</span>
      </button>
    </nav>
  );
}
