// Types and helpers for the import job queue.
//
// One Job = one uploaded image and the pipeline run on top of it. The job
// progresses through processing → reviewing → done (or error). The carousel
// operates on `activeJob.items`; finished jobs go to a fading history list.

import type { ImportPhotoResponse, TransactionCreate } from '@/lib/types';

export type DraftStatus = 'pending' | 'saved' | 'skipped' | 'error';

export interface DraftItem {
  /** Stable identity for animation keying within a job. */
  key: number;
  draft: TransactionCreate;
  confidence: number;
  status: DraftStatus;
  errorMessage?: string;
}

export type JobStatus = 'processing' | 'reviewing' | 'done' | 'error';

export interface Job {
  id: string;
  fileName: string;
  fileSizeBytes: number;
  /** Object URL for thumbnail. Revoke when job leaves history. */
  previewUrl: string | null;
  status: JobStatus;
  /** ms epoch */
  startedAt: number;

  // Populated once status hits 'reviewing'.
  response: ImportPhotoResponse | null;
  items: DraftItem[];
  cursor: number;

  errorMessage?: string;
  /** ms epoch when this job's history row should auto-remove. */
  fadeAt?: number;
}

/** A draft is auto-savable if it cleared the threshold AND has the minimum
 *  required fields. Empty-OCR placeholders explicitly fail this. */
export function isAutoSavable(item: DraftItem, threshold: number): boolean {
  return (
    item.confidence >= threshold &&
    !!item.draft.merchant &&
    item.draft.merchant !== 'Unknown' &&
    item.draft.amountCents !== 0 &&
    !!item.draft.currency
  );
}

// Linear navigation through the draft list. Saved/skipped items are still
// reachable — the user might want to re-verify them. The carousel UI handles
// per-status presentation (read-only banner for saved items, etc.).
export function findNext(items: DraftItem[], from: number): number {
  return from + 1 < items.length ? from + 1 : -1;
}

export function findPrev(_items: DraftItem[], from: number): number {
  return from > 0 ? from - 1 : -1;
}

export interface JobStats {
  saved: number;
  skipped: number;
  errored: number;
  pending: number;
  total: number;
}

export function jobStats(job: Job): JobStats {
  let saved = 0;
  let skipped = 0;
  let errored = 0;
  let pending = 0;
  for (const it of job.items) {
    if (it.status === 'saved') saved += 1;
    else if (it.status === 'skipped') skipped += 1;
    else if (it.status === 'error') errored += 1;
    else pending += 1;
  }
  return { saved, skipped, errored, pending, total: job.items.length };
}

/** Should the carousel be visible right now? Only for the active job, only
 *  while there's still something to confirm. */
export function isReviewing(job: Job | null): boolean {
  if (!job) return false;
  if (job.status !== 'reviewing') return false;
  return jobStats(job).pending > 0 || jobStats(job).errored > 0;
}

/** Remaining unhandled items (not saved). */
export function remainingCount(job: Job): number {
  const s = jobStats(job);
  return s.pending + s.errored + s.skipped;
}
