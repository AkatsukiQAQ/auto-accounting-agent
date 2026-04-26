import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { ApiError } from '@/lib/api';
import type { Category, CategoryCreate, CategoryUpdate } from '@/lib/types';

interface Props {
  initial?: Category;
  onSubmit: (input: CategoryCreate | CategoryUpdate) => Promise<unknown>;
  onCancel: () => void;
}

const SLUG_RE = /^[a-z][a-z0-9_]{0,31}$/;
const HEX_RE = /^#[0-9A-Fa-f]{6}$/;

const SUGGESTED_COLORS: Array<[string, string]> = [
  ['#FCE5CE', '#D97706'],
  ['#DCE5F3', '#3B5EAA'],
  ['#F4DCE8', '#B56576'],
  ['#E5E0F3', '#6B5BA8'],
  ['#F9E6BD', '#C99A33'],
  ['#DDEED6', '#6E9455'],
  ['#D7E8CD', '#4F7B49'],
  ['#EEDFC8', '#9E6A37'],
  ['#E9E4D8', '#8B7E6C'],
];

export function CategoryForm({ initial, onSubmit, onCancel }: Props) {
  const editing = !!initial;
  const [id, setId] = useState(initial?.id ?? '');
  const [label, setLabel] = useState(initial?.label ?? '');
  const [colorBg, setColorBg] = useState(initial?.colorBg ?? '#E9E4D8');
  const [colorDot, setColorDot] = useState(initial?.colorDot ?? '#8B7E6C');
  const [keywordsText, setKeywordsText] = useState(
    (initial?.keywords ?? []).join(', '),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function clientValidate(): string | null {
    if (!editing && !SLUG_RE.test(id)) {
      return "Slug must be lowercase letters/digits/underscore, ≤32 chars, starting with a letter (e.g. 'coffee').";
    }
    if (!label.trim()) return 'Label is required.';
    if (!HEX_RE.test(colorBg)) return 'colorBg must be #RRGGBB.';
    if (!HEX_RE.test(colorDot)) return 'colorDot must be #RRGGBB.';
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const v = clientValidate();
    if (v) {
      setError(v);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const keywords = keywordsText
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      if (editing) {
        await onSubmit({
          label,
          colorBg,
          colorDot,
          keywords,
        } as CategoryUpdate);
      } else {
        await onSubmit({
          id,
          label,
          colorBg,
          colorDot,
          keywords,
          autoAssign: true,
        } as CategoryCreate);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Something went wrong.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error ? <Alert tone="error">{error}</Alert> : null}

      {!editing && (
        <Field label="ID (slug)" hint="lowercase, no spaces. Used in URLs and the API.">
          <input
            type="text"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="coffee"
            className={inputCls}
            required
          />
        </Field>
      )}

      <Field label="Label">
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Coffee"
          className={inputCls}
          required
        />
      </Field>

      <Field label="Colors">
        <div className="grid grid-cols-2 gap-2">
          <input
            type="text"
            value={colorBg}
            onChange={(e) => setColorBg(e.target.value)}
            placeholder="#FCE5CE"
            className={inputCls}
          />
          <input
            type="text"
            value={colorDot}
            onChange={(e) => setColorDot(e.target.value)}
            placeholder="#D97706"
            className={inputCls}
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SUGGESTED_COLORS.map(([bg, dot]) => (
            <button
              key={bg}
              type="button"
              title={`Use ${bg} / ${dot}`}
              onClick={() => {
                setColorBg(bg);
                setColorDot(dot);
              }}
              className="h-6 w-10 rounded-full border border-ink-200"
              style={{ background: bg }}
            >
              <span
                className="ml-1 inline-block h-2 w-2 rounded-full align-middle"
                style={{ background: dot }}
              />
            </button>
          ))}
        </div>
      </Field>

      <Field label="Keywords" hint="Comma-separated. The classifier matches these against merchant names.">
        <textarea
          value={keywordsText}
          onChange={(e) => setKeywordsText(e.target.value)}
          rows={3}
          className={inputCls + ' resize-y'}
          placeholder="starbucks, coffee, espresso"
        />
      </Field>

      <div className="flex items-center justify-end gap-2 pt-1">
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : editing ? 'Save' : 'Create'}
        </Button>
      </div>
    </form>
  );
}

const inputCls =
  'w-full rounded-lg border border-ink-200 bg-cream-50 px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/20';

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-ink-500">
        {label}
      </span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-ink-500">{hint}</span> : null}
    </label>
  );
}
