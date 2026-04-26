import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { fetchJson, qs } from '@/lib/api';
import type {
  Transaction,
  TransactionCreate,
  TransactionListResponse,
  TransactionUpdate,
} from '@/lib/types';

export interface TransactionFilters {
  /** ISO datetime — maps to query `from`. */
  from?: string;
  /** ISO datetime — maps to query `to`. */
  to?: string;
  /** Category slugs. Sent as comma-separated `category=`. */
  category?: string[];
  /** Merchant search substring. */
  q?: string;
  limit?: number;
}

const LIST_KEY = ['transactions', 'list'] as const;

export function useTransactions(filters: TransactionFilters = {}) {
  const limit = filters.limit ?? 50;
  return useInfiniteQuery({
    queryKey: [...LIST_KEY, filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      fetchJson<TransactionListResponse>(
        `/api/transactions${qs({
          from: filters.from,
          to: filters.to,
          category: filters.category,
          q: filters.q,
          limit,
          cursor: pageParam,
        })}`,
      ),
    getNextPageParam: (last) => last.nextCursor ?? undefined,
  });
}

export function useTransaction(id: string | undefined) {
  return useQuery({
    queryKey: ['transactions', 'one', id],
    queryFn: () => fetchJson<Transaction>(`/api/transactions/${id}`),
    enabled: !!id,
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ['transactions'] });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransactionCreate) =>
      fetchJson<Transaction>('/api/transactions', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: TransactionUpdate }) =>
      fetchJson<Transaction>(`/api/transactions/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      }),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<{ ok: boolean }>(`/api/transactions/${id}`, { method: 'DELETE' }),
    onSuccess: () => invalidateAll(qc),
  });
}
