# REBOOT.md — Dashboards refactor playbook

> **Purpose:** Drop this into a fresh chat alongside the relevant view file(s)
> and you can pick up where the previous chat left off, on whichever dashboard
> is next.

---

## Current state (April 2026)

The dashboards system is being rebuilt around a **BigQuery views layer** that
sits between raw Firestore exports and the Python snapshot scripts. All heavy
lifting (nested field extraction, FX conversion, demo/internal filtering,
status mapping) happens in SQL views. Python scripts become trivial:
SELECT, add snapshot_date, write.

### What's done

- ✅ `dashboard_views` dataset created in `outstaffer-app-prod`
- ✅ `vw_contracts_base` — foundation view, one row per contract with flat
  AUD-converted fees, status mapping, lifecycle stage, `is_internal` flag
- ✅ `vw_unmapped_contract_statuses` — monitoring view for new statuses
- ✅ `vw_revenue_snapshot` — produces revenue metrics in the long format
  expected by `monthly_revenue_metrics`
- ✅ `snapshot_revenue.py` rewritten — ~200 lines, reads from view, ~100
  lines of actual logic
- ✅ Revenue dashboard live and working
- ✅ Lookup tables in place: `contract_status_mapping` (with both `mapped_status`
  and `lifecycle_stage` columns), `internal_companies`

### What's left (in priority order)

| Priority | Job | Status | Source data |
|---|---|---|---|
| 1 | Customer dashboard | broken, contracts-based + companies | `vw_contracts_base` + companies + industries + sizes + users |
| 2 | Geographic dashboard | broken, contracts-based | `vw_contracts_base` only |
| 3 | Requisitions | broken, separate domain | `firestore_exports.requisitions` |
| 4 | Plan & Add-ons | working but old code, low urgency | contracts + plan data |
| 5 | Health Insurance | working but old code, low urgency | contracts + health benefit data |

### Things deferred

- **One-time / pass-through revenue** (placement fees, security deposits,
  local govt tax): needs separate `vw_money_flow_snapshot` view eventually.
  Not blocking any dashboard.
- **Cross-snapshot metrics** (new_subscriptions, churned_subscriptions,
  retention_rate, churn_rate, new_customers_this_month): need previous-month
  comparison logic. Can be added to the Python scripts later, or built into
  views by joining to previous month's row in the snapshot table.
- **Backup table cleanup**: ~43 `*_backup_YYYYMMDD` tables in
  `dashboard_metrics`. Defer until all jobs running cleanly for 1-2 months,
  then drop and add table expiration policy.
- **View deployment automation**: views are currently applied manually via
  BigQuery console. Eventually wire up Cloud Build trigger on the
  `bigquery-views` repo for `CREATE OR REPLACE VIEW` on push.

---

## The pattern (for each dashboard)

For any broken/new dashboard, the workflow is:

### 1. Investigate

- Find the failing snapshot script in `python/`
- Read what metric_types/ids/labels the OLD output produced (dashboard
  frontend depends on these)
- Check the output table schema (`monthly_revenue_metrics`,
  `customer_snapshot`, etc.)
- Look at the dashboard React component to see what fields it queries
- If the dashboard has a screenshot, even better — confirms expected shape

### 2. Decide what's in scope

- Headline numbers (counts, MRR, ARR) — always
- Per-X breakdowns (country, type, etc.) — usually
- Cross-snapshot metrics (deltas, retention, churn) — defer for v1
- One-time/pass-through fees — defer (separate view)

### 3. Draft the view

- Lives in `bigquery-views/dashboard_views/<view_name>.sql`
- Reads from `vw_contracts_base` if contracts-based — never re-extract
  from `firestore_exports.employee_contracts` directly in a snapshot view
- Follows the slice pattern (All / External / Internal) for any metric
  that should be toggle-able in the UI
- Long format output: `metric_type, id, label, count, value_aud, percentage`
- See `bigquery-views/dashboard_views/PATTERN.md` for full conventions

### 4. Validate

- Run the view in BigQuery console
- Compare headline numbers against last known-good snapshot (or current
  dashboard if it's still partially working)
- Check that slices reconcile: `total = external + internal` for each metric
- Spot-check one specific row (e.g. PH active count = N, MRR = $X)

### 5. Rewrite the Python script

- Read the existing failing script with desktop-commander first
- Move it to `<name>_OLD.py` to preserve as backup
- Write the new lean version that:
  - Queries the view via `client.query("SELECT * FROM ...").to_dataframe()`
  - Adds `snapshot_date = datetime.now().date()`
  - Coerces dtypes to match the BigQuery schema (count → Int64,
    value_aud/percentage → float)
  - Calls `write_snapshot_to_bigquery(df, table_id, schema, dry_run=...)`
- Use `snapshot_revenue.py` as a reference template — same shape will
  apply to all of these

### 6. Test locally

```powershell
cd F:\Documents\Steve\Development\outstaffer-platform-reporting\python
python snapshot_<name>.py --dry-run
```

- Inspect the dry-run CSV
- Confirm row counts and headline numbers
- Then run without `--dry-run` to write to BigQuery
- Refresh the dashboard, confirm it works

### 7. Deploy

The Cloud Run job already exists and points at the script. Just rebuild
the container and redeploy. (Or push to main if there's a Cloud Build
trigger — check the repo.)

---

## Key conventions / decisions

These came out of the original refactor. Don't relitigate.

### Naming

- Views: `vw_<name>` lowercase snake_case (e.g. `vw_contracts_base`,
  `vw_revenue_snapshot`)
- Datasets: `dashboard_views` (modeled views), `dashboard_metrics`
  (snapshot output + lookups), `firestore_exports` (raw, untouchable)
- Slices: `<id>` (all), `<id>_external` (excludes internal Outstaffer),
  `<id>_internal` (Outstaffer only). All three emitted for every metric
  that should be toggle-able.

### What MRR includes

- EOR, Device, Hardware, Software, Health, Cross-border (compliance fee)
- Local govt tax is **NOT** MRR (pass-through to authorities)
- Placement fees are **NOT** MRR (one-time event, separate view later)
- Security deposits are **NOT** revenue at all (held in escrow)

### Status mapping

`dashboard_metrics.contract_status_mapping` has two columns:
- `mapped_status` — binary `Active` / `Inactive`
- `lifecycle_stage` — fine-grained `Active` / `Offboarding` / `Not Started` / `Inactive`

Use `mapped_status = 'Active'` for revenue calcs (anyone in the funnel
or working). Use `lifecycle_stage` for breakdowns where you need to
distinguish offboarding from active or pre-onboarded.

### Internal company filter

`dashboard_metrics.internal_companies` lists Outstaffer's own entities
(4 of them as of writing). `vw_contracts_base` flags `is_internal = TRUE`
for any contract belonging to those companies. Snapshot views emit
metrics for All / External / Internal slices so the UI can toggle.

### FX

Pulled from `firestore_exports.currency_pairs` — one row per pair, holds
**current** rate. No month-by-month history. Snapshots freeze the AUD
value at point-in-time when they run, which matches how billing works.

### Data quality

`vw_unmapped_contract_statuses` surfaces any new statuses that need
adding to the mapping. Snapshot scripts should query this view at the
start and log a warning if rows > 0 (don't fail — just shout).

---

## Reference files

When working on a new dashboard, useful files to drop into the chat:

**Always:**
- `REBOOT.md` (this file)
- `bigquery-views/dashboard_views/PATTERN.md` (view conventions)
- `bigquery-views/dashboard_views/vw_contracts_base.sql` (foundation)
- `python/snapshot_revenue.py` (reference for new Python scripts)
- `python/snapshot_utils.py` (write_snapshot_to_bigquery helper)

**Specific to the dashboard you're working on:**
- The current broken Python script (e.g. `python/snapshot_customers.py`)
- The output table schema if known
- A screenshot of the dashboard if you have one
- The relevant React component (`src/components/<X>Dashboard.jsx`)

---

## Quick reference: file/dataset locations

```
BigQuery (outstaffer-app-prod):
  firestore_exports.*                   — raw, never modified
  dashboard_views.vw_*                   — modeled views (the new layer)
  dashboard_metrics.*                    — snapshot output tables + lookups
    .contract_status_mapping             — Active/Inactive + lifecycle_stage
    .internal_companies                  — Outstaffer's own entities
    .monthly_revenue_metrics             — revenue snapshot output
    .customer_snapshot                   — customer dashboard output
    .geographic_metrics                  — geo dashboard output
    .health_insurance_metrics            — health dashboard output
    .monthly_addon_snapshot              — add-ons output
    .requisition_snapshots               — requisitions output

Local repos:
  outstaffer-platform-reporting/
    python/snapshot_*.py                 — Python snapshot scripts
    backend/routers/*.py                 — FastAPI dashboard endpoints
    src/components/*Dashboard.jsx        — React dashboard components

  bigquery-views/
    dashboard_views/                     — view DDL (source of truth)
      PATTERN.md
      vw_contracts_base.sql
      vw_revenue_snapshot.sql
      vw_unmapped_contract_statuses.sql

GCP:
  Project outstaffer-app-prod              — BigQuery + Firestore
  Project dashboards-ccc88                 — Cloud Run jobs + Scheduler
```

---

## Working with Sonnet on this

The architecture and conventions are settled. Sonnet is a fine choice
for this work — it's pattern application, not architecture design. If you
hit a genuine architectural question (e.g. "should this be one view or
two", "where does this fee actually live in the calc tree"), that might
be worth bumping back to Opus.

When opening a fresh chat:

1. Drop in REBOOT.md, PATTERN.md, vw_contracts_base.sql,
   snapshot_revenue.py
2. Drop in the broken script for whichever dashboard you're tackling
3. Drop in any screenshots / output table schemas you have
4. Say something like: *"Picking up the customer dashboard next.
   Following the pattern in REBOOT.md. Let's start by investigating
   what the current broken snapshot_customers.py expects to produce
   and the customer_snapshot table schema."*

That's enough to get going.
