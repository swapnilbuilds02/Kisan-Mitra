# Stage 2A: Farmer plots and weather context

**Status:** Source implemented on 2026-11-27; PostgreSQL migration, RLS, mobile type check, and device behavior remain unverified. Phase 1 verification gates stay open. This stage follows the owner's newer direction that **every eligible active Farmer** may manage plots; it supersedes the older roadmap's Pro-only plot gate for this feature. Subscription rules remain an owner decision.

## Farmer workflow and API

An authenticated, active Farmer may create multiple independent plots, list or retrieve only their own plots, edit fields, select one active plot, and archive a plot. The first created plot is selected. Archiving the selected plot selects another active plot if one exists. Archived plots remain visible for history and cannot be edited, selected, or used for weather context. No permanent-delete endpoint exists.

| Method and route | Result |
| --- | --- |
| `POST /api/v1/farmer/plots` | Create a plot; returns its record (201). |
| `GET /api/v1/farmer/plots` | List own active and archived plots. |
| `GET /api/v1/farmer/plots/{plot_id}` | Retrieve one own plot; unrelated IDs return 404. |
| `PATCH /api/v1/farmer/plots/{plot_id}` | Validate a merged update; ownership/status fields cannot be supplied. |
| `POST /api/v1/farmer/plots/{plot_id}/select` | Select an active own plot. |
| `POST /api/v1/farmer/plots/{plot_id}/archive` | Archive an active own plot and clear its precise coordinates. |
| `GET /api/v1/farmer/plots/{plot_id}/weather/context` | Return plot-scoped weather context or an explicit unavailable state. |

The backend reads Farmer identity from the existing RS256 token, active session, and server-side role record. Shop, Consultant, pending partner, suspended Farmer, and unauthenticated requests cannot enter these routes. Partner relationship access remains **denied**; no relationship engine or temporary partner grant was added. The mobile UI uses the existing auth client and Farmer role view; it does not expose plots in partner views.

## Data and migration

Migration `0009_farmer_plots.up.sql` adds `public.farmer_plots` linked by FK to `users.id`. Each plot has an independent UUID, crop code (initial `grape`), optional grape variety, area/unit, village/taluka/district/state, optional consented coordinates, pruning date, stage code, language (`mr`/`en`), active/archive status, selected flag, and timestamps. Marathi or English names and variety labels are accepted; crop/stage codes remain language-neutral for localized display. Check constraints cover positive area, units, coordinate bounds/pairing with permission timestamp, language, status, and archive selection. A partial unique index permits at most one selected active plot per Farmer. Creation, selection, and archive lock the Farmer identity row to serialize concurrent changes; audit events are written in the same database transaction.

The table has RLS enabled with no direct `km_api` table grant. Narrow migration-owned functions take the Farmer subject supplied by the authenticated server. **This is an API trust boundary:** the runtime database role can call its granted functions with a subject argument, so theft of that database credential would bypass API ownership. Do not expose that credential to clients. A stronger database-bound identity proof is a future hardening decision; do not describe the current design as end-to-end RLS isolation.

`0009_farmer_plots.down.sql` is for a marked disposable database only; it removes all plot rows. Production rollback requires a reviewed backup/forward-migration plan, not this data-dropping script.

## Location permission and weather

Precise coordinates are optional. The API requires a paired latitude/longitude and explicit Farmer permission; omitting them uses district/state context. Revoking permission through an update requires clearing both coordinates. Archival clears coordinates. No GPS permission is requested automatically by the mobile app.

`WeatherContextService` accepts an injected provider protocol. No live provider is configured, so the API returns `status: unavailable` without fabricated measurements. An isolated provider can return source, observation time, expiry, temperature, rainfall, and summary. The in-process cache key includes Farmer, plot, and location; fresh values are reused until expiry. On provider failure, a value expired by at most six hours is labeled `stale`; older values are withheld. A production provider needs owner approval, units/source validation, durable or distributed cache, retention, and failure/precision policy before activation.

## Verification and remaining work

`python -m pytest backend/tests -q` returned **138 passed, 9 skipped, 0 failed**. The new API tests cover two plots, selection/archive fallback, own/cross-Farmer access, role/state denial, forbidden update fields, coordinate permission, weather scope, stale fallback, and unavailable state. The ninth guarded test, `backend/tests/test_postgres_plot_integration.py`, is prepared for a dedicated marked disposable PostgreSQL database and has **not executed**. It checks migration application, constraints, unique selection under concurrency, SQL ownership functions, direct-table denial under `km_api`, and disposable rollback.

Run PostgreSQL integration in the documented disposable environment after migrations 0001-0008 are validated. The CI command now appends the plot test **after** the Admin test, which leaves migrations 0001-0008 in place. A standalone plot test can apply 0001-0008 itself to a fresh marked disposable database. Never run the down script against real Farmer data.

Mobile dependencies are still unavailable in this managed workspace, so type checking, native build, and device accessibility checks are pending. No weather API, Gemini, SMS, or deployment was activated. Next: verify the guarded migration and mobile build; then approve a weather-provider/data-consent contract before implementing a live adapter.

Git staging remains blocked: `git add -N` could not create `.git/index.lock` (`Permission denied`). The branch is `main`, and the configured `origin` is the authorized Kisan-Mitra repository. No Stage 2A commit or push occurred. Preserve all existing uncommitted branding work when Git write and GitHub connectivity are restored.
