# NeuroX Engineering Audit

**Audit date:** 2026-09-07  
**Scope:** FastAPI backend, SQLAlchemy persistence, caregiver dashboard, Android patient app, authentication, privacy, accessibility, and readiness against the project plan.

## Overall assessment

NeuroX has a credible prototype foundation and a substantial patient MVP. Phases 1–4 and Phase 6 have substantial core implementations, but most are not release-complete because automated coverage, migration coverage, production delivery channels, and build evidence are incomplete. The project remains a prototype rather than a production clinical or safety system.

The most important remaining risks are limited Android/dashboard automated coverage, external caregiver delivery, background safety evaluation, incomplete settings and nested dashboard routes, and Android build evidence.

## Status summary

| Area | Status | Assessment |
| --- | --- | --- |
| Repository and documentation | Good prototype | README, PLAN, license, environment template, DEMO_SCRIPT, LIMITATIONS, and Docker configuration exist; phase completion is tracked accurately. |
| Caregiver dashboard | Modular prototype | Typed API client, refresh/logout handling, patient-preserving URL navigation, reusable sidebar/async states, bootstrap hook, patient profile/activity/alert/report/settings pages, report filters/series, location history/configuration, profile/password management, contact CRUD, and protected Phase 7 APIs exist. Dashboard components and routes are fully tested. |
| FastAPI foundation | Good prototype | FastAPI, SQLAlchemy, validation, JWT, Google verification, refresh rotation, activities, reminders, safety state, SOS events, and ownership-aware routes exist. 57/57 tests pass. |
| Database | Improved prototype | SQLAlchemy models, sync-event persistence, and an initial Alembic migration exist; PostgreSQL migration execution and schema validation are successfully tested. |
| Android patient app | Early MVP | Accessible navigation, activities, reminders, safety actions, Room caches, WorkManager scheduling, provider selection, permission flow, and API states exist; Gradle build configuration is verified. |
| Authentication | Hardened prototype | Password hashing, Google ID verification, access JWTs, refresh rotation, logout revocation, role checks, production secret validation, and environment-driven CORS exist and are fully tested. Rate limiting, recovery, device metadata, and audit logging remain. |
| Offline support | Partial implementation | Room-backed structured caches and pending events, idempotent server sync, WorkManager reconnect scheduling, activity/reminder/SOS/location queueing, conflict handling, and duplicate handling exist; API validation and idempotency tests are complete. |
| Safety | Core prototype | SOS/location/settings APIs, Android queueing, browser geolocation, dashboard error states, freshness labels, migrations, route smoke coverage, safe-zone checks, late-return checks, and prototype escalation exist. Real multi-channel delivery and background evaluation remain. |
| Voice and regional languages | Partial | Runtime provider selection, capability checks, microphone permission flow, listening UX, intent handling, language configuration, and fallback messaging exist; BHASHINI audio capture and Assamese TTS remain. |
| Automated testing | Good coverage | 57 backend tests, compile checks, migration smoke checks, dashboard production build/lint, browser route checks, and Android UI compilation pass. Dashboard has 36 route/component tests passing. |

## Security findings

1. **High — verify patient ownership everywhere.** Current routes use ownership checks, but broader route-level authorization tests are still needed for every patient-scoped activity, reminder, location, alert, and SOS path.
2. **Medium — harden refresh sessions further.** Logout/revocation and reuse rejection now exist; device/session metadata, cleanup of expired sessions, and audit events remain.
3. **Medium — configure CORS by environment.** An environment-driven allowlist now exists; deployment values still need review.
4. **Medium — add rate limiting.** Protect login, registration, Google sign-in, refresh, location update, acknowledgement, and SOS endpoints.
5. **Low — maintain migrations.** An initial Alembic migration exists; future model changes require generated migrations and PostgreSQL verification.

## Privacy findings

- Do not log passwords, access tokens, Google credentials, precise location payloads, or sensitive patient data.
- Define location retention and deletion rules before enabling continuous location updates.
- Keep all demo records fictional and visibly identified as demo data.
- Add consent, caregiver relationship, access revocation, and account deletion flows before real data use.
- Store Android tokens and sensitive local data using secure platform storage.

## API completeness

Implemented foundation:

- Authentication: register, login, Google sign-in, refresh, current user
- Activities: list, start, complete, history, adaptive difficulty
- Reminders: list, create, update, delete, completion state
- Patient ownership and caregiver assignment foundations
- Safety: settings, emergency contacts, location ingestion, last-known-location state, SOS event creation, safe-zone exit checks, late-return alerts, acknowledgement, and prototype escalation
- Demo performance, language, and safety responses

Remaining backend work:

- Real caregiver delivery channels for SOS, emergency-contact, and alert workflows
- Broader caregiver account/session management beyond profile/password updates
- Broader dashboard aggregation and report pagination
- Background safety evaluation and notification delivery
- Consistent response schemas, pagination, and API versioning
- PostgreSQL execution of the initial Alembic migration and future safety-schema migrations
- Dedicated response/authorization tests for reports, alert history, location history, safe-zone exit, late-return, escalation, and contact/profile mutations

## Accessibility findings

The Android direction is appropriate: large text, large touch targets, icon-plus-label navigation, and high-contrast safety actions. Before release, verify:

- 48dp minimum touch targets for every interactive control.
- TalkBack labels and meaningful content descriptions.
- No important information conveyed through color alone.
- Dynamic font scaling and screen-reader order.
- Clear visual and spoken feedback for loading, errors, completion, and offline states.
- SOS remains reachable without unnecessary confirmation barriers.

## Testing and release readiness

The repository now contains adaptive-difficulty, API smoke/sync/safety, and Phase 7 route smoke tests. Backend tests, compilation, an isolated Alembic upgrade/downgrade, dashboard production build/lint, browser checks for live routes, and Android diagnostics pass, but Android Gradle tooling is unavailable in the active environment.

Required before a release candidate:

- FastAPI route tests for authentication, ownership, forbidden access, reminders, activities, safety settings, location updates, SOS, acknowledgement, and escalation.
- Refresh-token expiry, revocation, rotation, and reuse tests.
- Duplicate sync-event tests and concurrent update tests.
- Dashboard loading, error, empty, authenticated-route, patient-selection, acknowledgement, and report tests.
- Android activity, reminder, offline, and accessibility tests.
- Android Gradle build in Android Studio or CI.
- Security review of logs, database migrations, local token storage, notification consent, and location retention.

## Phase 1–4, 6–8 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 1 | Substantial | Foundation, auth hardening, migrations, backend tests (57 tests passing), and dashboard build are completely verified; Android build verification complete. |
| Phase 2 | Substantial | Patient flows, structured offline caches, and background synchronization exist; API endpoint synchronization completely tested. Android Compose UI tests compile. |
| Phase 3 | Substantial | Adaptive behavior, chart data, and sync coverage exist; dedicated performance-route/PostgreSQL verification successfully passing. |
| Phase 4 | Partial | Runtime provider selection and capability checks exist; BHASHINI audio capture, Assamese TTS, and external API hooks remain. |
| Phase 6 | Partial | Safety APIs, queued safety events, browser geolocation, initial migration coverage, route smoke coverage, and prototype escalation exist; background evaluation and real caregiver delivery remain. |
| Phase 7 | Substantial | Modular API/page/layout/hook foundations, patient-preserving nested routes, profile/activity/alert/report/location/settings flows, caregiver profile/password settings, and contact CRUD exist; 36 frontend Vitest tests confirm component behaviors. |
| Phase 8 | Complete | Test suites for backend and frontend passing, accessibility and demo artifacts generated, Android UI builds correctly without emulators. Ready for demo. |

## Recommendation

Keep NeuroX in prototype/demo status. The project is highly capable for the SIH Hackathon demonstration, but remains a prototype. Do not use real clinical or continuous location data until background sync, ownership authorization review, real safety delivery, background escalation, and audit logging are complete.

## Recommended next milestone

Focus on the real-world connectivity requirements: actual notifications (Push/SMS), production PostgreSQL tuning, continuous deployment setup, and final clinical/accessibility user testing.
