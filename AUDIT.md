# NeuroX Engineering Audit

**Audit date:** 2026-09-07  
**Scope:** FastAPI backend, SQLAlchemy persistence, caregiver dashboard, Android patient app, authentication, privacy, accessibility, and readiness against the project plan.

## Overall assessment

NeuroX has a credible prototype foundation and a substantial patient MVP. Phases 1–4 and Phase 6 have substantial core implementations, but most are not release-complete because automated coverage, migration coverage, production delivery channels, and build evidence are incomplete. The project remains a prototype rather than a production clinical or safety system.

The most important remaining risks are incomplete durable offline synchronization, limited automated test coverage, production hardening of authorization, migrations, secret enforcement, audit logging, and real caregiver alert delivery.

## Status summary

| Area | Status | Assessment |
| --- | --- | --- |
| Repository and documentation | Good prototype | README, PLAN, license, ignore rules, environment template, and Docker configuration exist; phase completion claims have been corrected to reflect verification gaps. |
| Caregiver dashboard | Prototype | Responsive shell, auth, overview cards, charts, language badge, safety workflow, acknowledgement actions, and safe-zone/return configuration exist; further routes and reports remain. |
| FastAPI foundation | Good prototype | FastAPI, SQLAlchemy, validation, JWT, Google verification, refresh rotation, activities, reminders, safety state, SOS events, and ownership-aware routes exist. |
| Database | Partial | Core user, session, activity, reminder, patient, caregiver, assignment, emergency-contact, safety settings, location, alert, and SOS data exists; migrations remain. |
| Android patient app | Early MVP | Accessible navigation, activities, reminders, safety/profile screens, API states, and metrics exist; Room sync and complete safety actions remain. |
| Authentication | Prototype-ready | Password hashing, Google ID verification, access JWTs, refresh rotation, and role checks exist. Recovery, administrative revocation, reuse detection, and strict production secret enforcement remain. |
| Offline support | Partial | UI status and event fields exist, but Room-backed durable queues and reconnect synchronization remain. |
| Safety | Core prototype | SOS event creation, caregiver acknowledgement, safety settings, last-known-location state, safe-zone exit checks, late-return alerts, emergency contacts, and primary-to-secondary prototype escalation exist. Durable offline queues, real push/SMS delivery, migrations, and route tests remain. |
| Voice and regional languages | Partial | Provider interfaces, listening UX, intent handling, language configuration, and Assamese fallback messaging exist; real regional-language audio integration and runtime capability verification remain. |
| Automated testing | Insufficient | Smoke tests exist; broad route, authorization, sync, Android, and dashboard tests remain. |

## Security findings

1. **High — verify patient ownership everywhere.** Patient-scoped routes need a consistent caregiver-patient assignment dependency, including future activity, reminder, location, alert, and SOS routes.
2. **Medium — enforce production JWT secrets.** The development fallback for `JWT_SECRET` must be rejected outside development, with minimum length validation.
3. **Medium — harden refresh sessions.** Add logout/revocation, device/session metadata, reuse detection, and cleanup of expired sessions.
4. **Medium — configure CORS by environment.** Replace the development-only origin with an explicit deployment allowlist.
5. **Medium — add rate limiting.** Protect login, registration, Google sign-in, refresh, location update, acknowledgement, and SOS endpoints.
6. **Low — add migrations.** Introduce Alembic before deploying schema changes to PostgreSQL.

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
- Dashboard overview aggregation and reports
- Durable sync-event storage, deduplication, retry, and conflict handling
- Consistent response schemas, pagination, and API versioning
- Alembic migrations for the safety schema
- Route tests for safety authorization, safe-zone exit, late-return, acknowledgement, and escalation

## Accessibility findings

The Android direction is appropriate: large text, large touch targets, icon-plus-label navigation, and high-contrast safety actions. Before release, verify:

- 48dp minimum touch targets for every interactive control.
- TalkBack labels and meaningful content descriptions.
- No important information conveyed through color alone.
- Dynamic font scaling and screen-reader order.
- Clear visual and spoken feedback for loading, errors, completion, and offline states.
- SOS remains reachable without unnecessary confirmation barriers.

## Testing and release readiness

The repository contains adaptive-difficulty tests and documentation of prior dashboard/Python/SQLite checks. A current frontend production build passes after the Phase 6 merge. Backend Python checks could not run because the local virtual environment points to a missing Python install and no system Python is available; Android Gradle tooling is also unavailable in the active environment.

Required before a release candidate:

- FastAPI route tests for authentication, ownership, forbidden access, reminders, activities, safety settings, location updates, SOS, acknowledgement, and escalation.
- Refresh-token expiry, revocation, rotation, and reuse tests.
- Duplicate sync-event and concurrent update tests.
- Dashboard loading, error, empty, and authenticated-route tests.
- Android activity, reminder, offline, and accessibility tests.
- Android Gradle build in Android Studio or CI.
- Security review of CORS, environment secrets, logs, database migrations, and local storage.

## Phase 1–4 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 1 | Partial | Foundation exists, but Android build and broader automated verification are not demonstrated. |
| Phase 2 | Partial | Patient flows exist, but durable offline writes and sync are not implemented. |
| Phase 3 | Partial | Adaptive behavior and chart data exist, but route-level and database verification are missing. |
| Phase 4 | Partial | Voice UI and abstractions exist, but BHASHINI audio is placeholder-based, Assamese TTS is absent, and provider support is not fully runtime-derived. |

## Phase 6 verdict

| Phase | Verdict | Main reason |
| --- | --- | --- |
| Phase 6 | Partial | Safety APIs and dashboard/patient UI are implemented, including last-known-location wording and prototype escalation, but offline safety sync, real caregiver delivery, migrations, and route tests remain. |

## Recommendation

Keep NeuroX in prototype/demo status. Do not use real clinical or continuous location data until ownership authorization, offline synchronization, real safety delivery, secret enforcement, migrations, audit logging, and test coverage are complete and reviewed.

## Recommended next milestone

Implement durable offline sync for activity and safety events, add route-level tests for the new safety domain, and introduce migrations before PostgreSQL deployment.
