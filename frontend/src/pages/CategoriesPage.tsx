import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { CatPill } from '@/components/ui/CatPill';
import { Icon } from '@/components/ui/Icon';
import { Modal } from '@/components/ui/Modal';
import { Alert } from '@/components/ui/Alert';
import { Spinner } from '@/components/ui/Spinner';
import { PageHeader } from '@/components/layout/PageHeader';
import { CategoryForm } from '@/components/categories/CategoryForm';
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from '@/hooks/useCategories';
import { ApiError } from '@/lib/api';
import type { Category } from '@/lib/types';

type ModalState =
  | { kind: 'closed' }
  | { kind: 'create' }
  | { kind: 'edit'; cat: Category }
  | { kind: 'delete'; cat: Category };

export function CategoriesPage() {
  const list = useCategories();
  const createM = useCreateCategory();
  const updateM = useUpdateCategory();
  const deleteM = useDeleteCategory();

  const [modal, setModal] = useState<ModalState>({ kind: 'closed' });
  const [deleteError, setDeleteError] = useState<{
    message: string;
    code: string;
    meta: Record<string, unknown>;
  } | null>(null);

  function close() {
    setModal({ kind: 'closed' });
    setDeleteError(null);
  }

  async function handleDelete(cat: Category) {
    setDeleteError(null);
    try {
      await deleteM.mutateAsync(cat.id);
      close();
    } catch (err) {
      if (err instanceof ApiError) {
        setDeleteError({ message: err.message, code: err.code, meta: err.meta });
      } else {
        setDeleteError({
          message: err instanceof Error ? err.message : 'Failed to delete.',
          code: 'unknown',
          meta: {},
        });
      }
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Categories"
        title="Manage tags"
        actions={
          <Button leadingIcon={<Icon name="plus" size={14} />} onClick={() => setModal({ kind: 'create' })}>
            New Category
          </Button>
        }
      />

      {list.isLoading && (
        <div className="flex items-center gap-2 text-sm text-ink-500">
          <Spinner size={16} /> Loading…
        </div>
      )}

      {list.isError && <Alert tone="error">Failed to load categories.</Alert>}

      {list.data && list.data.length === 0 && (
        <Alert tone="info">No categories yet. Create one to start tagging transactions.</Alert>
      )}

      {list.data && list.data.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-cream-200 bg-cream-100">
          <table className="w-full text-sm">
            <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-2 font-semibold">Category</th>
                <th className="px-4 py-2 font-semibold">Slug</th>
                <th className="px-4 py-2 font-semibold">Keywords</th>
                <th className="px-4 py-2 font-semibold">Sort</th>
                <th className="px-4 py-2 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cream-200">
              {list.data.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-3">
                    <CatPill slug={c.id} label={c.label} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-500">{c.id}</td>
                  <td className="px-4 py-3 text-ink-700">
                    {c.keywords.length === 0 ? (
                      <span className="text-ink-500">—</span>
                    ) : (
                      <span title={c.keywords.join(', ')}>
                        {c.keywords.length} keyword{c.keywords.length === 1 ? '' : 's'}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-500">{c.sortOrder}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        leadingIcon={<Icon name="edit" size={14} />}
                        onClick={() => setModal({ kind: 'edit', cat: c })}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        leadingIcon={<Icon name="trash" size={14} />}
                        onClick={() => setModal({ kind: 'delete', cat: c })}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={modal.kind === 'create'}
        onClose={close}
        title="New Category"
      >
        {modal.kind === 'create' && (
          <CategoryForm
            onSubmit={async (input) => {
              await createM.mutateAsync(input as Parameters<typeof createM.mutateAsync>[0]);
              close();
            }}
            onCancel={close}
          />
        )}
      </Modal>

      <Modal
        open={modal.kind === 'edit'}
        onClose={close}
        title="Edit Category"
      >
        {modal.kind === 'edit' && (
          <CategoryForm
            initial={modal.cat}
            onSubmit={async (input) => {
              await updateM.mutateAsync({
                id: modal.cat.id,
                patch: input as Parameters<typeof updateM.mutateAsync>[0]['patch'],
              });
              close();
            }}
            onCancel={close}
          />
        )}
      </Modal>

      <Modal
        open={modal.kind === 'delete'}
        onClose={close}
        title="Delete category?"
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={close} disabled={deleteM.isPending}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => modal.kind === 'delete' && handleDelete(modal.cat)}
              disabled={deleteM.isPending}
            >
              {deleteM.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </>
        }
      >
        {modal.kind === 'delete' && (
          <div className="space-y-3 text-sm text-ink-700">
            <p>
              Delete <span className="font-semibold">{modal.cat.label}</span>?
              This can't be undone.
            </p>
            {deleteError && (
              <Alert tone="error">
                {deleteError.code === 'category_in_use' ? (
                  <>
                    {String((deleteError.meta as { transactionCount?: number }).transactionCount ?? 0)}{' '}
                    transaction(s) still use this category. Reassign them to{' '}
                    <span className="font-semibold">Other</span> first.
                  </>
                ) : deleteError.code === 'cannot_delete_system_category' ? (
                  "This is a system category and can't be deleted."
                ) : (
                  deleteError.message
                )}
              </Alert>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
