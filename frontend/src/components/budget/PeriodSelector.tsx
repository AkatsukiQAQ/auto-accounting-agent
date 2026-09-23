import { Button } from '@/components/ui/Button';
import { shiftPeriod, type PeriodType } from '@/lib/budget';

export function PeriodSelector({ type, start, end, switchOn, onChange }: {
  type: PeriodType; start: string; end: string; switchOn: string; onChange: (type: PeriodType, date: string) => void;
}) {
  return <div className="flex flex-wrap items-center gap-2">
    <div className="flex gap-1 rounded-lg bg-cream-200 p-1" aria-label="Budget period">
      {(['week', 'month'] as const).map(p => <Button key={p} size="sm" variant={type === p ? 'primary' : 'ghost'}
        aria-pressed={type === p} onClick={() => onChange(p, switchOn)}>{p === 'week' ? 'Week' : 'Month'}</Button>)}
    </div>
    <Button variant="ghost" aria-label="Previous period" onClick={() => onChange(type, shiftPeriod(type, start, -1))}>←</Button>
    <span className="text-sm text-ink-700">{start} – {end}</span>
    <Button variant="ghost" aria-label="Next period" onClick={() => onChange(type, shiftPeriod(type, start, 1))}>→</Button>
  </div>;
}
