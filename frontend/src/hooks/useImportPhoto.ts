import { useMutation } from '@tanstack/react-query';
import { fetchMultipart } from '@/lib/api';
import type { ImportPhotoResponse } from '@/lib/types';

export function useImportPhoto() {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('image', file);
      return fetchMultipart<ImportPhotoResponse>('/api/import/photo', form);
    },
  });
}
