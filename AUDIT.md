# NeuroX Engineering Audit

**Audit date:** 2026-09-07  
**Scope:** FastAPI backend, SQLAlchemy persistence, caregiver dashboard, Android patient app, authentication, privacy, accessibility, and readiness against the project plan.

## Overall assessment

NeuroX has a credible prototype foundation and a substantial patient MVP. Phases 1–4 and Phase 6 have substantial core implementations, but most are not release-complete because automated coverage, migration coverage, production delivery channels, and build evidence are incomplete. The project remains a prototype rather than a production clinical or safety system.

The most important remaining risks are limited Android/dashboard automated coverage, external caregiver delivery, background safety evaluation, incomplete settings and nested dashboard routes, and Android build evidence.

## Status summary

| Area | Status | Assessment |
| --- | --- | --- |
| Repository and documentation | Good prototype | README, PLAN, license, ignore rules, environment template, and Docker configuration exist; phase completion claims have been corrected to reflect verification gaps. |
| Caregiver dashboard | Modular prototype | Typed API client, refresh/logout handling, patient-preserving URL navigation, reusable sidebar/async states, bootstrap hook, patient profile/activity/alert/report/settings pages, report filters/series, location history/configuration, profile/password management, contact CRUD, and protected Phase 7 APIs exist; frontend tests remain. |
| FastAPI foundation | Good prototype | FastAPI, SQLAlchemy, validation, JWT, Google verification, refresh rotation, activities, reminders, safety state, SOS events, and ownership-aware routes exist. |
| Database | Improved prototype | SQLAlchemy models, sync-event persistence, and an initial Alembic migration exist; PostgreSQL migration execution and future schema migration discipline remain. |
| Android patient app | Early MVP | Accessible navigation, activities, reminders, safety actions, Room caches, WorkManager scheduling, provider selection, permission flow, and API states exist; Gradle build evidence, UI tests, and full safety/location integration verification remain. |
| Authentication | Hardened prototype | Password hashing, Google ID verification, access JWTs, refresh rotation, logout revocation, role checks, production secret validation, and environment-driven CORS exist. Rate limiting, recovery, device metadata, and audit logging remain. |
| Offline support | Partial implementation | Room-backed structured caches and pending events, idempotent server sync, WorkManager reconnect scheduling, activity/reminder/SOS/location queueing, conflict handling, and duplicate handling exist; full sync-state UI and Android end-to-end verification remain. |
| Safety | Core prototype | SOS/location/settings APIs, Android queueing, browser geolocation, dashboard error states, freshness labels, migrations, route smoke coverage, safe-zone checks, late-return checks, and prototype escalation exist. Real multi-channel delivery and background evaluation remain. |
| Voice and regional languages | Partial | Runtime provider selection, capability checks, microphone permission flow, listening UX, intent handling, language configuration, and fallback messaging exist; BHASHINI audio capture and Assamese TTS remain. |
| Automated testing | Improving but incomplete | 16 backend tests, compile checks, migration smoke checks, dashboard production build/lint, browser route checks, and Android diagnostics pass; Android Gradle, dashboard route/component, PostgreSQL, and broader authorization/safety tests remain. |

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

## Phase 1–4 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 1 | Partial | Foundation, auth hardening, migrations, backend tests, and dashboard build are verified; Android build and broader UI verification are not demonstrated. |
| Phase 2 | Partial | Patient flows, structured offline caches, and background synchronization exist; Android UI and end-to-end emulator verification remain. |
| Phase 3 | Partial | Adaptive behavior, chart data, and sync coverage exist; dedicated performance-route/PostgreSQL verification remains. |
| Phase 4 | Partial | Runtime provider selection and capability checks exist; BHASHINI audio capture, Assamese TTS, and Android build verification remain. |

## Phase 6 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 6 | Partial | Safety APIs, queued safety events, browser geolocation, initial migration coverage, route smoke coverage, and prototype escalation exist; background evaluation and real caregiver delivery remain. |

## Phase 7 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 7 | Partial | Modular API/page/layout/hook foundations, patient-preserving nested routes, profile/activity/alert/report/location/settings flows, caregiver profile/password settings, and contact CRUD exist; frontend tests, PostgreSQL verification, and complete dashboard coverage remain. |

## Recommendation

Keep NeuroX in prototype/demo status. Do not use real clinical or continuous location data until background sync, ownership authorization review, real safety delivery, background escalation, audit logging, and Android/PostgreSQL verification are complete.

## Recommended next milestone

Add frontend route/component tests, configured caregiver delivery, background safety evaluation, and Android/PostgreSQL release verification.
