# MITA Finance — Design System

Shared across all phases. Read this alongside whichever `PHASE_N.md` you're working on.

Everything listed here is demonstrated in `design-references/Auto-accounting dashboard.html`
and defined in `design-references/styles.css`.

---

## Design tokens (CSS variables in `styles.css`)

### Neutrals — warm paper
- `--cream-50` → `--cream-400` · page, cards, subtle fills
- `--ink-100` → `--ink-900` · borders, text, strong surfaces
- `--paper` · page background (cream-100 light / ink-950 dark)

### Accents
- `--pos-500` (green) · income, positive states
- `--neg-500` (red) · expense, warnings
- `--accent-amber` · highlights, savings
- `--accent-blue`, `--accent-violet`, `--accent-teal` · category chips

### Typography
- `--font-ui` — system UI stack, body copy
- `--font-serif` — **Fraunces**, large numbers & section titles
- `--font-hand` — **Caveat / Kalam**, Variant B "journal" accents (Phase 3)
- `--font-mono` — code, `.env` preview, timestamps

### Geometry
- Radius: 6 / 9 / 12 / 16 px (button / field / card / hero)
- Borders: 1px `var(--ink-100)` or `var(--ink-200)`
- Shadow: 1px hairline `rgba(0,0,0,.04)` + 4px soft on hover. **Never a drop shadow on primary light-mode cards** — use borders.

### Dark mode (Phase 3)
Controlled by `<body data-theme="dark">`. `styles.css` defines the full ink-reversed palette under `[data-theme="dark"]`. Everything reads tokens, so dark mode is free once Phase 3 turns it on.

---

## Icons

Inline SVG registry in `primitives.jsx` → `Icon` component. Source: Lucide.

In a real project: `import { Settings, Moon, Sun, Sparkles } from 'lucide-react';`

---

## Component inventory

All reusable primitives live in `primitives.jsx`. Port these first.

| Primitive | Purpose |
|---|---|
| `PaperCard` | Workhorse container. 1px ink border, slight grain, 12px radius. Use everywhere instead of raw `<div>`. |
| `APButton` | Button. Variants: `primary`, `outline`, `ghost`. Sizes: `sm`, `md`, `lg`. Optional `icon` prop. |
| `Icon` | Inline SVG from the registry. |
| `CatPill` | Category chip. Reads from `CAT_COLORS` map. |
| `Num` | Wraps money/number text in `.tabular-nums` so columns align. |
| `fmtMoney(amount, currency)` | Formats by currency code. Negative = expense, positive = income. |

Chrome (layout-level) lives in `chrome.jsx`:
- `SideNav` — left sidebar with brand + nav items + bottom agent-status pill
- `TopBar` — right-aligned cluster: search (⌘K), language picker (Phase 3), theme toggle (Phase 3), avatar menu
- `AccountMenu` — avatar dropdown with profile card + Settings link + Sign out
- `ChatPanel` — right-docked overlay, 420px (Phase 3)

Charts live in `charts.jsx`. All SVG, all hand-drawn feel:
- `MonthlyFlow` — daily expense/income curve for current month
- `YearlyFlow` — 12-month bars
- `Sparkline` — tiny inline trend
- `CategoryDonut` — category spend breakdown

---

## Interaction patterns worth preserving

1. **Selected option in pickers** — bold text + ✓ mark. No checkmark-only / no bold-only.
2. **Pipeline stage cards** (Settings) — radio-style option list. Selected gets a thick left inset + solid dot.
3. **Transaction rows** — merchant in ink-900 medium, category pill on the right, amount tabular-nums right-aligned, sign-colored. Hover reveals edit / ellipsis.
4. **Savings goals** — watercolor-ish progress ring (see `GoalCard` in `dashboard-a.jsx`).
5. **Handwritten accents** (Phase 3 / Variant B) — section numbers, goal titles, and money pips use Caveat / Kalam.
6. **Language/currency pickers** — selected option bolded + ✓; on-change persists to localStorage.

---

## Things to NOT lift from the prototype

- `design-canvas.jsx` — Figma-ish canvas wrapper used only for presenting variants side-by-side. Don't port.
- `SAMPLE` hardcoded data at the bottom of `primitives.jsx` — replace with real API calls.
- Any component that only exists inside a dashboard variant and isn't exported from `primitives.jsx` — rebuild cleanly in your real codebase rather than copy-pasting.
- The inline `<script type="text/babel">` Babel setup — the prototype uses it so a single HTML file can render JSX. Your real app should use a real build tool.

---

## One aesthetic rule to preserve across everything

The prototype is deliberately **paper-like and quiet**. No gradients as page
backgrounds. No emoji used as UI (only as user-chosen content, e.g. goal icons).
No heavy drop shadows. If you find yourself adding visual noise to compensate
for a weak layout, fix the layout.
