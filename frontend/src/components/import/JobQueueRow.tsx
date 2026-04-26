import { Icon } from '@/components/ui/Icon';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import type { Job } from '@/lib/importJob';
import { jobStats } from '@/lib/importJob';

interface Props {
  job: Job;
  /** Seconds elapsed since start (caller provides — ImportPage already ticks). */
  elapsedSec: number;
  /** Whether this job is the carousel target. Highlights the row. */
  isFocused?: boolean;
  /** Click handler — typically jumps the carousel to this job. */
  onClick?: () => void;
}

const STATUS_COLOR: Record<Job['status'], string> = {
  processing: 'bg-blue-50 text-blue-700 border-blue-300',
  reviewing: 'bg-cream-200 text-warn-500 border-warn-500',
  done: 'bg-pos-50 text-pos-500 border-pos-500',
  error: 'bg-neg-50 text-neg-500 border-neg-500',
};

export function JobQueueRow({ job, elapsedSec, isFocused, onClick }: Props) {
  const stats = jobStats(job);
  const summary = describeSummary(job, stats, elapsedSec);

  return (
    <div
      onClick={onClick}
      className={[
        'flex items-center gap-3 rounded-lg border p-2.5 transition-colors',
        isFocused
          ? 'border-ink-900 bg-cream-50'
          : 'border-cream-300 bg-cream-50 hover:bg-cream-100',
        onClick ? 'cursor-pointer' : '',
        job.status === 'done' ? 'opacity-70' : '',
      ].join(' ')}
    >
      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-md border border-cream-300 bg-cream-100">
        {job.previewUrl ? (
          <img src={job.previewUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <Icon name="image" size={16} className="text-ink-500" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium text-ink-900">
          {job.fileName}
        </div>
        <div className="truncate text-[11px] text-ink-500">{summary}</div>
      </div>

      <span
        className={[
          'inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold capitalize',
          STATUS_COLOR[job.status],
        ].join(' ')}
      >
        {job.status === 'processing' ? <Spinner size={10} /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
        {job.status}
      </span>
    </div>
  );
}

function describeSummary(
  job: Job,
  stats: ReturnType<typeof jobStats>,
  elapsedSec: number,
): string {
  if (job.status === 'processing') return `Running OCR · ${elapsedSec}s elapsed`;
  if (job.status === 'error') return job.errorMessage ?? 'Failed';
  if (stats.total === 0) return 'No receipts found';
  const parts: string[] = [];
  if (stats.saved > 0) parts.push(`${stats.saved} saved`);
  if (stats.skipped > 0) parts.push(`${stats.skipped} skipped`);
  if (stats.errored > 0) parts.push(`${stats.errored} errored`);
  if (job.status === 'reviewing') {
    if (stats.pending > 0) parts.push(`${stats.pending} to confirm`);
    return parts.join(' · ') || 'Ready to review';
  }
  return parts.join(' · ');
}

interface QueueButtonProps {
  onResumeReview: () => void;
}

export function ResumeReviewButton({ onResumeReview }: QueueButtonProps) {
  return (
    <Button size="sm" variant="outline" onClick={onResumeReview}>
      Resume review
    </Button>
  );
}
