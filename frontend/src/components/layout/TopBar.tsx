import { Link } from 'react-router-dom';
import { Icon } from '@/components/ui/Icon';
import { useLocale } from '@/lib/locale';

export function TopBar() {
  const { locale, setLocale, t } = useLocale();
  return (
    <header className="flex h-14 items-center gap-3 border-b border-cream-200 px-4 md:px-6 md:pr-gutter">
      <div className="relative flex-1 max-w-xl">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500">
          <Icon name="search" size={14} />
        </span>
        <input
          type="text"
          placeholder={t('search.placeholder')}
          aria-label={t('search.label')}
          disabled
          className="w-full rounded-lg border border-cream-200 bg-cream-50 pl-9 pr-12 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/15 disabled:cursor-not-allowed disabled:opacity-80"
        />
        <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-cream-300 bg-cream-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-ink-500">
          ⌘K
        </kbd>
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <div className="inline-flex rounded-full border border-cream-200 bg-cream-100 p-0.5 text-xs">
          <button type="button" onClick={() => setLocale('zh')} aria-pressed={locale === 'zh'} className={`h-7 rounded-full px-2.5 ${locale === 'zh' ? 'bg-cream-300 font-medium text-ink-900' : 'text-ink-500 hover:text-ink-700'}`}>中</button>
          <button type="button" onClick={() => setLocale('en')} aria-pressed={locale === 'en'} className={`h-7 rounded-full px-2.5 ${locale === 'en' ? 'bg-cream-300 font-medium text-ink-900' : 'text-ink-500 hover:text-ink-700'}`}>EN</button>
          <button type="button" onClick={() => setLocale('ja')} aria-pressed={locale === 'ja'} className={`h-7 rounded-full px-2.5 ${locale === 'ja' ? 'bg-cream-300 font-medium text-ink-900' : 'text-ink-500 hover:text-ink-700'}`}>日</button>
        </div>
        <Link
          to="/settings"
          aria-label="Settings"
          className="rounded-lg p-2 text-ink-700 hover:bg-cream-100"
        >
          <Icon name="settings" size={18} />
        </Link>
      </div>
    </header>
  );
}
