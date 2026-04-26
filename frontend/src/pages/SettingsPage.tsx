import { useEffect, useState, type FormEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Field, inputClass } from '@/components/ui/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { PaperCard } from '@/components/ui/PaperCard';
import { Spinner } from '@/components/ui/Spinner';
import { useHealth } from '@/hooks/useHealth';
import { useSettings, useUpdateSettings } from '@/hooks/useSettings';
import { ApiError } from '@/lib/api';
import { QUICK_IMPORT_DEFAULTS, type Settings } from '@/lib/types';

const TIMEZONES = [
  'UTC',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Hong_Kong',
  'Asia/Seoul',
  'America/New_York',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
];

const CURRENCIES = ['USD', 'JPY', 'CNY', 'HKD', 'EUR', 'GBP', 'KRW'];

export function SettingsPage() {
  const settings = useSettings();

  if (settings.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-ink-500">
        <Spinner size={16} /> Loading settings…
      </div>
    );
  }
  if (settings.isError || !settings.data) {
    return <Alert tone="error">Failed to load settings.</Alert>;
  }

  return (
    <div className="grid max-w-2xl gap-4">
      <PageHeader eyebrow="Settings" title="Preferences" />
      <ProfileSection data={settings.data} />
      <ImportSection data={settings.data} />
      <ApiKeysSection data={settings.data} />
      <AboutSection />
    </div>
  );
}

function SectionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <PaperCard>
      <h2 className="mb-4 text-base font-semibold text-ink-900">{title}</h2>
      <div className="space-y-3">{children}</div>
    </PaperCard>
  );
}

function ProfileSection({ data }: { data: Settings }) {
  const update = useUpdateSettings();
  const profile = data.profile;
  const [fullName, setFullName] = useState(profile.fullName);
  const [preferredName, setPreferredName] = useState(profile.preferredName);
  const [email, setEmail] = useState(profile.email);
  const [timezone, setTimezone] = useState(profile.timezone);
  const [defaultCurrency, setDefaultCurrency] = useState(profile.defaultCurrency);
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'error'; msg: string } | null>(null);

  // Re-sync when settings refetch.
  useEffect(() => {
    setFullName(profile.fullName);
    setPreferredName(profile.preferredName);
    setEmail(profile.email);
    setTimezone(profile.timezone);
    setDefaultCurrency(profile.defaultCurrency);
  }, [profile]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFeedback(null);
    try {
      await update.mutateAsync({
        profile: { fullName, preferredName, email, timezone, defaultCurrency },
      });
      setFeedback({ tone: 'success', msg: 'Profile saved.' });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : 'Save failed.';
      setFeedback({ tone: 'error', msg });
    }
  }

  return (
    <SectionShell title="Profile">
      <form onSubmit={onSubmit} className="space-y-3">
        {feedback && <Alert tone={feedback.tone}>{feedback.msg}</Alert>}
        <Field label="Full name">
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={inputClass}
            placeholder="Your name"
          />
        </Field>
        <Field label="Preferred name" hint="What we call you in the app.">
          <input
            type="text"
            value={preferredName}
            onChange={(e) => setPreferredName(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Timezone">
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className={inputClass}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Default currency">
            <select
              value={defaultCurrency}
              onChange={(e) => setDefaultCurrency(e.target.value)}
              className={inputClass}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </form>
    </SectionShell>
  );
}

function ApiKeysSection({ data }: { data: Settings }) {
  const update = useUpdateSettings();
  const stored = data.apiKeys?.openai ?? '';
  const [openai, setOpenai] = useState('');
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'error'; msg: string } | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!openai.trim()) {
      setFeedback({ tone: 'error', msg: 'Paste a key first.' });
      return;
    }
    setFeedback(null);
    try {
      await update.mutateAsync({ apiKeys: { openai: openai.trim() } });
      setOpenai('');
      setFeedback({ tone: 'success', msg: 'OpenAI key saved.' });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : 'Save failed.';
      setFeedback({ tone: 'error', msg });
    }
  }

  async function onClear() {
    setFeedback(null);
    try {
      await update.mutateAsync({ apiKeys: { openai: null } });
      setOpenai('');
      setFeedback({ tone: 'success', msg: 'OpenAI key removed.' });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : 'Clear failed.';
      setFeedback({ tone: 'error', msg });
    }
  }

  return (
    <SectionShell title="API Keys">
      <form onSubmit={onSubmit} className="space-y-3">
        {feedback && <Alert tone={feedback.tone}>{feedback.msg}</Alert>}
        <Field
          label="OpenAI API key"
          hint="Used by the receipt-import pipeline. Stored locally in your SQLite — never sent anywhere except OpenAI."
        >
          <input
            type="password"
            value={openai}
            onChange={(e) => setOpenai(e.target.value)}
            placeholder={stored ? `…${stored.slice(-4)} (saved)` : 'sk-…'}
            className={inputClass}
            autoComplete="off"
          />
        </Field>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-ink-500">
            {stored ? `Currently set: ends in ${stored.slice(-4)}` : 'No key configured.'}
          </span>
          <div className="flex gap-2">
            {stored ? (
              <Button type="button" variant="ghost" onClick={onClear} disabled={update.isPending}>
                Clear
              </Button>
            ) : null}
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </div>
      </form>
    </SectionShell>
  );
}

function ImportSection({ data }: { data: Settings }) {
  const update = useUpdateSettings();
  const stored = data.import ?? {};
  const [quickImport, setQuickImport] = useState(
    stored.quickImport ?? QUICK_IMPORT_DEFAULTS.quickImport,
  );
  const [threshold, setThreshold] = useState(
    stored.confidenceThreshold ?? QUICK_IMPORT_DEFAULTS.confidenceThreshold,
  );
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'error'; msg: string } | null>(null);

  useEffect(() => {
    setQuickImport(stored.quickImport ?? QUICK_IMPORT_DEFAULTS.quickImport);
    setThreshold(stored.confidenceThreshold ?? QUICK_IMPORT_DEFAULTS.confidenceThreshold);
  }, [stored.quickImport, stored.confidenceThreshold]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFeedback(null);
    try {
      await update.mutateAsync({
        import: { quickImport, confidenceThreshold: threshold },
      });
      setFeedback({ tone: 'success', msg: 'Saved.' });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : 'Save failed.';
      setFeedback({ tone: 'error', msg });
    }
  }

  return (
    <SectionShell title="Import">
      <form onSubmit={onSubmit} className="space-y-3">
        {feedback && <Alert tone={feedback.tone}>{feedback.msg}</Alert>}

        <Field
          label="Quick import"
          hint="When ON, drafts with confidence above the threshold are saved automatically. Lower-confidence drafts still ask you to confirm one at a time."
        >
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-ink-900">
            <input
              type="checkbox"
              checked={quickImport}
              onChange={(e) => setQuickImport(e.target.checked)}
              className="h-4 w-4 rounded border-ink-300 text-ink-900 focus:ring-ink-900/20"
            />
            <span>{quickImport ? 'Enabled' : 'Disabled'}</span>
          </label>
        </Field>

        <Field
          label={`Confidence threshold · ${threshold.toFixed(2)}`}
          hint="Drafts at or above this are auto-saved when Quick import is on. 0.50 is permissive, 0.95 is strict."
        >
          <input
            type="range"
            min={0.5}
            max={0.95}
            step={0.05}
            value={threshold}
            onChange={(e) => setThreshold(Number.parseFloat(e.target.value))}
            disabled={!quickImport}
            className="w-full accent-ink-900 disabled:opacity-50"
          />
          <div className="mt-1 flex justify-between text-[11px] text-ink-500">
            <span>0.50 permissive</span>
            <span>0.80 default</span>
            <span>0.95 strict</span>
          </div>
        </Field>

        <div className="flex justify-end">
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </form>
    </SectionShell>
  );
}

function AboutSection() {
  const health = useHealth();
  return (
    <SectionShell title="About">
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
        <dt className="text-ink-500">App</dt>
        <dd className="text-ink-900">Mita Finance — Phase 1</dd>
        <dt className="text-ink-500">Backend</dt>
        <dd className="text-ink-900 font-mono text-xs">
          {health.data?.version ?? (health.isLoading ? 'loading…' : '—')}
        </dd>
      </dl>
    </SectionShell>
  );
}
