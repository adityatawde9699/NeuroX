# Implementation progress

Updated: 2026-09-09. This records implementation evidence against `PLAN.md`;
the existing production plan remains the source of priorities.

## First milestone: Phase 0 build and security foundation

- Public registration accepts only patient and caregiver roles. Regression
  tests reject administrator, healthcare-worker, and invalid role requests and
  verify that rejected requests do not create usable accounts.
- Dashboard test setup loads Vitest-specific DOM matchers and explicitly
  imports lifecycle hooks, fixing the production TypeScript build.
- Android startup and voice-message syntax are corrected; unsupported speech
  constants are replaced or removed. Java and Kotlin target JDK 17 and
  BuildConfig generation is enabled.
- Release networking disallows cleartext HTTP; the debug manifest permits it
  for local emulator development.
- Help requests take precedence when a voice phrase also mentions an activity
  or reminder. JVM regression tests cover that routing.
- The backend location smoke test uses the current capture time so its valid
  update is not rejected as stale merely because the calendar has advanced.
- GitHub Actions configuration covers backend, dashboard, Android, and
  PostgreSQL migration upgrade/rollback. A remote CI run is still required.

## Second milestone: Phase 0 session and environment hardening

- Android has a patient setup/sign-in screen and authentication ViewModel.
  Demo credentials are removed from app source; only the debug variant has a
  default emulator URL. Release requires a user-entered HTTPS server.
- Android sessions use AES-GCM with a non-exportable Android Keystore key.
  Legacy plaintext sessions are removed and require sign-in again. Patient/server
  bindings are retained, and unknown bindings with local records fail closed.
  No queued records are deleted to switch accounts. App backup is disabled.
- Android refresh rotation is serialized across repository/worker instances.
  Revoked sessions return to setup; temporary network/service failures retain
  queued work for retry. Redirects are disabled on authenticated API clients.
- Browser refresh tokens now use an HttpOnly, SameSite=Strict cookie, Secure
  outside development. Access tokens and identity remain in memory. Legacy
  browser storage is removed; reload restores the cookie session. Origin checks
  protect every browser session endpoint, including login and logout.
- Browser requests share one in-flight refresh per tab. Logout waits for an
  in-flight rotation before revoking the cookie; late refresh responses cannot
  restore cleared in-memory sessions. The server atomically claims refresh tokens.
- Authentication routes are extracted from `main.py` into
  `backend/app/routers/authentication.py`; native token routes remain compatible.
- Staging/production require explicit HTTPS dashboard origins, PostgreSQL, and
  a non-placeholder JWT secret. Unknown environments fail startup. Demo seeding
  and automatic table creation occur only in development.
- Android setup, Keystore round-trip, corruption, and refresh instrumentation
  tests replace the old tests that assumed automatic demo sign-in. Full patient
  flow coverage with injected repositories remains to be rebuilt.

## Third milestone: Phase 0 domain boundaries and patient state

- Patient profiles, caregiver assignments, contacts, and reminders now live in
  `backend/app/routers/care.py`. Shared authorization is in `app/access.py` and
  response formatting in `app/presenters.py`.
- Authorization tests cover unassigned caregivers across patient reads and
  contact/reminder/activity/safety mutations. Additional regression tests cover
  multi-patient reminder ownership, revoked assignments, and activity event IDs.
- Reminder sync calls the extracted handler and checks that the reminder belongs
  to the envelope's patient. Rejected retries stay rejected; revoked assignments
  cannot replay a previously accepted event to retrieve its result.
- Activity submission requires a patient role, including direct handler calls
  from sync. Reusing another patient's activity event ID cannot disclose their
  session, and event IDs cannot be reused across different activities.
- `PatientViewModel` owns patient loading, activity actions, reminders, and help
  actions through an injected `PatientRepository`. Compose observes StateFlow;
  `MainActivity.kt` now contains 177 lines of startup/navigation wiring, with
  screens moved to `PatientScreens.kt`.
- ViewModel tests cover offline cache loading, unavailable local storage,
  completion event identity, repeated starts, navigation cancellation, reminder
  queue failures, SOS queue failures, and bounded difficulty updates. Failed local
  persistence reports an error rather than claiming successful offline saving.
- Profile and safety screens use loaded patient data; fixed demo identity,
  safety, location-accuracy, and expected-return labels have been removed.
  New screen instrumentation tests compile but still require a device to run.

## Fourth milestone: remaining Phase 0 implementation

- Backend composition is separated from auth, patients/contacts, reminders,
  activities, reports, safety, notifications (the existing alert feed), and sync
  HTTP bindings and services. Online and offline mutations share services.
- Android now has separate Room and Retrofit data sources, a repository contract,
  manual dependency injection shared by UI/workers, and activity/reminder/help
  use cases. Existing offline and failure-path ViewModel tests pass unchanged.
- Real PostgreSQL testing exposed revision 001 importing evolving model metadata,
  causing revision 002 to add an existing column. The initial schema is frozen;
  exception-swallowing in revision 002 is removed. Upgrade, intermediate rollback,
  patient-data preservation, re-upgrade, and full rollback pass on PostgreSQL 18.6.
- Migration verification refuses nonempty databases, fails on missing configuration,
  avoids printing credentials, and cannot be redirected by DATABASE_URL.
  SQLite regression tests also cover revision history and URL isolation.
- Dependency auditing identified the obsolete JWT library's unpatched ecdsa
  dependency and outdated test/install tooling. Authentication now uses PyJWT
  with an explicit HS256 allowlist and required subject/expiry/type claims.
  The obsolete packages were removed from the local virtual environment.
- CI now includes Ruff, Bandit, Python/npm dependency audits, OSV scanning of the
  resolved Android release Maven graph, and release APK literal/manifest gates.
  Security-gate regression tests prove demo credentials, emulator URLs, JWT
  literals, and cleartext manifests are rejected.

## Current verification

- Backend: 112 tests pass, including authorization, sync, browser sessions,
  migration history, JWT claims, and release security gates.
- Dashboard: 35 tests pass; production build and TypeScript checks pass.
- Android: 13 JVM tests pass; debug/release APKs and instrumentation APK compile.
  Lint has zero errors and 15 warnings.
- PostgreSQL 18.6: upgrade/rollback and existing patient-data preservation pass
  against isolated disposable databases. The temporary server has been stopped.
  PostgreSQL 16 remains configured as the remote CI migration target.
- Ruff and Bandit: no findings. pip-audit and npm audit: no known vulnerabilities.
  OSV: no known vulnerabilities in 102 resolved Android release Maven packages.
- Release APK literal scan passes; merged release manifest disallows cleartext,
  backup, and debugging. This targeted scan is not proof of absence of all secrets.
- Nonblocking warnings: Vite's large bundle, Android SDK/lint warnings, and Python
  dependency deprecations/development-only JWT key-length warnings.

## Phase 0 acceptance status

The remaining Phase 0 code and local verification are implemented. Phase 0 is
**not yet accepted**: PLAN.md explicitly requires passing CI, and this workspace's
changes have not been committed/pushed or verified by a remote CI run. Publishing
the changes and observing all required checks is the remaining Phase 0 gate.

Device/Keystore/UI instrumentation is compiled but not executed because this
environment has no emulator/KVM. Full device workflows and process-death game
recovery remain production-validation work; this update does not claim they are
implemented or tested. The broader pilot/production gates in PLAN.md remain open.
