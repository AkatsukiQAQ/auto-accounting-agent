import { Link } from 'react-router-dom';
import { Icon } from '@/components/ui/Icon';

export function TopBar() {
  return (
    <header className="flex h-14 items-center gap-4 border-b border-cream-200 px-4 md:px-6">
      <div className="relative flex-1 max-w-xl">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500">
          <Icon name="search" size={14} />
        </span>
        <input
          type="text"
          placeholder="Search records, categories…"
          aria-label="Search (coming in a later phase)"
          disabled
          className="w-full rounded-lg border border-cream-200 bg-cream-50 pl-9 pr-12 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/15 disabled:cursor-not-allowed disabled:opacity-80"
        />
        <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-cream-300 bg-cream-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-ink-500">
          ⌘K
        </kbd>
      </div>
      <Link
        to="/settings"
        aria-label="Settings"
        className="rounded-lg p-2 text-ink-700 hover:bg-cream-100"
      >
        <Icon name="settings" size={18} />
      </Link>
    </header>
  );
}
