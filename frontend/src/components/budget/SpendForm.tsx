import { useState, type FormEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Field, inputClass } from '@/components/ui/Field';
import { useCategories } from '@/hooks/useCategories';
import { useBudgetWrite } from '@/hooks/useBudgets';
import { isSpendingCategory, parseMoney, todayInZone } from '@/lib/budget';

export function SpendForm({ currency, timezone, planId, categoryId: initialCategory, onDone }: {
  currency: string; timezone?: string; planId?: string; categoryId?: string; onDone: () => void;
}) {
  const cats = useCategories();
  const write = useBudgetWrite();
  const [amount, setAmount] = useState('');
  const [categoryId, setCategory] = useState(initialCategory ?? 'other');
  const [date, setDate] = useState(todayInZone(timezone));
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault(); setError('');
    try {
      const cents = parseMoney(amount);
      if (cents <= 0) throw new Error('Enter an amount greater than zero.');
      await write.mutateAsync({ path: planId ? '/api/budget-spend/set-total' : '/api/transactions/quick',
        body: planId ? { planId, categoryId, totalCents: cents, note: note || null }
          : { amountCents: cents, categoryId, occurredOn: date, currency, note: note || null } });
      onDone();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save expense.'); }
  }
  return <form onSubmit={submit} className="space-y-3">
    {error && <Alert tone="error">{error}</Alert>}
    {planId && <p className="text-sm text-ink-500">Set the category total for this period. A difference adjustment will be added; existing records stay intact. Later imports add to this total.</p>}
    <Field label={`${planId ? 'Category total' : 'Amount'} (${currency})`}><input autoFocus required className={inputClass}
      inputMode="decimal" value={amount} onChange={e => setAmount(e.target.value)} /></Field>
    <Field label="Category"><select className={inputClass} value={categoryId} onChange={e => setCategory(e.target.value)}>
      {(cats.data ?? []).filter(isSpendingCategory).map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
    </select></Field>
    {!planId && <Field label="Date"><input type="date" required max={todayInZone(timezone)} className={inputClass} value={date} onChange={e => setDate(e.target.value)} /></Field>}
    <Field label="Note (optional)"><input className={inputClass} value={note} onChange={e => setNote(e.target.value)} /></Field>
    {cats.isError && <Alert tone="error">Could not load categories.</Alert>}
    <Button type="submit" disabled={write.isPending || cats.isLoading || cats.isError}>{write.isPending ? 'Saving…' : planId ? 'Set total' : 'Add expense'}</Button>
  </form>;
}
