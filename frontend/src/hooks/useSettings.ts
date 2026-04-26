import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchJson } from '@/lib/api';
import type { Settings } from '@/lib/types';

const KEY = ['settings'] as const;

export function useSettings() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => fetchJson<Settings>('/api/settings'),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Record<string, unknown>) =>
      fetchJson<Settings>('/api/settings', {
        method: 'PATCH',
        body: JSON.stringify(patch),
      }),
    onSuccess: (data) => {
      qc.setQueryData(KEY, data);
    },
  });
}
