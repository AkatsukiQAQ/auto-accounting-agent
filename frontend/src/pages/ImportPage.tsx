import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Icon } from '@/components/ui/Icon';
import { PaperCard } from '@/components/ui/PaperCard';
import { Spinner } from '@/components/ui/Spinner';
import { TransactionForm } from '@/components/transactions/TransactionForm';
import { JobQueueRow } from '@/components/import/JobQueueRow';
import { PageHeader } from '@/components/layout/PageHeader';
import { useImportPhoto } from '@/hooks/useImportPhoto';
import { useCreateTransaction } from '@/hooks/useTransactions';
import { useSettings } from '@/hooks/useSettings';
import { ApiError } from '@/lib/api';
import {
  type DraftItem,
  type Job,
  findNextEditable,
  findPrevEditable,
  isAutoSavable,
  isReviewing,
  jobStats,
  remainingCount,
} from '@/lib/importJob';
import { QUICK_IMPORT_DEFAULTS, type TransactionCreate } from '@/lib/types';

type Tab = 'photo' | 'manual';

const HISTORY_FADE_MS = 60_000;

export function ImportPage() {
  const [tab, setTab] = useState<Tab>('photo');

  // ─── Photo flow state (lifted above the tab switcher so it survives) ───
  const settings = useSettings();
  const importM = useImportPhoto();
  const createM = useCreateTransaction();
  const navigate = useNavigate();

  const quickImport =
    settings.data?.import?.quickImport ?? QUICK_IMPORT_DEFAULTS.quickImport;
  const threshold =
    settings.data?.import?.confidenceThreshold ??
    QUICK_IMPORT_DEFAULTS.confidenceThreshold;

  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [history, setHistory] = useState<Job[]>([]);
  const [pickedFile, setPickedFile] = useState<File | null>(null);
  const [pickedPreview, setPickedPreview] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<{ code: string; message: string } | null>(null);
  const [tickSec, setTickSec] = useState(0);
  const [direction, setDirection] = useState<'forward' | 'backward'>('forward');
  const [animTick, setAnimTick] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const intentRef = useRef<'one' | 'all'>('one');
  /** Refs to active timeouts so we can clear on unmount. */
  const fadeTimers = useRef<Map<string, number>>(new Map());

  const carouselVisible = isReviewing(activeJob);
  const isBusy =
    !!activeJob && (activeJob.status === 'processing' || activeJob.status === 'reviewing');

  // ─── Effects ───────────────────────────────────────────────────────────

  // Tick the elapsed-time counter for the active processing job.
  useEffect(() => {
    if (activeJob?.status !== 'processing') {
      setTickSec(0);
      return;
    }
    setTickSec(Math.floor((Date.now() - activeJob.startedAt) / 1000));
    const id = window.setInterval(() => {
      setTickSec(Math.floor((Date.now() - activeJob.startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [activeJob?.status, activeJob?.startedAt]);

  // Manage object URL for the currently-picked file (before upload starts).
  useEffect(() => {
    if (!pickedFile) {
      setPickedPreview(null);
      return;
    }
    const url = URL.createObjectURL(pickedFile);
    setPickedPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pickedFile]);

  // Schedule fade-out for history items that have a fadeAt timestamp.
  useEffect(() => {
    for (const job of history) {
      if (!job.fadeAt) continue;
      if (fadeTimers.current.has(job.id)) continue;
      const ms = Math.max(0, job.fadeAt - Date.now());
      const id = window.setTimeout(() => {
        setHistory((h) => h.filter((j) => j.id !== job.id));
        if (job.previewUrl) URL.revokeObjectURL(job.previewUrl);
        fadeTimers.current.delete(job.id);
      }, ms);
      fadeTimers.current.set(job.id, id);
    }
    // Snapshot for cleanup so we don't capture a stale ref.
    const timers = fadeTimers.current;
    return () => {
      // Don't wipe on every effect run — only on unmount.
      // (This effect re-runs when history changes, but timers per-id stay valid.)
      void timers;
    };
  }, [history]);

  // On unmount, clear all timers.
  useEffect(() => {
    return () => {
      for (const id of fadeTimers.current.values()) window.clearTimeout(id);
      fadeTimers.current.clear();
    };
  }, []);

  // ─── Helpers ───────────────────────────────────────────────────────────

  function clearPickedFile() {
    setPickedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function pickFile(f: File | null | undefined) {
    if (!f) return;
    if (!f.type.startsWith('image/')) {
      setUploadError({ code: 'unsupported_image', message: 'Please pick a JPEG / PNG / WebP image.' });
      return;
    }
    setPickedFile(f);
    setUploadError(null);
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    pickFile(e.dataTransfer.files?.[0]);
  }

  function moveJobToHistory(job: Job) {
    const fading: Job = { ...job, fadeAt: Date.now() + HISTORY_FADE_MS };
    setHistory((h) => [fading, ...h]);
    setActiveJob(null);
  }

  // ─── Upload + pipeline orchestration ───────────────────────────────────

  async function uploadFile(file: File) {
    if (isBusy) return;
    setUploadError(null);

    const previewUrl = URL.createObjectURL(file);
    const job: Job = {
      id: crypto.randomUUID(),
      fileName: file.name,
      fileSizeBytes: file.size,
      previewUrl,
      status: 'processing',
      startedAt: Date.now(),
      response: null,
      items: [],
      cursor: 0,
    };
    setPickedFile(null);
    setPickedPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setActiveJob(job);
    setTickSec(0);

    try {
      const result = await importM.mutateAsync(file);
      let items: DraftItem[] = result.previewTransactions.map((d, i) => ({
        key: i,
        draft: d,
        confidence: result.confidences[i] ?? 0,
        status: 'pending',
      }));

      // Quick-import auto-save loop.
      if (quickImport) {
        for (let i = 0; i < items.length; i += 1) {
          if (isAutoSavable(items[i], threshold)) {
            try {
              await createM.mutateAsync(items[i].draft);
              items[i] = { ...items[i], status: 'saved' };
            } catch (err) {
              items[i] = {
                ...items[i],
                status: 'error',
                errorMessage: err instanceof Error ? err.message : 'Auto-save failed.',
              };
            }
          }
        }
      }

      const allHandled = items.every((it) => it.status === 'saved');
      const reviewedJob: Job = {
        ...job,
        status: allHandled ? 'done' : 'reviewing',
        response: result,
        items,
        cursor: Math.max(0, items.findIndex((it) => it.status !== 'saved')),
      };

      if (allHandled) {
        moveJobToHistory(reviewedJob);
      } else {
        setActiveJob(reviewedJob);
        setDirection('forward');
        setAnimTick((t) => t + 1);
      }
    } catch (err) {
      const code = err instanceof ApiError ? err.code : 'unknown';
      const message =
        err instanceof ApiError || err instanceof Error ? err.message : 'Upload failed.';
      setUploadError({ code, message });
      // Discard the job on upload failure — top alert tells the user.
      if (job.previewUrl) URL.revokeObjectURL(job.previewUrl);
      setActiveJob(null);
    }
  }

  // ─── Carousel actions ──────────────────────────────────────────────────

  function updateActive(updater: (job: Job) => Job) {
    setActiveJob((j) => (j ? updater(j) : j));
  }

  async function commitDraft(input: TransactionCreate, idx: number, jobItems: DraftItem[]): Promise<DraftItem[]> {
    try {
      await createM.mutateAsync(input);
      return jobItems.map((x, i) =>
        i === idx ? { ...x, draft: input, status: 'saved', errorMessage: undefined } : x,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Save failed.';
      return jobItems.map((x, i) =>
        i === idx ? { ...x, draft: input, status: 'error', errorMessage: msg } : x,
      );
    }
  }

  async function onSubmitForm(input: TransactionCreate) {
    if (!activeJob) return;
    const job = activeJob;
    if (intentRef.current === 'all') {
      // Save current + all subsequent non-saved items.
      let items = await commitDraft(input, job.cursor, job.items);
      for (let i = job.cursor + 1; i < items.length; i += 1) {
        if (items[i].status === 'saved') continue;
        try {
          await createM.mutateAsync(items[i].draft);
          items = items.map((x, k) => (k === i ? { ...x, status: 'saved' } : x));
        } catch (err) {
          const msg = err instanceof Error ? err.message : 'Save failed.';
          items = items.map((x, k) =>
            k === i ? { ...x, status: 'error', errorMessage: msg } : x,
          );
        }
      }
      const finalJob: Job = { ...job, items, cursor: items.length, status: 'done' };
      moveJobToHistory(finalJob);
    } else {
      const items = await commitDraft(input, job.cursor, job.items);
      const nextIdx = findNextEditable(items, job.cursor);
      if (nextIdx === -1) {
        const finalJob: Job = { ...job, items, cursor: items.length, status: 'done' };
        moveJobToHistory(finalJob);
      } else {
        setDirection('forward');
        setAnimTick((t) => t + 1);
        updateActive((j) => ({ ...j, items, cursor: nextIdx }));
      }
    }
  }

  function onSkip() {
    if (!activeJob) return;
    const items = activeJob.items.map((x, i) =>
      i === activeJob.cursor ? { ...x, status: 'skipped' as const } : x,
    );
    const nextIdx = findNextEditable(items, activeJob.cursor);
    if (nextIdx === -1) {
      const finalJob: Job = {
        ...activeJob,
        items,
        cursor: items.length,
        status: 'done',
      };
      moveJobToHistory(finalJob);
    } else {
      setDirection('forward');
      setAnimTick((t) => t + 1);
      updateActive((j) => ({ ...j, items, cursor: nextIdx }));
    }
  }

  function onPrevious() {
    if (!activeJob) return;
    const prevIdx = findPrevEditable(activeJob.items, activeJob.cursor);
    if (prevIdx === -1) return;
    setDirection('backward');
    setAnimTick((t) => t + 1);
    updateActive((j) => ({ ...j, cursor: prevIdx }));
  }

  function onDiscardRemaining() {
    if (!activeJob) return;
    const items = activeJob.items.map((x) =>
      x.status === 'saved' ? x : { ...x, status: 'skipped' as const },
    );
    const finalJob: Job = { ...activeJob, items, cursor: items.length, status: 'done' };
    moveJobToHistory(finalJob);
  }

  // ─── Render ────────────────────────────────────────────────────────────

  // Compose queue list (active + history). Active item, if any, shows on top.
  const queueRows: Job[] = activeJob ? [activeJob, ...history] : history;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Import"
        title="Capture a receipt"
        hint="Upload a screenshot, or add an entry manually."
      />
      <div className="inline-flex rounded-lg border border-ink-200 bg-cream-100 p-1">
        <TabButton active={tab === 'photo'} onClick={() => setTab('photo')}>
          Photo
        </TabButton>
        <TabButton active={tab === 'manual'} onClick={() => setTab('manual')}>
          Manual
        </TabButton>
      </div>

      {tab === 'photo' ? (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* ── Upload zone ─── */}
            <PaperCard>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={onDrop}
                className="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-ink-200 bg-cream-50 p-8 text-center"
              >
                <Icon name="upload" size={28} className="text-ink-500" />
                <div className="text-sm text-ink-700">
                  Drop a receipt image here, or
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => pickFile(e.target.files?.[0])}
                />
                <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
                  Browse files
                </Button>
                {pickedFile && (
                  <div className="flex items-center gap-3 text-xs text-ink-700">
                    {pickedPreview && (
                      <img
                        src={pickedPreview}
                        alt=""
                        className="h-12 w-12 rounded border border-cream-200 object-cover"
                      />
                    )}
                    <div>
                      <div className="font-medium">{pickedFile.name}</div>
                      <div className="text-ink-500">{(pickedFile.size / 1024).toFixed(0)} KB</div>
                    </div>
                  </div>
                )}
              </div>

              {uploadError && (
                <div className="mt-3">
                  <Alert tone="error">
                    {uploadError.code === 'api_key_not_configured' ? (
                      <>
                        OpenAI API key not configured.{' '}
                        <Link to="/settings" className="underline">
                          Set it on Settings
                        </Link>{' '}
                        first.
                      </>
                    ) : uploadError.code === 'unsupported_image' ? (
                      <>We couldn't read this image. Try a clearer JPEG / PNG.</>
                    ) : uploadError.code === 'pipeline_llm_error' ? (
                      <>OpenAI is having trouble. Try again in a moment.</>
                    ) : (
                      uploadError.message
                    )}
                  </Alert>
                </div>
              )}

              <div className="mt-3 flex justify-end gap-2">
                {pickedFile && !isBusy && (
                  <Button variant="ghost" onClick={clearPickedFile}>
                    Reset
                  </Button>
                )}
                <Button
                  onClick={() => pickedFile && uploadFile(pickedFile)}
                  disabled={!pickedFile || isBusy}
                >
                  {isBusy && activeJob?.status === 'processing' ? (
                    <>
                      <Spinner size={14} /> Processing… {tickSec}s
                    </>
                  ) : isBusy ? (
                    'Reviewing…'
                  ) : (
                    'Upload'
                  )}
                </Button>
              </div>
            </PaperCard>

            {/* ── Mita's tips ─── */}
            <PaperCard>
              <h3 className="hand-body mb-3 text-2xl text-ink-900">Mita's tips</h3>
              <ul className="space-y-2 pl-5 text-sm text-ink-700" style={{ listStyle: 'disc' }}>
                <li>Drop a receipt image — single receipts and multi-receipt screenshots both work.</li>
                <li>Each upload takes <strong>30–60 seconds</strong>; you can switch tabs while it runs.</li>
                <li>
                  Each receipt becomes a draft you can edit.{' '}
                  {quickImport
                    ? 'High-confidence ones are saved automatically.'
                    : 'Turn on Quick import in Settings to skip the obvious ones.'}
                </li>
              </ul>
              {settings.data && !settings.data.apiKeys?.openai && (
                <div className="mt-3">
                  <Alert tone="warning">
                    No OpenAI key set.{' '}
                    <Link to="/settings" className="underline">
                      Configure it first.
                    </Link>
                  </Alert>
                </div>
              )}
            </PaperCard>
          </div>

          {/* ── Queue ─── */}
          {queueRows.length > 0 && (
            <PaperCard>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                Processing queue
              </h3>
              <div className="space-y-1.5">
                {queueRows.map((job) => (
                  <JobQueueRow
                    key={job.id}
                    job={job}
                    elapsedSec={tickSec}
                    isFocused={job.id === activeJob?.id && carouselVisible}
                  />
                ))}
              </div>
            </PaperCard>
          )}

          {/* ── Carousel ─── */}
          {carouselVisible && activeJob && (
            <CarouselArea
              job={activeJob}
              direction={direction}
              animTick={animTick}
              defaultCurrency={settings.data?.profile.defaultCurrency ?? 'JPY'}
              quickImport={quickImport}
              isPending={createM.isPending}
              intentRef={intentRef}
              onSubmitForm={onSubmitForm}
              onSkip={onSkip}
              onPrevious={onPrevious}
              onDiscard={onDiscardRemaining}
              onViewRecords={() => navigate('/records')}
            />
          )}
        </div>
      ) : (
        <ManualTab />
      )}
    </div>
  );
}

// ─────────────────────────────── Tab button ───────────────────────────────

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-md px-3 py-1 text-sm font-medium transition-colors',
        active ? 'bg-ink-900 text-cream-50' : 'text-ink-700 hover:bg-cream-200',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

// ─────────────────────────────── Carousel area ────────────────────────────

interface CarouselProps {
  job: Job;
  direction: 'forward' | 'backward';
  animTick: number;
  defaultCurrency: string;
  quickImport: boolean;
  isPending: boolean;
  intentRef: React.MutableRefObject<'one' | 'all'>;
  onSubmitForm: (input: TransactionCreate) => Promise<void>;
  onSkip: () => void;
  onPrevious: () => void;
  onDiscard: () => void;
  onViewRecords: () => void;
}

function CarouselArea({
  job,
  direction,
  animTick,
  defaultCurrency,
  quickImport,
  isPending,
  intentRef,
  onSubmitForm,
  onSkip,
  onPrevious,
  onDiscard,
}: CarouselProps) {
  const stats = jobStats(job);
  const remaining = remainingCount(job);
  const current = job.items[job.cursor];
  if (!current) return null;
  const formId = `draft-form-${job.id}-${current.key}-${animTick}`;
  const canPrev = findPrevEditable(job.items, job.cursor) !== -1;
  const remainingAfter = job.items
    .slice(job.cursor + 1)
    .filter((x) => x.status !== 'saved').length;

  return (
    <div className="space-y-3">
      <PaperCard>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-ink-900">
              {job.items.length === 1
                ? 'Confirm this draft'
                : `Reviewing ${job.cursor + 1} of ${job.items.length}`}
            </h3>
            <p className="mt-0.5 text-xs text-ink-500">
              {quickImport && stats.saved > 0 ? (
                <>
                  {stats.saved} auto-saved
                  {stats.errored > 0 ? ` · ${stats.errored} need a second look` : ''}
                  {' · '}
                  {remaining} to confirm.
                </>
              ) : (
                <>{remaining} to confirm.</>
              )}
            </p>
          </div>
          <Button variant="ghost" onClick={onDiscard} disabled={isPending}>
            Discard remaining
          </Button>
        </div>

        {job.response?.ocrText && (
          <details className="mt-3 text-xs">
            <summary className="cursor-pointer text-ink-500">
              OCR text · {job.response.ocrEngine}
            </summary>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-cream-50 p-2 text-ink-700">
              {job.response.ocrText}
            </pre>
          </details>
        )}

        {job.items.length > 1 && (
          <div className="mt-3 flex items-center gap-1.5">
            {job.items.map((it, i) => (
              <span
                key={it.key}
                className={[
                  'h-1.5 rounded-full transition-all',
                  it.status === 'saved'
                    ? 'w-6 bg-pos-500'
                    : it.status === 'skipped'
                      ? 'w-3 bg-ink-200'
                      : it.status === 'error'
                        ? 'w-4 bg-neg-500'
                        : i === job.cursor
                          ? 'w-8 bg-ink-900'
                          : 'w-3 bg-ink-200',
                ].join(' ')}
                title={`${i + 1}: ${it.status}`}
              />
            ))}
          </div>
        )}
      </PaperCard>

      <div
        key={`carousel-${current.key}-${animTick}`}
        className={direction === 'forward' ? 'slide-in-from-right' : 'slide-in-from-left'}
      >
        <DraftCard
          index={job.cursor}
          total={job.items.length}
          draft={current.draft}
          confidence={current.confidence}
          errorMessage={current.errorMessage}
          previewImageUrl={job.previewUrl}
          defaultCurrency={defaultCurrency}
          formId={formId}
          onSubmit={onSubmitForm}
        />

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <Button
            variant="outline"
            onClick={onPrevious}
            disabled={isPending || !canPrev}
          >
            ← Previous
          </Button>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" onClick={onSkip} disabled={isPending}>
              Skip
            </Button>
            <Button
              type="submit"
              form={formId}
              onClick={() => {
                intentRef.current = 'one';
              }}
              disabled={isPending}
            >
              {isPending && intentRef.current === 'one' ? 'Saving…' : 'Save next'}
            </Button>
            {remainingAfter > 0 && (
              <Button
                type="submit"
                form={formId}
                variant="outline"
                onClick={() => {
                  intentRef.current = 'all';
                }}
                disabled={isPending}
              >
                {isPending && intentRef.current === 'all'
                  ? 'Saving all…'
                  : `Save all remaining (${remainingAfter + 1})`}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────── Draft card ────────────────────────────────

interface DraftCardProps {
  index: number;
  total: number;
  draft: TransactionCreate;
  confidence: number;
  errorMessage?: string;
  previewImageUrl: string | null;
  defaultCurrency: string;
  formId: string;
  onSubmit: (input: TransactionCreate) => Promise<unknown>;
}

function DraftCard({
  index,
  total,
  draft,
  confidence,
  errorMessage,
  previewImageUrl,
  defaultCurrency,
  formId,
  onSubmit,
}: DraftCardProps) {
  const lowConf = confidence < 0.5;
  return (
    <PaperCard>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {previewImageUrl && total > 1 && (
            <img
              src={previewImageUrl}
              alt=""
              className="h-12 w-12 rounded border border-cream-200 object-cover"
            />
          )}
          <div>
            <h4 className="text-sm font-semibold text-ink-900">
              Draft {index + 1} of {total}
            </h4>
            <div className="mt-0.5 flex items-center gap-2 text-xs">
              <span className="text-ink-500">Confidence</span>
              <span
                className={[
                  'font-mono font-semibold',
                  lowConf ? 'text-neg-500' : 'text-ink-900',
                ].join(' ')}
              >
                {confidence.toFixed(2)}
              </span>
              {lowConf && (
                <span className="rounded-full bg-neg-50 px-2 py-0.5 text-[11px] font-semibold text-neg-500">
                  low — double-check
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="mb-3">
          <Alert tone="error">{errorMessage}</Alert>
        </div>
      )}

      <TransactionForm
        initial={draft}
        defaultCurrency={defaultCurrency}
        formId={formId}
        hideSubmitButton
        onSubmit={(input) => onSubmit(input as TransactionCreate)}
      />
    </PaperCard>
  );
}

// ─────────────────────────────── Manual tab ────────────────────────────────

function ManualTab() {
  const createM = useCreateTransaction();
  const settings = useSettings();
  const navigate = useNavigate();
  return (
    <PaperCard>
      <TransactionForm
        defaultCurrency={settings.data?.profile.defaultCurrency ?? 'JPY'}
        submitLabel="Add Transaction"
        onSubmit={async (input) => {
          await createM.mutateAsync(input as TransactionCreate);
          navigate('/records');
        }}
      />
    </PaperCard>
  );
}

