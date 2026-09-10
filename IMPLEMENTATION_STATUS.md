# Implementation progress

Updated: 2026-09-10. This records implementation evidence against `PLAN.md`;
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

- Backend: 146 tests pass, including Phase 1 privacy checks and Phase 2 API
  versioning, readiness, error-envelope, request-ID, and pagination checks.
- Dashboard: 44 tests pass; production build and TypeScript checks pass.
- Android: 19 JVM tests pass; debug/release APKs and instrumentation APK compile.
  Lint has no errors; it reports dependency/target-SDK update warnings.
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

## Phase 1 implementation status

- Patients can independently enable or stop location sharing. New location
  submissions are rejected unless the signed-in patient has explicitly enabled
  sharing; caregivers cannot submit a patient's location on their behalf.
- Patients can record or withdraw versioned consent for location, voice
  recording, caregiver access, notifications, and personalization. Consent,
  location changes, caregiver revocation, export access, and deletion requests
  create minimal audit events without copying sensitive data into audit metadata.
- Patients can immediately revoke an active caregiver assignment; every
  subsequent protected read or mutation by that caregiver is denied. The patient
  web safety screen exposes location sharing, caregiver revocation, data export,
  and deletion-request controls. Android Profile now also exposes location sharing
  and caregiver revocation with observable ViewModel state.
- Data export is available as a browser-downloaded JSON record. Deletion requests
  are deliberately recorded for review rather than automatically erasing data:
  retention, legal review, and approved operational handling are still required.
- Review-group formation, field research in NER communities, formal legal review,
  approved retention/deletion policy, incident-response ownership, and an approved
  pilot protocol require real people and external approval. They are not claimed
  complete by this implementation.

## Phase 2 implementation status

- A stable `/api/v1` surface now covers native authentication and application
  resources. Legacy routes remain available during client migration. Browser
  session endpoints deliberately stay under `/auth/browser/*` so the refresh
  cookie retains its narrow path scope.
- Android and dashboard resource clients use `/api/v1`. Browser sign-in,
  registration, refresh, and logout continue to use the cookie-scoped endpoints.
- Every response carries a validated or generated `X-Request-ID`. HTTP and
  validation failures expose a consistent error object while retaining the
  existing `detail` field for backward compatibility; unexpected failures do
  not expose internal exception details.
- Liveness and database-readiness probes are available at `/health` and `/ready`.
  Activity history, reminders, and location history have bounded `limit` and
  `offset` query parameters.
- OpenAPI contract tests protect the core versioned paths and operation-ID
  uniqueness. Backend, dashboard, and Android local verification all pass after
  the client migration.
- Password sign-in now persists failed-attempt counts and applies a timed account
  lock after five failures. Successful authentication after the lock expires
  clears the failure state, and lock responses include `Retry-After`.
- Refresh sessions are grouped into rotation families. Reusing a consumed token
  revokes every active replacement in that family and records a content-minimal
  audit event. Password changes revoke all of the account's refresh sessions.
- Account owners can list and revoke their active sessions through `/api/v1`.
  The caregiver Settings screen exposes those controls and does not rely on
  frontend visibility for authorization.
- Email verification and password reset use cryptographically random, expiring,
  single-use tokens; only token digests are stored. Reset requests return the
  same response for known and unknown emails, successful resets clear lockouts
  and revoke existing sessions, and both workflows create minimal audit events.
- SMTP delivery is isolated behind a server-only adapter. Staging and production
  require SMTP sender configuration and an exact HTTPS public web origin, and
  enforce email verification. The dashboard implements forgot-password, reset,
  and verification-link screens.
- Phone verification uses six-digit, ten-minute, one-use codes whose HMAC digests
  are stored instead of the raw code. A provider-neutral HTTPS SMS adapter keeps
  provider credentials server-side. Sessions retain bounded client labels so the
  dashboard can show and revoke recognizable Android/web sessions.
- Authentication and recovery endpoints have distributed Redis rate limiting in
  staging/production and a deterministic in-memory test/development backend.
  Redis failure closes protected endpoints rather than silently disabling limits.
- Administrative APIs enforce the administrator role for assignment changes,
  privacy-request review, and audit access. Database and ORM safeguards make audit
  records append-only; patient access, consent/assignment, safety settings,
  acknowledgements, and administrative actions emit content-minimal events.
- The maintenance worker expires retained authentication records and executes only
  administrator-approved deletion requests, pseudonymizing the account while
  transactionally removing patient-domain records. JWT `kid` headers and previous
  signing secrets support controlled signing-key rollover.
- The production reference topology includes Caddy HTTPS termination, controlled
  migrations, PostgreSQL, Redis, a worker, object storage, external secret mounts,
  OTLP tracing, Prometheus metrics, and starter availability/error-rate alerts.
  Encrypted `age` backup and guarded restore-drill scripts are documented in
  `deploy/README.md`; the compose database deliberately makes no false PITR claim.
- Android now uses restricted modern TLS for HTTPS, battery-aware exponential sync
  retry, reboot/time/time-zone rescheduling, saved activity/navigation state, and
  Room-backed screen reads. Compiled instrumentation tests verify the complete
  Room 1-to-4 migration preserves an offline queued event and recovery restores a
  checkpointed last-known-good database instead of silently discarding the queue.
- The dashboard has an application error boundary, a shared React Query cache,
  caregiver availability/notification preferences, relationship controls, and
  labeled device/session management. Backend authorization remains authoritative.

## Phase 2 acceptance status

All Phase 2 work that can be implemented and locally verified in this repository
is present. Phase 2 is **implementation-complete but not operationally accepted**.
Acceptance still requires deploying the reference topology in separate staging and
production environments and recording real evidence for HTTPS, managed secrets,
SMS/email delivery, Redis behavior, telemetry/alert delivery, encrypted restore,
managed PostgreSQL point-in-time recovery, expected-load latency, uptime, and
Android device/emulator recovery. The 99.5% availability/crash-free targets and
P95 latency targets require measured pilot data; source code cannot prove them.

## Phase 3 implementation status

- The backend and Android catalog now contain all six planned activities:
  Memory Match, Object Recall, Pattern Completion, Sequence Recall, Daily Routine
  Recall, and Story Recall. Each flow has an introduction, practice step,
  pause/resume, simple progress, supportive correction, and calm completion.
- Activity UI state uses saveable Compose state and the active activity/event is
  retained by `SavedStateHandle`. Room retains the catalog content version for
  offline use. Completion records now include event ID, content version,
  difficulty, timestamps, attempts, accuracy, response time, completion state,
  interruptions, accessibility mode, offline origin, and app/model versions.
- Reminder records now carry upcoming/snoozed/done/missed state, acknowledgement
  time, snooze time, repeat rule, enabled state, and IANA time zone. Android uses
  WorkManager and separate notification channels for medication, hydration,
  appointment, and activity reminders, restores schedules after reboot/time-zone
  changes, and supports offline Snooze and Done actions with later sync.
- Patients cannot create or alter medication schedules. An assigned caregiver or
  administrator must confirm those operations, and confirmations create minimal
  audit events. Medication copy explicitly avoids dosage advice and does not
  infer consumption from the Done action.
- The caregiver web has a patient-scoped reminder page for one-time, daily, and
  weekly schedules. Medication creation requires an explicit confirmation, and
  enabling or disabling an existing medication reminder requires reconfirmation.
- Patient reminder controls and game actions use 56dp-or-larger targets. Compose
  tests cover the guided practice/pause/correction/completion path and reminder
  action sizing; JVM tests cover offline snooze and complete activity metadata.
- `PHASE3_CONTENT_REVIEW.md` registers all current content as prototype-only and
  lists the required NER community, language, accessibility, and clinical-safety
  review before pilot use.

## Phase 3 acceptance status

Phase 3 is **in progress**. Repository implementation covers the six activity
flows, state capture, and the core reminder lifecycle. It is not accepted until
the content and language review is approved and representative-device sessions
verify TalkBack, font scaling, tremor/imprecise touch, low vision, hearing needs,
cognitive load, process death, reboot restoration, and sustained offline use.
The instrumentation tests compile locally but still require an Android device or
emulator to execute.
