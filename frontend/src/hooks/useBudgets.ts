import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { fetchJson, qs } from '@/lib/api';
import { periodBounds, todayInZone, type BudgetPlan, type BudgetSummary, type PeriodType } from '@/lib/budget';

export function useBudgetPeriod(timezone?: string) {
  const [params, setParams] = useSearchParams();
  const type: PeriodType = params.get('period') === 'week' ? 'week' : 'month';
  const candidate = params.get('date');
  const on = candidate && /^\d{4}-\d{2}-\d{2}$/.test(candidate) && !Number.isNaN(Date.parse(candidate)) ? candidate : todayInZone(timezone);
  const { start, end } = periodBounds(type, on);
  const today = todayInZone(timezone);
  return { type, on, start, end, switchOn: start <= today && today <= end ? today : on, search: `?period=${type}&date=${start}`,
    change: (period: PeriodType, date: string) => setParams({ period, date }) };
}

export function useBudgetPlans(type: PeriodType, start: string, end: string, currency: string) {
  return useQuery({ queryKey: ['budgets', 'plans', type, start, end, currency],
    queryFn: () => fetchJson<BudgetPlan[]>(`/api/budget-plans${qs({ periodType: type, from: start, to: end, currency })}`) });
}

export function useBudgetSummary(planId?: string) {
  return useQuery({ queryKey: ['budgets', 'summary', planId], enabled: !!planId,
    queryFn: () => fetchJson<BudgetSummary>(`/api/budget-plans/${planId}/summary`) });
}

export function useBudgetWrite() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ path, method = 'POST', body }: { path: string; method?: string; body?: unknown }) =>
    fetchJson<unknown>(path, { method, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }),
    onSuccess: async () => { await Promise.all([
      qc.invalidateQueries({ queryKey: ['budgets'] }), qc.invalidateQueries({ queryKey: ['transactions'] }),
    ]); } });
}
