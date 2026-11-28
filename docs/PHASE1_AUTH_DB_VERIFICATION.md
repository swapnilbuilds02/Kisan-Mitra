# Phase 1 authentication and database verification

Stage 2A source work began by explicit owner authorization while these Phase 1 gates remain open. The latest local backend suite returned **138 passed, 9 skipped, 0 failed** on 2026-11-27; the ninth skip is the guarded plot migration test. No PostgreSQL migration or RLS verification has succeeded in this managed environment. See [Stage 2A](STAGE2A_PLOTS_WEATHER.md) for the plot-specific test and the current API trust boundary. Earlier counts below are historical snapshots.

## Stage 1F current status (supersedes older snapshots below)

**133 Python tests passed, 8 guarded PostgreSQL tests skipped, 0 failed** on 2026-11-27. The backend now returns opaque challenge IDs for Farmer/partner registration and password recovery, and `/api/v1/auth/session` returns only the authenticated identity's role/state, including eligible pending partners. Unknown and eligible numbers receive the same response shape at request time. Admin partner decisions require a current-session, five-minute RS256 reauthentication proof created only after password verification. The proof cannot be used as an access token. Migration `0008` now has private, persistent Admin mobile/IP counters: three password attempts per 15 minutes and two Admin OTP requests per hour. These SQL limits have **not run on PostgreSQL**; the guarded Admin test is prepared to check the password limit.

The Expo source uses `expo-secure-store` for refresh credentials and in-memory access tokens, with one refresh promise per app process, timeout/error handling, and pending-partner routing. Registration fails closed if an approved consent document ID, version, and HTTPS URL are absent. The Next.js source proxies auth through server route handlers, uses `HttpOnly`/`SameSite=Strict` cookies (`Secure` in production), and checks origin plus CSRF token on mutations. The Admin queue, detail, history, and decision controls use protected backend endpoints. Sensitive decisions require a fresh password proof. Neither frontend has been type-checked, built, rendered, or device-tested: `npm ping` failed with `EACCES`, and neither package has `node_modules` (`tsc`/`next` commands not found).

**Remaining security limits:** No approved live OTP sender or consent wording, no PostgreSQL migration/RLS/concurrency run, no browser/device check, and no cross-instance coordination for web refresh rotation. The web refresh coordinator only covers concurrent requests within one server process; a shared coordination mechanism or serialized browser flow must be verified before multi-instance deployment. Client role routing remains a convenience; server-side authorization is the enforcement boundary. Rejected/suspended partner status details are not exposed under the existing backend policy. Admin password-only and SMS OTP-only login retain credential-theft and SIM-swap risks; optional stronger factors remain recommended. No live provider or deployment was activated.

Git remains blocked in this managed workspace: `.git/index.lock` creation is denied, and `git ls-remote origin HEAD` cannot connect to GitHub port 443. No Stage 1F commit or push has occurred. After Git write and HTTPS access are restored, review the full staged diff and remote divergence, preserve unrelated branding changes, verify the configured author email, and commit/push without force.

## Stage 1E current status (supersedes older counts below)

The Stage 1E local suite returned **129 passed, 8 skipped, 0 failed** on 2026-11-27. The eighth skip is `test_postgres_admin_integration.py`. Migration `0008_admin_identity.up.sql` and the guarded Admin test are prepared but have **not** run on PostgreSQL. Phase 1 remains in progress. Earlier Stage 1D counts below are historical snapshots.

Migration `0008` adds private provisioning and one-time onboarding authorization tables with RLS and no runtime table grants. `km_private.prepare_admin` is intentionally **not granted** to `km_api`; only a migration-owner operator can prepare an inactive, unverified identity. Initial Owner preparation is allowed only when no `super_admin` exists. Later Admin preparation requires an active provisioned Owner ID, but the operator must independently verify that Owner's instruction: the supplied `--operator-id` is audit metadata, not cryptographic approval proof. Provisioning never sets a password or issues a session.

The Admin activation route requests an identity-bound `ACCOUNT_CLAIM` OTP, verifies it once, then issues a 10-minute digest-backed authorization. Completion creates an existing-format scrypt credential and activates the prepared identity atomically. The shared password and bound `LOGIN` OTP routes require active provisioning; Admin reset and authenticated password change reuse the existing credential infrastructure and revoke sessions. Protected Admin requests recheck provisioning. No public Admin registration, actual Owner account, live sender, or website UI was enabled.

| Stage 1E scenario | Executed evidence | Remaining verification |
| --- | --- | --- |
| Prepared identity, OTP activation, single-use token, no public registration | `test_admin_auth.py` local API tests pass | Actual migration, operator privileges, concurrent activation |
| Password/OTP login, OTP replay, cross-role denial | `test_admin_auth.py` local API tests pass | Database lock and rate-limit behavior, sender integration |
| Password reset/change and old-session rejection | `test_admin_auth.py` local API tests pass | Transactional persistence and restart behavior |
| Admin RLS, role grants, unique identity, audit persistence | `test_postgres_admin_integration.py` prepared | **Skipped locally**; inspect result on disposable PostgreSQL |
| Existing Farmer and partner regressions | Full Python suite passes | PostgreSQL, frontend, and end-to-end checks |

For a fresh, marked **disposable** database named `km_test_*` on a dedicated local cluster, set `KM_ALLOW_DISPOSABLE_DB_TESTS=YES` and `KM_TEST_DATABASE_URL` per the setup below. Run `python -m pytest backend/tests/test_postgres_identity_integration.py backend/tests/test_postgres_auth_integration.py backend/tests/test_postgres_farmer_integration.py backend/tests/test_postgres_password_integration.py backend/tests/test_postgres_recovery_integration.py backend/tests/test_postgres_onboarding_integration.py backend/tests/test_postgres_partner_integration.py backend/tests/test_postgres_admin_integration.py -q`. Expect eight passed and zero skipped only after successful execution. The Admin test runs last and leaves its schema for inspection. Verify the database marker and delete **only that disposable database** afterward. The `0008` migration has no production down script; a reviewed snapshot restore or disposable database recreation is the safe rollback approach. No production rollback has been rehearsed.

Admin password-only and SMS OTP-only access remain exposed to credential theft, SIM swaps, and mobile account recovery attacks. Optional stronger factors, independent recovery review, shorter Admin session limits, and alerting are recommended before live delivery. Recent-authentication proof for sensitive Admin decisions is a pending security control; applying it to existing decision routes needs a reviewed timeout and UX contract. Current password login limits are five attempts per mobile and IP per 15 minutes; stricter Admin-specific limits remain pending. PostgreSQL concurrency, real RLS, audit retention, and OTP sender failure behavior are still unverified.

Git synchronization is also blocked in this workspace: `git add` cannot create `.git/index.lock` because `.git` is read-only under the managed filesystem policy. `git ls-remote origin HEAD` cannot connect to `github.com:443`. No Stage 1E commit or push has occurred. The configured author matches the latest local commit (`Swapnil <jeeswapnil002@gmail.com>`), but GitHub account association cannot be checked while GitHub is unreachable. Preserve the current worktree; once authorized filesystem write access and HTTPS connectivity are restored, inspect the full staged diff and remote divergence, then commit and push without force.

**Status, 2026-11-27:** RS256, Farmer onboarding, recovery, and Stage 1D partner application API tests run locally; seven PostgreSQL integration tests skip because the driver/server are unavailable. Frontend builds have not run. Phase 1 is still in progress.

**Stage 1D update:** Migration `0007_partner_applications` adds Shop/Consultant applications, role-bound registration OTPs, partner consents, decision history, status gates, and transactional session revocation on decisions. Registration and Admin review routes are implemented. Pending sessions can reach only own application/profile and credential routes; approved partners can reach the partner overview. Local suite: **121 passed, 7 skipped, 0 failed**. PostgreSQL migration, RLS, locking, and restricted-role behavior are unverified.

| Stage 1D security scenario | Executed evidence | Remaining verification |
| --- | --- | --- |
| Shop/Consultant registration, pending scope, Admin approval, approved password login | `test_partner_applications.py` parameterized API tests pass | Atomic persistence and restricted SQL role on PostgreSQL |
| Partner OTP login, suspension, revoked access/refresh, reactivation | `test_partner_applications.py` parameterized API tests pass | Concurrent suspension/login and live adapter behavior on PostgreSQL |
| Farmer OTP, password, profile and RS256 regressions | Existing Python suite passes | End-to-end device and PostgreSQL verification |
| OTP cross-role binding, duplicate application, decision conflict, RLS table denial | `test_postgres_partner_integration.py` prepared | **Skipped; not executed locally** |
| Partner password recovery/change, refresh/logout | `test_partner_applications.py` parameterized API tests pass | PostgreSQL transaction and adapter execution |
| Rejection denial | `test_partner_applications.py` parameterized API tests pass | PostgreSQL state and revocation verification |
| Decision history, cross-partner reads, concurrent decisions | Guarded concurrent decision test prepared; isolated route tests are partial | Run focused PostgreSQL and API scenarios before production |

**Stage 1C update:** Migration `0006_farmer_onboarding` adds profile completion metadata, a private digest-only onboarding authorization, consent documents, and Farmer consent records. Routes cover request/verify/complete, OTP-only password enrollment, own profile read/update, and onboarding status. The backend enforces approved consent documents, single-use authorization, and Farmer-only profile access. Local API tests use isolated adapters; the guarded PostgreSQL transaction test is prepared but unexecuted. No approved production consent document or live OTP sender is configured.

**Stage 1B update:** Migration `0005_otp_recovery` adds purpose and identity binding to the existing OTP challenge table, invalidates unlabelled outstanding challenges, and adds digest-only reset authorizations. New endpoints: `POST /api/v1/auth/password/forgot`, `/reset/verify`, `/reset`, and authenticated `/change`. Recovery is restricted to verified active Farmers with existing credentials; partner/Admin recovery fails closed. A successful reset or change revokes sessions transactionally. Local suite: **111 passed, 5 skipped, 0 failed**. Database execution, atomicity, and permissions remain unverified.

**Stage 1A update:** Shared scrypt password handling, private one-to-one credential storage migration `0004_password_credentials`, an internal credential repository, and `POST /api/v1/auth/password/login` are implemented. The endpoint issues an existing RS256/session pair only to verified, active Farmer identities with an internally provisioned credential. Other roles fail closed pending approval/provisioning gates. There is no public password-setting route. Local suite: **107 passed, 4 PostgreSQL tests skipped, 0 failed**. The new guarded database test has not executed; neither migration `0004` nor its grants/RLS have been verified on PostgreSQL.

## Existing architecture and decisions

- One FastAPI authentication path is used. `backend/app/auth.py` extends the existing `main.py` and `identity.py` path; it does not create a second login system.
- Access tokens are RS256 JWTs signed by an environment-loaded RSA private key of at least 2048 bits, valid for 15 minutes. Verification uses a `kid`-indexed public-key ring and rejects unknown IDs and every non-RS256 algorithm. Issuer is `https://api.kisanmitra.in`; audience is `kisan-mitra-clients`. Tokens contain subject, session ID, token ID, type, issued/not-before time, and expiration. Roles/tier are read from PostgreSQL on each request, not trusted from token claims. Missing or invalid key configuration fails closed. Old HS256 tokens cannot be used after this change.
- OTP verification is a provider interface. No live SMS provider is connected. A verified code calls `km_private.claim_farmer` to claim an admin-prepared pending farmer or create one canonical farmer identity. The restricted `POST /api/v1/admin/farmers/pre-register` path prepares an unverified account with an audit reason. Shop, Consultant, and Admin OTP issuance stays closed while `DEC-003` is unresolved. Farmer profile completion and approved SMS delivery remain pending.
- Refresh tokens are 256-bit random values with a session ID prefix. Only a SHA-256 digest of the random value is stored. `0002_auth_state` defines PostgreSQL tables and row-locking functions for atomic rotation, consumed-hash history, replay-triggered user-wide revocation, expiry, and logout. `PostgresSessionStore` uses them when `DATABASE_URL` is configured. These paths are code-complete but **not database-verified** here. Test fakes are injected only in tests. Expired-row cleanup and retention policy remain pending.
- `PostgresOtpProvider` generates six-digit codes, HMACs the mobile/IP/code with a separate pepper, and calls database functions for 120-second expiry, five verification attempts, 60-second resend cooldown, and three requests per hour per mobile/IP. Challenge consumption uses row locking, while request limits use advisory transaction locks. The public request response is generic; invalid, absent, inactive, and non-farmer verification paths return the same `INVALID_OTP` response. Audit events contain event type and keyed hashes, not codes or tokens. No sender is configured by default, and database behavior is not yet verified.
- RS256 issuance and public-key overlap for rotation are unit-tested with temporary in-memory keys. Operational key provisioning, public-key publication, rotation timing, and revocation remain unverified. No private key is committed. The issuer change and old-token invalidation are compatibility changes that must be coordinated before deployment.
- `0001` creates `users`, `farmer_profiles`, `partner_profiles`, and `audit_logs`; `0002` adds session, consumed-refresh, OTP challenge/request, and security-event tables; `0003` adds admin preparation and OTP claim functions. RLS is enabled on tables with no direct runtime grants. Narrow `SECURITY DEFINER` functions expose transitions to `km_api`; the API database credential must never be distributed to clients. No per-farmer data policy has been added because no farmer data route exists.
- The [owner-approved role authentication policy](PHASE1_AUTH_POLICY_PROPOSAL.md) is documented. Only the Stage 1A farmer password path and pre-existing farmer OTP path are active; other roles await approval/provisioning implementation. PostgreSQL auth state differs from the older Redis session diagram; confirm that architecture before deployment.

## Reproducible PostgreSQL check

1. Start an isolated **local PostgreSQL server**. Create an empty database whose name starts with `km_test_`, using a migration account with `CREATEROLE`. Ensure it has no existing `km_api` role and no other non-template database besides `postgres`. Mark the test database as disposable before running migrations.
2. Install `backend/requirements-dev.txt` into a local virtual environment.
3. Set `KM_TEST_DATABASE_URL` to a connection string for that local test database, for example `postgresql://migration_user:password@localhost:5432/km_test_identity`, and set `KM_ALLOW_DISPOSABLE_DB_TESTS=YES`. Do not point it at a shared or production database.
4. Run `python -m pytest backend/tests/test_postgres_identity_integration.py backend/tests/test_postgres_auth_integration.py backend/tests/test_postgres_farmer_integration.py backend/tests/test_postgres_password_integration.py backend/tests/test_postgres_recovery_integration.py backend/tests/test_postgres_onboarding_integration.py backend/tests/test_postgres_partner_integration.py -q` from the repository root.

All seven integration tests require explicit opt-in, a local `km_test_*` database with the exact `KISAN_MITRA_DISPOSABLE_TEST_ONLY` comment, no other non-template database except `postgres`, and no existing `km_api` role. Each applies and rolls back migrations and checks restricted-role access. The identity test checks four tables, indexes, constraints, and RLS under `SET ROLE km_api`. The auth-state test checks persistent sessions, concurrent refresh/replay, logout, OTP cooldown, hourly limits, attempt limit, expiry, and audit event shape. The farmer test checks admin preparation, concurrent claims, unique identities, audit history, role collision, and RLS denial. The password test checks credential mutation and restricted-role denial. The recovery test checks purpose isolation, single-use authorization, reset, and session revocation. The onboarding test checks a development consent version, single-use registration, profile and credential uniqueness, and table access denial. The partner test checks OTP role binding, duplicate registration denial, approval conflict, and direct table access denial. They do **not** prove future per-user allow policies because those policies and CRUD routes do not exist yet.

No PostgreSQL server, `psql`, Docker/Podman, WSL, or `psycopg` package was available on this machine, and localhost:5432 was closed. All seven integration tests were skipped, not passed. Schema validity, role behavior, RLS, apply/rollback, durable session behavior, OTP limits, Farmer claiming, password storage, reset atomicity, onboarding persistence, and partner approval remain unverified in a real database. The existing GitHub Actions workflow has a PostgreSQL service job and web/mobile check jobs, but those jobs have not run from this working tree.

## Frontend verification and open gates

- `web/package.json` and `mobile/package.json` are the existing manifests. Online `npm install` failed while fetching `@types/node` for web and `@types/react` for mobile because registry HTTPS could not connect (`curl` exit 7; npm `EACCES`). DNS resolution works; TLS verification was not disabled. No `node_modules` or lockfile exists. Type checks and the Next build could not start; neither frontend is build-verified.
- The Expo config references local `icon.png`, `splash.png`, and `adaptive-foreground.png`; all resolve to 1024×1024 images. Launcher packaging and device rendering remain unverified.
- The mobile manifest now pairs Expo SDK 58 with React Native 0.88 and React 19.3.0, matching the [Expo SDK 58 version table](https://docs.expo.dev/versions/v58.0.0/). Node 24 exceeds Expo's documented minimum and [Next's minimum](https://nextjs.org/docs/app/getting-started/installation). Dependency resolution and runtime compatibility remain unverified until install/build jobs run.
- No lint script exists in either frontend manifest. Adding a lint tool and lockfiles remains pending after package installation is possible.
- Before Phase 1 can close: run all seven PostgreSQL integration tests; verify production-safe migration and operational key management; configure and test an approved SMS sender; approve consent wording; implement Admin authentication/provisioning and role shells; install frontend dependencies and run type/build/device checks; run CI. Verify proxy handling for peer-IP rate limits, OTP sender failures, cleanup/retention jobs, and audit access control.

## Owner setup on an isolated Windows development machine

1. Download the Windows installer from the [official PostgreSQL Windows download page](https://www.postgresql.org/download/windows/). Install a **dedicated, disposable PostgreSQL 16 instance** with its own data directory and a separate port such as `55432`; set a disposable administrator password and confirm the service starts. Use a fresh cluster with no real project data. The tests create and drop a cluster-wide `km_api` role, so a shared server is unsuitable.
2. From PowerShell in this repository, install the Python driver and test dependencies:

   ```powershell
   Set-Location 'D:\Kisan Mitra APP'
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
   ```

3. Create the empty test database on that **dedicated** instance. Use the port and path chosen during installation:

   ```powershell
   & 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -p 55432 -U postgres -d postgres -c 'CREATE DATABASE km_test_phase1;'
   & 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -p 55432 -U postgres -d postgres -c "COMMENT ON DATABASE km_test_phase1 IS 'KISAN_MITRA_DISPOSABLE_TEST_ONLY';"
   $env:KM_ALLOW_DISPOSABLE_DB_TESTS = 'YES'
   $env:KM_TEST_DATABASE_URL = 'postgresql://postgres:<URL_ENCODED_DISPOSABLE_PASSWORD>@localhost:55432/km_test_phase1'
   .\.venv\Scripts\python.exe -m pytest backend\tests\test_postgres_identity_integration.py backend\tests\test_postgres_auth_integration.py backend\tests\test_postgres_farmer_integration.py backend\tests\test_postgres_password_integration.py backend\tests\test_postgres_recovery_integration.py backend\tests\test_postgres_onboarding_integration.py backend\tests\test_postgres_partner_integration.py -q
   ```

   The placeholder is a disposable test password, not a production credential. URL-encode special characters. Expect **seven passed, zero skipped** from this targeted integration command. The tests refuse a nonlocal host, missing marker, another non-template database, pre-existing identity tables, or an existing `km_api` role. If a test fails, inspect the isolated instance before retrying; do not point it at another database to force a pass.

4. When HTTPS access to the npm registry is restored, run:

   ```powershell
   Set-Location 'D:\Kisan Mitra APP\web'
   npm.cmd install
   npm.cmd run typecheck
   npm.cmd run build
   Set-Location 'D:\Kisan Mitra APP\mobile'
   npm.cmd install
   npm.cmd run typecheck
   npx.cmd expo config --type public
   ```

The existing GitHub Actions workflow also defines isolated PostgreSQL, web, and mobile check jobs. It does not deploy. These jobs are **prepared but have not run** from the current working tree. A successful CI result would be additional evidence; it must be inspected before marking Phase 1 complete.

### Connectivity, cleanup, and CI

If npm installation fails, diagnose connectivity without changing TLS settings:

```powershell
npm.cmd config get registry
Resolve-DnsName registry.npmjs.org
Test-NetConnection registry.npmjs.org -Port 443
curl.exe -I --max-time 10 https://registry.npmjs.org/@types%2fnode
```

The current machine resolves DNS but cannot establish HTTPS to port 443. If these checks still fail, the owner or network administrator must restore permitted registry access or provide an approved package cache. Do not use `strict-ssl=false`, an HTTP registry, or an unreviewed proxy. After installation, the expected web result is a passing type check and Next production build; the expected mobile result is a passing type check and Expo configuration output. Native device packaging remains a separate gate. Neither frontend currently has a lint script.

The targeted PostgreSQL tests roll back their own schema changes. After reviewing their result, clean up **only the named disposable database on the dedicated test instance**:

```powershell
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -p 55432 -U postgres -d km_test_phase1 -Atc "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=current_database();"
# Continue only if the output is exactly KISAN_MITRA_DISPOSABLE_TEST_ONLY.
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -p 55432 -U postgres -d postgres -c 'DROP DATABASE km_test_phase1;'
Remove-Item Env:KM_TEST_DATABASE_URL, Env:KM_ALLOW_DISPOSABLE_DB_TESTS -ErrorAction SilentlyContinue
```

The source-only GitHub Actions workflow has four jobs: Python unit tests, PostgreSQL integration, web checks, and mobile checks. To execute it, push the reviewed branch to the repository and use **Actions → Backend foundation → Run workflow** on that branch, or run `gh workflow run backend-foundation.yml --ref <branch>` where GitHub CLI is configured. Inspect the PostgreSQL job for **seven passed and zero skipped**; the ordinary Python job may skip DB tests because it has no test database. CI does not deploy. The current workspace cannot report a CI result until the branch is pushed and a run is inspected.

## Phase 1 acceptance checklist (current evidence)

| Gate | Current status | Required next evidence |
| --- | --- | --- |
| RS256 issue/verify, issuer/audience, key IDs, algorithm denial | **Implemented and locally tested** | Production key provisioning, public-key distribution, rotation rehearsal |
| Farmer OTP claim and admin pre-registration | **API tested; database unverified** | Run `0003` integration test and inspect audit/uniqueness under concurrency |
| Durable sessions and OTP limits | **Code written; database unverified** | Run `0002` integration test against restricted role and restart/replay scenario |
| OTP purposes and password recovery | **Local API tested; database unverified** | Run `0005` guarded integration test, then exercise concurrent OTP and reset attempts against restricted database role |
| Identity schema, constraints, RLS | **Code written; database unverified** | Run `0001` integration test and inspect restricted-role results |
| Shop/Consultant sign-in and approval | **Local API tests pass; database unverified** | Run `0007` guarded test; verify pending scope, approval, suspension, recovery, and concurrency against PostgreSQL |
| Owner/Admin sign-in | **Pending Stage 1E** | Restricted provisioning and approved password/OTP paths |
| Farmer profile onboarding and consent | **Backend source and local API tested; database unverified** | Run `0006` guarded test and approve production consent wording; mobile UI pending |
| Web/mobile builds and auth client | **Blocked/pending** | npm install, type checks, Next build, Expo config/device checks, client integration |
| CI | **Jobs prepared; not run** | Review successful GitHub Actions run with no skipped DB tests |

Local verification on 2026-11-27: `python -m pytest backend/tests -q` returned **121 passed, 7 skipped, 0 failed**; `python -m compileall -q backend` and `git diff --check` passed. Guard unit tests run without PostgreSQL and do not replace database integration evidence.

**Estimate:** Phase 1 is roughly **86%** through source implementation and local checks, but the required database, frontend, operational key, Admin, consent, and live-delivery gates remain open. Overall project completion is roughly **22%** by planned phase scope; Phases 2–7 have not begun. These are planning estimates, not acceptance results.
