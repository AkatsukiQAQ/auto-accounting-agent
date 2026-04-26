import { useQuery } from '@tanstack/react-query';
import { fetchJson } from '@/lib/api';
import type { Health } from '@/lib/types';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => fetchJson<Health>('/api/health'),
    staleTime: Infinity, // version doesn't change at runtime
  });
}
