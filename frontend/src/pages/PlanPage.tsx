import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Field, inputClass } from '@/components/ui/Field';
import { PaperCard } from '@/components/ui/PaperCard';
import { Spinner } from '@/components/ui/Spinner';
import { PeriodSelector } from '@/components/budget/PeriodSelector';
import { useBudgetPeriod, useBudgetPlans, useBudgetSummary, useBudgetWrite } from '@/hooks/useBudgets';
import { useCategories } from '@/hooks/useCategories';
import { useSettings } from '@/hooks/useSettings';
import { isSpendingCategory, parseMoney, periodBounds, shiftPeriod, type BudgetItem, type BudgetKind, type BudgetPlan } from '@/lib/budget';
import { fmtMoney } from '@/lib/formatters';

export function PlanPage() {
  const settings = useSettings();
  const currency = settings.data?.profile.defaultCurrency ?? 'JPY';
  const period = useBudgetPeriod(settings.data?.profile.timezone);
  const plans = useBudgetPlans(period.type, period.start, period.end, currency);
  const previous = periodBounds(period.type, shiftPeriod(period.type, period.start, -1));
  const previousPlans = useBudgetPlans(period.type, previous.start, previous.end, currency);
  const plan = plans.data?.[0];
  const summary = useBudgetSummary(plan?.id);
  const write = useBudgetWrite();
  const [error, setError] = useState('');
  async function create(clone = false) {
    setError('');
    try {
      await write.mutateAsync(clone ? { path: `/api/budget-plans/${previousPlans.data?.[0]?.id}/clone`, body: { startsOn: period.start } }
        : { path: '/api/budget-plans', body: { periodType: period.type, startsOn: period.start, currency } });
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not create plan.'); }
  }
  async function cloneNext() {
    setError('');
    const next = shiftPeriod(period.type, period.start, 1);
    try { await write.mutateAsync({ path: `/api/budget-plans/${plan?.id}/clone`, body: { startsOn: next } }); period.change(period.type, next); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not duplicate plan.'); }
  }
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="hand-body text-4xl">A plan with room to live.</h1>
      <p className="mt-2 text-sm text-ink-500">Allocate your {currency} spending. Keep a buffer if you like.</p></div>
      <Link className="text-sm underline" to={`/${period.search}`}>View dashboard →</Link></div>
    <PeriodSelector {...period} onChange={period.change} />
    {error && <Alert tone="error">{error}</Alert>}
    {(plans.isError || settings.isError) && <Alert tone="error">Could not load plan.</Alert>}
    {plans.isLoading && <Spinner />}
    {summary.isError && <Alert tone="error">Could not load budget totals.</Alert>}
    {!plans.isLoading && !plans.isError && !plan && <PaperCard><h2 className="mb-3 font-semibold">Start this {period.type}'s plan</h2>
      <div className="flex flex-wrap gap-2"><Button disabled={write.isPending} onClick={() => create()}>Create blank plan</Button>
        <Button variant="outline" disabled={write.isPending || !previousPlans.data?.length} onClick={() => create(true)}>Duplicate last {period.type}</Button></div>
      {previousPlans.isError && <p className="mt-2 text-sm text-neg-500">Could not load the previous plan.</p>}
      {!previousPlans.isLoading && !previousPlans.isError && !previousPlans.data?.length && <p className="mt-2 text-xs text-ink-500">No plan in the preceding period to duplicate.</p>}
    </PaperCard>}
    {plan && <>
      <PlanDetails key={plan.id} plan={plan} />
      {summary.data && <PaperCard><div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Total planned spending" value={summary.data.plannedSpendCents} currency={currency} />
        <Metric label="Unallocated / planned residual" value={summary.data.plannedResidualCents} currency={currency} />
        <Metric label="Savings target" value={summary.data.savingsTargetCents} currency={currency} />
      </div><p className="mt-3 text-xs text-ink-500">Planned income − planned spending = residual. Savings target is a goal, not another expense allocation.</p></PaperCard>}
      <Allocations key={plan.id} plan={plan} />
      <Button variant="outline" disabled={write.isPending} onClick={cloneNext}>Duplicate into next {period.type}</Button>
      <p className="text-xs text-ink-500">Copies allocations and targets only. Spending stays in the original period.</p>
    </>}
  </div>;
}

function Metric({ label, value, currency }: { label: string; value: number | null; currency: string }) {
  return <div><div className="text-xs text-ink-500">{label}</div><div className="num mt-1 text-2xl">{value === null ? '—' : fmtMoney(value, currency)}</div></div>;
}

function PlanDetails({ plan }: { plan: BudgetPlan }) {
  const [income, setIncome] = useState(plan.plannedIncomeCents === null ? '' : String(plan.plannedIncomeCents / 100));
  const [savings, setSavings] = useState(plan.savingsTargetCents === null ? '' : String(plan.savingsTargetCents / 100));
  const [status, setStatus] = useState(plan.status);
  const [note, setNote] = useState(plan.note ?? '');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const write = useBudgetWrite();
  async function submit(e: FormEvent) {
    e.preventDefault(); setError(''); setSaved(false);
    try { await write.mutateAsync({ path: `/api/budget-plans/${plan.id}`, method: 'PATCH', body: {
      plannedIncomeCents: income.trim() ? parseMoney(income) : null, savingsTargetCents: savings.trim() ? parseMoney(savings) : null,
      status, note: note || null,
    } }); setSaved(true); } catch (e) { setError(e instanceof Error ? e.message : 'Could not save plan.'); }
  }
  return <PaperCard><form onSubmit={submit} className="space-y-3">
    {error && <Alert tone="error">{error}</Alert>}
    <div className="grid gap-3 sm:grid-cols-3">
      <Field label={`Planned income (${plan.currency})`} hint="Optional"><input className={inputClass} inputMode="decimal" value={income} onChange={e => { setIncome(e.target.value); setSaved(false); }} /></Field>
      <Field label={`Savings target (${plan.currency})`} hint="Optional"><input className={inputClass} inputMode="decimal" value={savings} onChange={e => { setSavings(e.target.value); setSaved(false); }} /></Field>
      <Field label="Status"><select className={inputClass} value={status} onChange={e => { setStatus(e.target.value as BudgetPlan['status']); setSaved(false); }}><option>draft</option><option>active</option><option>closed</option></select></Field>
    </div>
    <Field label="Note (optional)"><input className={inputClass} value={note} onChange={e => { setNote(e.target.value); setSaved(false); }} /></Field>
    <Button type="submit" disabled={write.isPending}>{write.isPending ? 'Saving…' : 'Save targets'}</Button>
    {saved && <span role="status" className="ml-3 text-sm text-pos-500">Saved</span>}
  </form></PaperCard>;
}

function Allocations({ plan }: { plan: BudgetPlan }) {
  const cats = useCategories();
  const [category, setCategory] = useState('');
  const [error, setError] = useState('');
  const write = useBudgetWrite();
  const available = (cats.data ?? []).filter(c => isSpendingCategory(c) && !plan.items.some(i => i.categoryId === c.id));
  async function add(e: FormEvent) {
    e.preventDefault(); setError('');
    try { await write.mutateAsync({ path: `/api/budget-plans/${plan.id}/items`, body: { categoryId: category, limitCents: 0 } }); setCategory(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not add category.'); }
  }
  return <section className="space-y-3"><h2 className="text-lg font-semibold">Category allocations</h2>
    {error && <Alert tone="error">{error}</Alert>}
    {cats.isError && <Alert tone="error">Could not load categories.</Alert>}
    {plan.items.map(item => <ItemEditor key={item.id} item={item} label={cats.data?.find(c => c.id === item.categoryId)?.label ?? item.categoryId} currency={plan.currency} />)}
    <form onSubmit={add} className="flex items-end gap-2"><Field label="Add category"><select required className={inputClass} value={category} onChange={e => setCategory(e.target.value)}><option value="">Choose category</option>{available.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></Field>
      <Button type="submit" disabled={write.isPending || !category}>Add</Button></form>
  </section>;
}

function ItemEditor({ item, label, currency }: { item: BudgetItem; label: string; currency: string }) {
  const [limit, setLimit] = useState(String(item.limitCents / 100));
  const [kind, setKind] = useState(item.kind);
  const [warning, setWarning] = useState(String(item.warningRatio * 100));
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const write = useBudgetWrite();
  async function submit(e: FormEvent) {
    e.preventDefault(); setError(''); setSaved(false);
    try { await write.mutateAsync({ path: `/api/budget-items/${item.id}`, method: 'PATCH', body: { limitCents: parseMoney(limit), kind, warningRatio: Number(warning) / 100 } }); setSaved(true); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save allocation.'); }
  }
  async function remove() {
    try { await write.mutateAsync({ path: `/api/budget-items/${item.id}`, method: 'DELETE' }); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not remove allocation.'); }
  }
  return <PaperCard><form onSubmit={submit} className="space-y-2"><h3 className="font-semibold">{label}</h3>
    {error && <Alert tone="error">{error}</Alert>}
    <div className="grid items-end gap-3 sm:grid-cols-3 lg:grid-cols-[1fr_1fr_1fr_auto]">
      <Field label={`Limit (${currency})`}><input required inputMode="decimal" className={inputClass} value={limit} onChange={e => { setLimit(e.target.value); setSaved(false); }} /></Field>
      <Field label="Kind"><select className={inputClass} value={kind} onChange={e => { setKind(e.target.value as BudgetKind); setSaved(false); }}><option value="fixed">Fixed</option><option value="flexible">Flexible</option><option value="discretionary">Discretionary</option></select></Field>
      <Field label="Warning threshold (%)"><input type="number" min="1" max="100" step="1" required className={inputClass} value={warning} onChange={e => { setWarning(e.target.value); setSaved(false); }} /></Field>
      <div className="flex gap-2"><Button type="submit" disabled={write.isPending}>Save</Button><Button type="button" variant="ghost" disabled={write.isPending} onClick={remove}>Remove</Button></div>
    </div>{saved && <p role="status" className="text-xs text-pos-500">Saved</p>}
  </form></PaperCard>;
}
