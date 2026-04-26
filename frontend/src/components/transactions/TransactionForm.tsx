import { useState, type FormEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Field, inputClass } from '@/components/ui/Field';
import { useCategories } from '@/hooks/useCategories';
import { ApiError } from '@/lib/api';
import type {
  Transaction,
  TransactionCreate,
  TransactionUpdate,
} from '@/lib/types';

interface Props {
  initial?: Partial<Transaction>;
  defaultCurrency?: string;
  submitLabel?: string;
  onSubmit: (input: TransactionCreate | TransactionUpdate) => Promise<unknown>;
  onCancel?: () => void;
  /** When set, the inner <form> gets this id so external buttons can do
   *  `<button type="submit" form={formId}>` to trigger submission. */
  formId?: string;
  /** When true, the form's own Save button is hidden (caller renders its own). */
  hideSubmitButton?: boolean;
}

const CURRENCIES = ['USD', 'JPY', 'CNY', 'HKD', 'EUR', 'GBP', 'KRW'];

function toLocalDatetime(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  // datetime-local needs YYYY-MM-DDTHH:MM (local time)
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalDatetime(local: string): string {
  // Treat input as local time, return ISO with timezone offset.
  return new Date(local).toISOString();
}

export function TransactionForm({
  initial,
  defaultCurrency = 'JPY',
  submitLabel,
  onSubmit,
  onCancel,
  formId,
  hideSubmitButton,
}: Props) {
  const cats = useCategories();

  const initialAmount = initial?.amountCents ?? 0;
  const [type, setType] = useState<'expense' | 'income'>(initialAmount > 0 ? 'income' : 'expense');
  const [amountStr, setAmountStr] = useState(
    initialAmount === 0 ? '' : (Math.abs(initialAmount) / 100).toString(),
  );
  const [merchant, setMerchant] = useState(initial?.merchant ?? '');
  const [currency, setCurrency] = useState(initial?.currency ?? defaultCurrency);
  const [categoryId, setCategoryId] = useState(initial?.categoryId ?? 'other');
  const [occurredAt, setOccurredAt] = useState(
    toLocalDatetime(initial?.occurredAt) || toLocalDatetime(new Date().toISOString()),
  );
  const [note, setNote] = useState(initial?.note ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildAmountCents(): number | null {
    const parsed = Number.parseFloat(amountStr);
    if (!Number.isFinite(parsed) || parsed <= 0) return null;
    const isJpyLike = currency === 'JPY' || currency === 'KRW';
    const cents = isJpyLike ? Math.round(parsed * 100) : Math.round(parsed * 100);
    return type === 'expense' ? -cents : cents;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!merchant.trim()) return setError('Merchant is required.');
    const amountCents = buildAmountCents();
    if (amountCents === null) return setError('Amount must be a positive number.');
    if (!occurredAt) return setError('Date/time is required.');

    setSubmitting(true);
    try {
      const payload: TransactionCreate = {
        occurredAt: fromLocalDatetime(occurredAt),
        merchant: merchant.trim(),
        amountCents,
        currency,
        categoryId,
        source: (initial?.source as 'photo' | 'manual') ?? 'manual',
        confidence: initial?.confidence ?? null,
        note: note.trim() || null,
        raw: initial?.raw ?? null,
      };
      await onSubmit(payload);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else if (err instanceof Error) setError(err.message);
      else setError('Save failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form id={formId} onSubmit={handleSubmit} className="space-y-3">
      {error ? <Alert tone="error">{error}</Alert> : null}

      <Field label="Merchant">
        <input
          type="text"
          value={merchant}
          onChange={(e) => setMerchant(e.target.value)}
          className={inputClass}
          placeholder="Starbucks Shibuya"
          required
        />
      </Field>

      <div className="grid grid-cols-[auto_1fr_auto] items-end gap-2">
        <Field label="Type">
          <select
            value={type}
            onChange={(e) => setType(e.target.value as 'expense' | 'income')}
            className={inputClass}
          >
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </select>
        </Field>
        <Field label="Amount">
          <input
            type="number"
            step="0.01"
            min="0"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            className={inputClass}
            placeholder="0.00"
            required
          />
        </Field>
        <Field label="Currency">
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className={inputClass}
          >
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Category">
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className={inputClass}
          disabled={cats.isLoading}
        >
          {(cats.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </Field>

      <Field label="When">
        <input
          type="datetime-local"
          value={occurredAt}
          onChange={(e) => setOccurredAt(e.target.value)}
          className={inputClass}
          required
        />
      </Field>

      <Field label="Note (optional)">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          className={inputClass + ' resize-y'}
        />
      </Field>

      {hideSubmitButton ? null : (
        <div className="flex items-center justify-end gap-2 pt-1">
          {onCancel ? (
            <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
              Cancel
            </Button>
          ) : null}
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : (submitLabel ?? 'Save')}
          </Button>
        </div>
      )}
    </form>
  );
}
