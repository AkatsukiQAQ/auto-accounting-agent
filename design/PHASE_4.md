# Frontend Phase 4 — Sync UI (TBD)

**Scope:** add the user-facing surface for the half-automated CSV sync
pathway built in [`BACKEND_PHASE_4.md`](./BACKEND_PHASE_4.md). The
backend ships the heavy lifting; the frontend exposes:

- A way to **add and configure sync sources** (folder paths, IMAP
  mailboxes, format / column mapping).
- A **manual "Sync now" trigger** for users who want to pull immediately
  rather than wait for the scheduler.
- A **history view** of past sync runs (file → counts → status), with
  drill-down into rows that landed in `/review`.
- Notifications when a scheduled sync brings in new transactions or
  routes some to review.

**Estimated effort:** 1–2 days of frontend work, on top of the backend
ready.

**Prerequisite:** [`BACKEND_PHASE_4.md`](./BACKEND_PHASE_4.md) shipped
with the API contract finalized.

---

## What's intentionally NOT in this doc yet

The detailed UI design — components, layout, copy, exact flows — is
**deferred to implementation time**, when:

- We've actually felt the friction of Phase 1 / 2 / 3 dogfood and know
  what real "everyday sync" looks like.
- The backend's API contract is concrete (CSV formats, error modes,
  source kinds) and the UI can match it without guessing.
- The sidebar Phase-2 placeholders (Review, Accounts, etc.) have
  matured into real screens, so we know how Sync slots in.

This doc records the **scope and integration surfaces only**. Treat it
as a sticky note for "when we get here, here's what to design."

---

## Integration surfaces (consumed from Phase 4 backend)

The UI plumbing must reach these endpoints (full contract in
`BACKEND_PHASE_4.md` §"API contract"):

| Endpoint | UI use |
|---|---|
| `GET /api/sync/sources` | Settings page list view |
| `POST/PATCH/DELETE /api/sync/sources` | Settings page CRUD |
| `POST /api/sync/sources/:id/test` | "Test source" button when adding/editing a source — surfaces what would import without writing |
| `POST /api/sync/run` | TopBar's "Sync now" button + "Run this source" inline action |
| `GET /api/sync/runs` | Sync history view |
| `GET /api/sync/runs/:id` | Drill-down detail when clicking a history row |

---

## Likely UI placements (subject to revision when we design it)

These are sketches for the conversation that happens at implementation
time — not commitments.

### TopBar

A small "Sync" button next to the existing settings icon. Click =
`POST /api/sync/run` against all enabled sources; toast surfaces the
combined result ("Imported 12, 3 to review"). Last-sync timestamp
appears as hover tooltip.

If a sync is running, the icon spins; clicking again is a no-op until
done.

### Settings → Sync Sources (new section)

Below the existing Profile / Import / API Keys / About sections.
A list of registered sources with:
- Source label, kind, format, last run timestamp, status.
- Per-source toggle (enable/disable).
- "Edit" → modal with `kind`-specific config form.
- "Run now" → triggers `POST /api/sync/run` for that source alone.
- "Add source" button → modal with kind picker (folder / imap), then
  format picker (PayPay / Alipay / WeChat / Generic), then config form.
- For Generic format: column-mapping editor (sample rows preview from
  `POST /api/sync/sources/:id/test`).

### History view

A new screen at `/sync/history` (or as a tab inside Settings →
Sync Sources?) listing recent `import_runs` with:
- Date / time, source label, file name.
- Counts: imported / duplicate / review / error.
- Click → detail page showing per-source-run summary; if there are
  review-queue items, link to `/review` filtered to this run.

### Records cross-link

Each Phase 4 transaction has `import_run_id` populated. Records page
adds a small chip/icon on rows that came from sync (vs photo or
manual). Click chip → filter Records to "all from this import run."

### Errors and edge surfaces

- `unknown_csv_format`: surface "We don't recognize this CSV. Pick a
  format or set up Generic mapping" with link to Sources settings.
- `column_mapping_invalid`: highlight the missing-fields list inline in
  the source's edit modal.
- `imap_connection_error`: surface near the source row + "Reconnect"
  button.

---

## Acceptance checklist (will firm up at design time)

- [ ] User can add a folder source from Settings, point it at a
      Downloads-style directory, pick "PayPay" as format, save.
- [ ] Drop a CSV in that folder → within ≤ scheduler tick, the new
      transactions appear in Records.
- [ ] Click "Sync now" in TopBar → manual run completes within seconds,
      toast shows summary.
- [ ] Sync history screen lists past runs with correct counts; drill-
      down shows review-queue items linked into `/review`.
- [ ] Records page shows a small "from sync" indicator on
      sync-imported rows; clicking filters the list to that import run.
- [ ] Error states (unknown format, IMAP fail, mapping invalid) all
      have actionable UI surfaces, not raw error toasts.

---

## Open questions to discuss when we get here

- **TopBar Sync button vs manual-only**: a global Sync button is fast
  but might run sources you didn't intend (e.g. a folder you're
  reorganizing). Per-source "Run now" is safer but slower. Maybe both?
- **History view location**: own screen vs Settings tab vs combined
  with `/review`? Depends on how much volume the history actually has.
- **Notifications**: in-app toasts only, or also browser notifications
  via `Notification.requestPermission()`? Browser notifications are
  great for "scheduled sync brought in 5 new things" but require an
  opt-in flow.
- **Column-mapping UI**: spreadsheet-style table with type pickers, or
  step-by-step wizard? Depends on how often users actually reach for
  Generic format.
- **Mobile**: relevant since CSV exports often start on phone. iCloud
  Drive / Google Drive sync to a watched folder is the implicit
  pattern. Test on iOS Safari before declaring this done.
