import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CatPill } from '@/components/ui/CatPill';
import { PaperCard } from '@/components/ui/PaperCard';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { PeriodSelector } from '@/components/budget/PeriodSelector';
import { SpendForm } from '@/components/budget/SpendForm';
import { RecentList } from '@/components/budget/DashboardParts';
import { useBudgetPeriod, useBudgetPlans, useBudgetSummary } from '@/hooks/useBudgets';
import { useTransactions } from '@/hooks/useTransactions';
import { useCategories } from '@/hooks/useCategories';
import { useSettings } from '@/hooks/useSettings';
import { fmtMoney } from '@/lib/formatters';
import type { BudgetSummary } from '@/lib/budget';
import { useLocale } from '@/lib/locale';

export function DashboardPage() {
  const settings = useSettings();
  const cats = useCategories();
  const timezone = settings.data?.profile.timezone;
  const currency = settings.data?.profile.defaultCurrency ?? 'JPY';
  const period = useBudgetPeriod(timezone);
  const plans = useBudgetPlans(period.type, period.start, period.end, currency);
  const plan = plans.data?.[0];
  const summary = useBudgetSummary(plan?.id);
  const recent = useTransactions({ limit: 5 });
  const [modal, setModal] = useState<'quick' | 'total' | null>(null);
  const { locale, t } = useLocale();
  const s = summary.data;
  const name = settings.data?.profile.preferredName || settings.data?.profile.fullName?.split(' ')[0] || 'there';
  const hour = new Date().getHours();
  const greeting = locale === 'zh' ? (hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好')
    : locale === 'ja' ? (hour < 12 ? 'おはようございます' : hour < 18 ? 'こんにちは' : 'こんばんは')
      : (hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening');
  const periodName = t(`period.${period.type}`);
  const category = (id: string) => cats.data?.find(c => c.id === id);
  const label = (id: string) => category(id)?.label ?? id;
  const categoryPill = (id: string) => ({ slug: id, label: label(id), icon: category(id)?.icon, imageUrl: category(id)?.iconImageUrl });
  const spendingBreakdown = s ? [...s.items, ...s.unbudgeted]
    .filter(item => item.spentCents > 0)
    .map(item => ({ slug: item.categoryId, label: label(item.categoryId), value: item.spentCents,
      color: cats.data?.find(category => category.id === item.categoryId)?.colorDot }))
    .sort((a, b) => b.value - a.value) : [];
  const atRisk = s?.items.filter(item => item.status !== 'safe').slice(0, 3) ?? [];
  const unallocatedSpend = s?.unbudgeted.reduce((total, item) => total + item.spentCents, 0) ?? 0;
  const budgetProgress = s?.plannedSpendCents ? Math.max(0, Math.min(100, s.actualSpendCents / s.plannedSpendCents * 100)) : 0;
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">{t('dashboard.eyebrow')}</div>
        <h1 className="hand-body mt-1 text-[40px] leading-tight text-ink-900">{greeting}, {name}<span className="ml-1 align-[0.6em] text-[0.5em] text-warn-500">✦</span></h1>
        <p className="mt-2 text-sm text-ink-500">{t('dashboard.subtitle')}</p></div>
      <Button onClick={() => setModal('quick')}>{t('dashboard.quickExpense')}</Button>
    </div>
    <PeriodSelector {...period} onChange={period.change} />
    {(plans.isLoading || summary.isLoading) && <Spinner />}
    {(plans.isError || summary.isError || settings.isError) && <Alert tone="error">{t('dashboard.loadingBudget')}</Alert>}
    {!plans.isLoading && !plans.isError && !plan && <PaperCard><h2 className="text-xl font-semibold">{t('dashboard.createTitle')}</h2>
      <p className="my-3 text-sm text-ink-500">{t('dashboard.createHint', { period: periodName, currency })}</p>
      <Link to={`/plan${period.search}`}><Button>{t('dashboard.createPlan')}</Button></Link></PaperCard>}
    {s && <div className="grid gap-4 lg:grid-cols-3">
      <PaperCard className="p-6 lg:col-span-2"><div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_15rem] md:items-end"><div>
        <div className="flex items-center justify-between gap-3"><p className="text-xs font-semibold uppercase tracking-widest text-ink-500">{t('dashboard.available', { period: periodName })}</p><Link to={`/plan${period.search}`} className="text-xs underline">{t('dashboard.adjustPlan')}</Link></div>
        <p className={`num mt-2 text-4xl md:text-5xl ${s.remainingBudgetCents < 0 ? 'text-neg-500' : 'text-ink-900'}`}>{fmtMoney(s.remainingBudgetCents, currency)}</p>
        <p className="mt-2 text-sm text-ink-500">{t('dashboard.spentOf', { spent: fmtMoney(s.actualSpendCents, currency), planned: fmtMoney(s.plannedSpendCents, currency), days: s.period.daysRemaining })}</p>
        <progress aria-label="Total budget used" max={100} value={budgetProgress} className="budget-progress mt-4 h-2 w-full" />
      </div><div className="border-t border-cream-200 pt-5 md:border-l md:border-t-0 md:pl-6 md:pt-0"><p className="text-xs font-semibold uppercase tracking-widest text-ink-500">{t('dashboard.safe')}</p>
        <p className="num mt-2 text-3xl">{fmtMoney(s.safeDailySpendCents, currency)} <span className="text-sm text-ink-500">{t('dashboard.perDay')}</span></p>
        <p className="mt-2 text-xs text-ink-500">{t('dashboard.safeHint')}</p></div></div></PaperCard>
      <PaperCard><h2 className="font-semibold">{t('dashboard.attention')}</h2>
        {atRisk.length === 0 && unallocatedSpend === 0 ? <p className="mt-3 text-sm text-ink-500">{t('dashboard.onTrack')}</p> : <div className="mt-3 divide-y divide-cream-200">{atRisk.map(item => <div key={item.categoryId} className="flex items-center justify-between gap-3 py-3"><CatPill {...categoryPill(item.categoryId)} size="sm" /><div className="text-right text-sm"><span className={item.status === 'over' ? 'text-neg-500' : 'text-warn-500'}>{item.status === 'over' ? t('dashboard.over') : t('dashboard.ahead')}</span><p className="text-xs text-ink-500">{t('dashboard.left', { amount: fmtMoney(item.remainingCents, currency) })}</p></div></div>)}
          {unallocatedSpend > 0 && <div className="flex items-center justify-between gap-3 py-3"><span className="text-sm font-medium text-warn-500">{t('dashboard.notAllocated')}</span><div className="text-right text-sm"><span>{fmtMoney(unallocatedSpend, currency)}</span><p className="text-xs text-ink-500">{t('dashboard.addPlan')}</p></div></div>}</div>}</PaperCard>
      <PaperCard><h2 className="font-semibold">{t('dashboard.mix')}</h2><p className="mt-1 text-xs text-ink-500">{t('dashboard.mixHint')}</p>
          {spendingBreakdown.length === 0 ? <p className="mt-4 text-sm text-ink-500">{t('dashboard.noSpend')}</p> : <><div className="mt-4 flex h-3 overflow-hidden rounded-full bg-cream-200">{spendingBreakdown.map(item => <span key={item.slug} title={`${item.label}: ${fmtMoney(item.value, currency)}`} style={{ width: `${item.value / s.actualSpendCents * 100}%`, backgroundColor: item.color }} />)}</div><div className="mt-4 space-y-2">{spendingBreakdown.slice(0, 3).map(item => <div key={item.slug} className="flex items-center justify-between gap-3 text-sm"><CatPill {...categoryPill(item.slug)} size="sm" /><span className="shrink-0">{fmtMoney(item.value, currency)} <span className="text-xs text-ink-500">{Math.round(item.value / s.actualSpendCents * 100)}%</span></span></div>)}</div></>}</PaperCard>
      <section className="lg:col-span-2 lg:max-w-3xl"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-lg font-semibold">{t('dashboard.budgets')}</h2><p className="text-sm text-ink-500">{t('dashboard.budgetHint')}</p></div><Button variant="outline" size="sm" disabled={s.period.daysElapsed === 0} onClick={() => setModal('total')}>{t('dashboard.setTotal')}</Button></div>
        {s.items.length === 0 ? <PaperCard><p>{t('dashboard.noAllocated')} <Link className="underline" to={`/plan${period.search}`}>{t('dashboard.addCategories')}</Link>.</p></PaperCard> : <PaperCard className="grid overflow-hidden p-0 sm:grid-cols-2">{s.items.map(item => <div key={item.categoryId} className="flex items-center gap-2 border-b border-cream-200 p-3 sm:odd:border-r"><BudgetGauge item={item} label={label(item.categoryId)} /><div className="min-w-0"><CatPill {...categoryPill(item.categoryId)} size="sm" /><p className="mt-1 truncate text-sm">{fmtMoney(item.spentCents, currency)} <span className="text-ink-500">/ {fmtMoney(item.limitCents, currency)}</span></p><p className="text-xs text-ink-500">{t('dashboard.left', { amount: fmtMoney(item.remainingCents, currency) })} · {t(`status.${item.status}`)}</p></div></div>)}</PaperCard>}</section>
    </div>}
    <PaperCard><div className="mb-3 flex justify-between"><h3 className="text-sm font-semibold">{t('dashboard.recent')}</h3><Link className="text-xs underline" to="/records">{t('dashboard.viewAll')}</Link></div>
      {recent.isLoading ? <Spinner /> : recent.isError ? <Alert tone="error">Could not load records.</Alert> : <RecentList rows={recent.data?.pages.flatMap(p => p.data) ?? []} categories={cats.data ?? []} />}
    </PaperCard>
    <Modal open={modal !== null} onClose={() => setModal(null)} title={modal === 'total' ? t('dashboard.totalTitle') : t('dashboard.quickTitle')}>
      <SpendForm key={modal} currency={currency} timezone={timezone} planId={modal === 'total' ? plan?.id : undefined} onDone={() => setModal(null)} />
    </Modal>
  </div>;
}

function BudgetGauge({ item, label }: { item: BudgetSummary['items'][number]; label: string }) {
  const percent = Math.max(0, Math.min(100, Math.round((item.usedRatio ?? 0) * 100)));
  const color = item.status === 'safe' ? 'var(--color-pos-500)'
    : item.status === 'watch' ? 'var(--color-warn-500)' : 'var(--color-neg-500)';
  return <div role="img" aria-label={`${label}: ${percent}% of budget used`} className="grid size-12 shrink-0 place-items-center rounded-full"
    style={{ background: `conic-gradient(${color} ${percent}%, var(--color-cream-200) 0)` }}>
    <span className="grid size-9 place-items-center rounded-full bg-cream-50 text-[10px] font-semibold text-ink-700">{percent}%</span>
  </div>;
}
