# MITA Finance — Handoff package

Reference prototype + specs for building the MITA Finance frontend **and**
rebuilding the backend pipeline underneath it. **Not** a shipping app — a
design and contract reference for your real codebase.

---

## ⚠️ Two tracks, run in phases. Give Claude Code one phase at a time.

This package splits work into **two parallel tracks** that converge:

- **Frontend track** (`PHASE_1.md` → `PHASE_2.md` → `PHASE_3.md`) — build the UI
  against the API contract defined in each phase. Can start with mock data; doesn't
  have to wait for the backend.
- **Backend track** (`BACKEND_PHASE_0.md` → `BACKEND_PHASE_1.md` → `BACKEND_PHASE_2.md`) —
  rebuild the OCR pipeline into a real HTTP service with persistence, aligned
  with the API contracts the frontend phases promise.

The existing backend (`AkatsukiQAQ/auto-accounting-agent` on GitHub) is a
proof-of-concept: three LangChain tools chained by a LangGraph agent, no DB,
no HTTP layer, categories in YAML. **Useful algorithms, wrong architecture for
a product.** The backend track rebuilds it; the frontend track doesn't care
how the backend is implemented as long as it speaks the API.

The prototype in `design-references/` shows the **final product vision**.
Handing all of that to Claude Code in one prompt produces a half-broken
codebase with shaky data cascades and schema rework every two days.
Scope one phase at a time.

### Phase matrix

| # | Frontend | Backend | What exists after |
|---|---|---|---|
| 0 | — | [`BACKEND_PHASE_0.md`](./BACKEND_PHASE_0.md) | Legacy pipeline's core algorithms extracted as pure functions, framework-free. Half-day to a day. |
| 1 | [`PHASE_1.md`](./PHASE_1.md) | [`BACKEND_PHASE_1.md`](./BACKEND_PHASE_1.md) | Working capture tool: Dashboard, Records, Import, Categories, Settings. `transactions` + `categories` tables. REST API. 2–3 days front + 3–4 days back. |
| 2 | [`PHASE_2.md`](./PHASE_2.md) | [`BACKEND_PHASE_2.md`](./BACKEND_PHASE_2.md) | Actual finance system: Accounts, Budgets, Recurring, Review queue, Transfers. Cascade logic. Merchant normalization. ~1 week each side. |
| 3 | [`PHASE_3.md`](./PHASE_3.md) | *(inlined in PHASE_3.md per feature)* | Agent intelligence: learning rules, pipeline visualization, chatbot, dark mode, i18n. Ongoing. |

**Always shared** (read alongside any phase):
- [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md) — tokens, typography, component inventory. Phase-agnostic.
- [`design-references/Auto-accounting dashboard.html`](./design-references/) — the interactive prototype. Visual reference only; **ignore screens that aren't in the current phase's doc.**
- [`design-references/src/*.jsx`](./design-references/src/) — JSX source per screen.
- [`design-references/styles.css`](./design-references/styles.css) — design tokens as CSS variables.

---

## Recommended workflow with Claude Code

### Backend-first order (recommended for a solo project)

1. Ship `BACKEND_PHASE_0.md` — extract the pure functions. Half day.
2. Pick your stack (see §"Stack questions" at the end of each backend phase).
3. Ship `BACKEND_PHASE_1.md` — real HTTP API with OpenAPI schema, running locally. Frontend doesn't exist yet; test with `curl` / `httpie` / the auto-generated docs UI.
4. Ship `PHASE_1.md` (frontend) against the real backend. End-to-end working capture tool. Deploy and use it.
5. Ship `BACKEND_PHASE_2.md`, then `PHASE_2.md`. Repeat.
6. Phase 3: pick one feature at a time (Tier A first). Each one might touch both sides; `PHASE_3.md` calls out the backend needs inline.

### Parallel order (if you can context-switch)

Both phase-1 documents define the same API contract. You can build the frontend against a mock API (MSW, `vite-plugin-mock`, or hand-rolled) while the backend comes up. Converge when both are done. Faster in wall-clock time but requires keeping two Claude Code sessions coherent — only worth it if you're comfortable with that.

### Session hygiene

Open a **fresh Claude Code session per phase.** Give it only the files for the current phase:

- **Frontend Phase N** → `HANDOFF.md` + `DESIGN_SYSTEM.md` + `PHASE_N.md` + `design-references/`
- **Backend Phase N** → `HANDOFF.md` + `BACKEND_PHASE_N.md` + (for Phase 1+) previous backend phases as schema reference + the real backend repo

Starting fresh per phase matters more than it sounds — old sessions accumulate bad assumptions from the smaller schema that will bleed into later decisions.

---

## Repository layout

```
handoff_mita_finance/
├── HANDOFF.md                          # (this file) — index + workflow
│
│   # Frontend track
├── PHASE_1.md                          # FE Sprint 1: pipeline + dashboard + records
├── PHASE_2.md                          # FE Sprint 2: accounts, budgets, recurring, review
├── PHASE_3.md                          # FE Sprint 3+: agent intelligence, polish (has inline backend notes)
│
│   # Backend track
├── BACKEND_PHASE_0.md                  # BE prep: extract pure functions from legacy pipeline
├── BACKEND_PHASE_1.md                  # BE Sprint 1: HTTP + DB, rebuilt pipeline, aligns with FE P1
├── BACKEND_PHASE_2.md                  # BE Sprint 2: cascade, normalization, recurring worker, review queue
│
│   # Shared
├── DESIGN_SYSTEM.md                    # Shared across all phases
└── design-references/
    ├── Auto-accounting dashboard.html  # Interactive prototype (open in browser)
    ├── styles.css                      # Design tokens + base styles
    ├── design-canvas.jsx               # Canvas wrapper (prototype-only — don't port)
    ├── ds/
    │   └── colors_and_type.css         # Base design system (Master Component DS)
    └── src/
        ├── app.jsx                     # Prototype root
        ├── primitives.jsx              # Icon, APButton, PaperCard, CatPill, fmtMoney, SAMPLE
        ├── charts.jsx                  # MonthlyFlow, YearlyFlow, Sparkline, CategoryDonut
        ├── chrome.jsx                  # SideNav, TopBar, LanguagePicker, AccountMenu, ChatPanel
        ├── dashboard-a.jsx             # Phase 1 — Classic ledger
        ├── dashboard-b.jsx             # Phase 3 — Handwritten journal variant
        ├── dashboard-c.jsx             # Phase 3 — Control room variant
        ├── screens.jsx                 # Records, Import, Budget v1, Categories, Settings
        ├── new-screens.jsx             # Phase 2 — Accounts, Recurring, Review, BudgetScreenV2
        └── i18n.jsx                    # Phase 3 — three-language dictionary
```

---

## A note on the legacy backend

If you've already read the `auto-accounting-agent` repo:

- The pipeline is three LangChain tools (`ocr_tool`, `model_ocr_result_parser`, `classification_tool`) chained by `create_react_agent`.
- No DB, no HTTP, categories in `backend/configs/CategoryConfigs.yaml`.
- Structures OCR output as `ParsedReceipt` (merchant, amount, currency, date, time, raw_text).
- Classifies via regex-first (YAML keywords compiled to regex), LLM fallback for unmatched, two-stage if a top-level match has subcategories.

What's worth keeping for the rebuild (see `BACKEND_PHASE_0.md`):

- Currency detection (`CurrencyParser` — the symbol table, disambiguation rules for `$` and `¥`).
- Category keyword regex compilation (`_compile_regex_pattern`).
- The two-stage classify-then-subclassify flow for categories with children.
- The Pydantic schemas (`ParsedReceipt`, `ReceiptCategory`) — they're good; they just need to stop being the storage format and become an intermediate DTO.

What to replace:

- LangGraph `create_react_agent` as the pipeline driver → a plain orchestrator class that calls stages in order. You get determinism, testability, and the ability to return intermediate stage outputs to the UI.
- `ChatOpenAI(model="gpt-5-nano", ...)` hardcoded three times → one LLM client behind a `PipelineLLM` interface, with the model name in config.
- YAML category file as source of truth → DB table, seeded from YAML on first boot.
- No persistence → SQLAlchemy models + Alembic migrations.
- No HTTP → FastAPI (recommended — Pydantic is already a dependency) with routes matching the frontend phase contracts.
