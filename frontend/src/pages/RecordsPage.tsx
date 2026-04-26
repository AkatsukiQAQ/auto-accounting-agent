import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CatPill } from '@/components/ui/CatPill';
import { Icon } from '@/components/ui/Icon';
import { Modal } from '@/components/ui/Modal';
import { PaperCard } from '@/components/ui/PaperCard';
import { Spinner } from '@/components/ui/Spinner';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { TransactionForm } from '@/components/transactions/TransactionForm';
import { useCategories } from '@/hooks/useCategories';
import {
  useDeleteTransaction,
  useTransactions,
  useUpdateTransaction,
} from '@/hooks/useTransactions';
import { fmtMoney } from '@/lib/formatters';
import type { Transaction } from '@/lib/types';

type ModalState =
  | { kind: 'closed' }
  | { kind: 'edit'; txn: Transaction }
  | { kind: 'delete'; txn: Transaction };

function isoOrUndef(v: string): string | undefined {
  if (!v) return undefined;
  // Treat naked YYYY-MM-DD as start of day local; convert to ISO.
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

export function RecordsPage() {
  const cats = useCategories();
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [search, setSearch] = useState('');
  const [pickedCats, setPickedCats] = useState<string[]>([]);

  const filters = useMemo(
    () => ({
      from: isoOrUndef(from),
      to: isoOrUndef(to),
      q: search.trim() || undefined,
      category: pickedCats.length ? pickedCats : undefined,
      limit: 50,
    }),
    [from, to, search, pickedCats],
  );

  const list = useTransactions(filters);
  const updateM = useUpdateTransaction();
  const deleteM = useDeleteTransaction();

  const [modal, setModal] = useState<ModalState>({ kind: 'closed' });
  const close = () => setModal({ kind: 'closed' });

  const allRows = list.data?.pages.flatMap((p) => p.data) ?? [];
  const isEmpty = !list.isLoading && allRows.length === 0;

  function toggleCat(id: string) {
    setPickedCats((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Records" title="Your transactions" />

      <PaperCard>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Search">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Merchant…"
              className={inputClass}
            />
          </Field>
          <Field label="From">
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="To">
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className={inputClass}
            />
          </Field>
        </div>
        <div className="mt-3">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-ink-500">
            Categories
          </span>
          <div className="flex flex-wrap gap-1.5">
            {(cats.data ?? []).map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => toggleCat(c.id)}
                className={[
                  'rounded-full border px-2.5 py-1 text-xs',
                  pickedCats.includes(c.id)
                    ? 'border-ink-900 bg-ink-900 text-cream-50'
                    : 'border-ink-200 text-ink-700 hover:bg-cream-100',
                ].join(' ')}
              >
                {c.label}
              </button>
            ))}
            {pickedCats.length > 0 && (
              <button
                type="button"
                onClick={() => setPickedCats([])}
                className="rounded-full px-2.5 py-1 text-xs text-ink-500 hover:bg-cream-100"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </PaperCard>

      {list.isLoading && (
        <div className="flex items-center gap-2 text-sm text-ink-500">
          <Spinner size={16} /> Loading…
        </div>
      )}
      {list.isError && <Alert tone="error">Failed to load transactions.</Alert>}

      {isEmpty && (
        <PaperCard>
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <Icon name="list" size={28} className="text-ink-500" />
            <p className="text-sm text-ink-500">No transactions match these filters.</p>
            <Link to="/import">
              <Button>Import a receipt</Button>
            </Link>
          </div>
        </PaperCard>
      )}

      {allRows.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-cream-200 bg-cream-100">
          <table className="w-full text-sm">
            <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-2 font-semibold">Date</th>
                <th className="px-4 py-2 font-semibold">Merchant</th>
                <th className="px-4 py-2 font-semibold">Category</th>
                <th className="px-4 py-2 font-semibold text-right">Amount</th>
                <th className="px-4 py-2 font-semibold">Source</th>
                <th className="px-4 py-2 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cream-200">
              {allRows.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-3 text-ink-700">
                    {new Date(t.occurredAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-ink-900">
                    {t.merchant}
                    {t.note ? (
                      <div className="text-xs text-ink-500" title={t.note}>
                        {t.note.length > 60 ? t.note.slice(0, 60) + '…' : t.note}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <CatPill slug={t.categoryId} label={catLabel(cats.data, t.categoryId)} />
                  </td>
                  <td
                    className={[
                      'px-4 py-3 text-right font-mono text-sm',
                      t.amountCents >= 0 ? 'text-pos-500' : 'text-ink-900',
                    ].join(' ')}
                  >
                    {fmtMoney(t.amountCents, t.currency)}
                  </td>
                  <td className="px-4 py-3 text-ink-500">
                    <span title={t.source} aria-label={t.source}>
                      <Icon name={t.source === 'photo' ? 'image' : 'edit'} size={14} />
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        leadingIcon={<Icon name="edit" size={14} />}
                        onClick={() => setModal({ kind: 'edit', txn: t })}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        leadingIcon={<Icon name="trash" size={14} />}
                        onClick={() => setModal({ kind: 'delete', txn: t })}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {list.hasNextPage && (
            <div className="flex justify-center border-t border-cream-200 p-3">
              <Button
                variant="outline"
                onClick={() => list.fetchNextPage()}
                disabled={list.isFetchingNextPage}
              >
                {list.isFetchingNextPage ? 'Loading…' : 'Load more'}
              </Button>
            </div>
          )}
        </div>
      )}

      <Modal
        open={modal.kind === 'edit'}
        onClose={close}
        title="Edit Transaction"
        size="lg"
      >
        {modal.kind === 'edit' && (
          <TransactionForm
            initial={modal.txn}
            onSubmit={async (input) => {
              await updateM.mutateAsync({ id: modal.txn.id, patch: input });
              close();
            }}
            onCancel={close}
          />
        )}
      </Modal>

      <Modal
        open={modal.kind === 'delete'}
        onClose={close}
        title="Delete transaction?"
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={close} disabled={deleteM.isPending}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                if (modal.kind !== 'delete') return;
                await deleteM.mutateAsync(modal.txn.id);
                close();
              }}
              disabled={deleteM.isPending}
            >
              {deleteM.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </>
        }
      >
        {modal.kind === 'delete' && (
          <p className="text-sm text-ink-700">
            Delete <span className="font-semibold">{modal.txn.merchant}</span> for{' '}
            <span className="font-mono">{fmtMoney(modal.txn.amountCents, modal.txn.currency)}</span>?
          </p>
        )}
      </Modal>
    </div>
  );
}

function catLabel(cats: { id: string; label: string }[] | undefined, id: string): string {
  if (!cats) return id;
  return cats.find((c) => c.id === id)?.label ?? id;
}
