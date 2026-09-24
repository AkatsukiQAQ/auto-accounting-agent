import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from '@/components/ui/Icon';
// Keep the full transparent character artwork intact and crop it in the 48px
// brand window, matching JobPilot. Previous Phase 1 marks live in
// `assets/archive/` and are intentionally not bundled.
import financeIconUrl from '@/assets/finance_icon.png';
import { useLocale } from '@/lib/locale';

interface Item {
  to: string;
  labelKey: string;
  icon: IconName;
  /** When true, render as a non-clickable preview (Phase 2/3 items). */
  upcoming?: boolean;
}

const GROUPS: { labelKey: string; items: Item[] }[] = [
  { labelKey: 'nav.group.budget', items: [
    { to: '/', labelKey: 'nav.dashboard', icon: 'home' },
    { to: '/plan', labelKey: 'nav.plan', icon: 'check' },
  ] },
  { labelKey: 'nav.group.activity', items: [
    { to: '/records', labelKey: 'nav.records', icon: 'list' },
    { to: '/import', labelKey: 'nav.import', icon: 'upload' },
    { to: '/categories', labelKey: 'nav.categories', icon: 'tag' },
  ] },
  { labelKey: 'nav.group.system', items: [
    { to: '/settings', labelKey: 'nav.settings', icon: 'settings' },
  ] },
];

export function SideNav() {
  const { t } = useLocale();
  return (
    <nav className="flex flex-row items-center gap-1 border-b border-cream-200 p-2 md:h-full md:w-60 md:flex-col md:items-stretch md:border-b-0 md:border-r md:p-4">
      {/* The source is a full character illustration. Draw it oversized and
          shift it so the compact brand mark shows the face and hat. */}
      <div className="hidden items-center gap-3 px-1 md:mb-6 md:flex">
        <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl bg-cream-200/50">
          <img
            src={financeIconUrl}
            alt=""
            aria-hidden="true"
            className="h-[112px] w-[112px] max-w-none -translate-x-[39px] -translate-y-px"
          />
        </div>
        <div className="mt-1 min-w-0">
          <div className="hand text-xl leading-[1.05] text-ink-900">Mita Finance</div>
          <div className="-mt-0.5 text-[10px] font-semibold uppercase leading-tight tracking-[0.12em] text-ink-500">
            {t('brand.tagline')}
          </div>
        </div>
      </div>

      {/* Nav list — horizontal on small screens, vertical on md+. */}
      <div className="flex w-full flex-row gap-1 overflow-x-auto md:flex-col">
        <NavLink to="/chat" className={({ isActive }) => [
          'mb-0 flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors md:mb-1 md:gap-3',
          isActive ? 'bg-cream-300 text-ink-900' : 'text-ink-700 hover:bg-cream-200/60',
        ].join(' ')}>
          <Icon name="message" size={18} /><span>{t('nav.chat')}</span>
        </NavLink>
        {GROUPS.map(group => <div key={group.labelKey} className="flex flex-row gap-1 md:flex-col">
          <div className="hidden px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-500 md:block">
            {t(group.labelKey)}
          </div>
          {group.items.map((item) => item.upcoming ? (
              <span key={item.to} title="Coming in a later phase" className="flex flex-shrink-0 cursor-default items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-ink-400 md:gap-3">
                <Icon name={item.icon} size={18} /><span>{t(item.labelKey)}</span>
                <span className="ml-auto hidden rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500 md:inline">Soon</span>
              </span>
            ) : (
              <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => [
                'flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors md:gap-3',
                isActive ? 'bg-cream-300 text-ink-900' : 'text-ink-700 hover:bg-cream-200/60',
              ].join(' ')}>
                <Icon name={item.icon} size={18} /><span>{t(item.labelKey)}</span>
              </NavLink>
            ))}
        </div>)}
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
