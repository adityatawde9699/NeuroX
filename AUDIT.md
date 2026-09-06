# NeuroX Engineering Audit

**Audit date:** 2026-09-06  
**Scope:** FastAPI backend, SQLAlchemy persistence, caregiver dashboard, Android patient app, authentication, privacy, accessibility, and readiness against the project plan.

## Overall assessment

NeuroX has a credible prototype foundation and a substantial patient MVP. Phases 1–4 have substantial core implementations, but none is release-complete because automated coverage and build evidence are incomplete and several claimed behaviors remain stubs or prototypes. The project remains a prototype rather than a production clinical or safety system.

The most important remaining risks are incomplete safety workflows, incomplete durable offline synchronization, limited automated test coverage, and production hardening of authorization, migrations, secret enforcement, and audit logging.

## Status summary

| Area | Status | Assessment |
| --- | --- | --- |
| Repository and documentation | Good prototype | README, PLAN, license, ignore rules, environment template, and Docker configuration exist; phase completion claims have been corrected to reflect verification gaps. |
| Caregiver dashboard | Prototype | Responsive shell, auth, overview cards, charts, alerts, and location presentation exist; further API wiring and routes remain. |
| FastAPI foundation | Good prototype | FastAPI, SQLAlchemy, validation, JWT, Google verification, refresh rotation, activities, reminders, and ownership-aware routes exist. |
| Database | Partial | Core user, session, activity, reminder, patient, caregiver, assignment, and emergency-contact data exists; migrations and the full safety schema remain. |
| Android patient app | Early MVP | Accessible navigation, activities, reminders, safety/profile screens, API states, and metrics exist; Room sync and complete safety actions remain. |
| Authentication | Prototype-ready | Password hashing, Google ID verification, access JWTs, refresh rotation, and role checks exist. Recovery, administrative revocation, reuse detection, and strict production secret enforcement remain. |
| Offline support | Partial | UI status and event fields exist, but Room-backed durable queues and reconnect synchronization remain. |
| Safety | UI/backend partial | Safety presentation and emergency-contact foundations exist; SOS dispatch workflow, locations, safe zones, alert rules, and escalation remain. |
| Voice and regional languages | Partial | Provider interfaces, listening UX, intent handling, language configuration, and Assamese fallback messaging exist; real regional-language audio integration and runtime capability verification remain. |
| Automated testing | Insufficient | Smoke tests exist; broad route, authorization, sync, Android, and dashboard tests remain. |

## Security findings

1. **High — verify patient ownership everywhere.** Patient-scoped routes need a consistent caregiver-patient assignment dependency, including future activity, reminder, location, alert, and SOS routes.
2. **Medium — enforce production JWT secrets.** The development fallback for `JWT_SECRET` must be rejected outside development, with minimum length validation.
3. **Medium — harden refresh sessions.** Add logout/revocation, device/session metadata, reuse detection, and cleanup of expired sessions.
4. **Medium — configure CORS by environment.** Replace the development-only origin with an explicit deployment allowlist.
5. **Medium — add rate limiting.** Protect login, registration, Google sign-in, refresh, and SOS endpoints.
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
- Demo performance and safety responses

Remaining backend work:

- SOS event creation, acknowledgement, and escalation
- Emergency-contact action workflow
- Location ingestion and last-known-location queries
- Safe-zone configuration and exit/late-return rules
- Alert creation, priority, acknowledgement, and caregiver delivery
- Dashboard overview aggregation and reports
- Durable sync-event storage, deduplication, retry, and conflict handling
- Consistent response schemas, pagination, and API versioning

## Accessibility findings

The Android direction is appropriate: large text, large touch targets, icon-plus-label navigation, and high-contrast safety actions. Before release, verify:

- 48dp minimum touch targets for every interactive control.
- TalkBack labels and meaningful content descriptions.
- No important information conveyed through color alone.
- Dynamic font scaling and screen-reader order.
- Clear visual and spoken feedback for loading, errors, completion, and offline states.
- SOS remains reachable without unnecessary confirmation barriers.

## Testing and release readiness

The repository contains adaptive-difficulty tests and documentation of prior dashboard/Python/SQLite checks. A current audit could not reproduce the full validation set because `pytest` is unavailable in the active environment and Android Gradle tooling is unavailable; the dashboard build also requires its project directory and installed dependencies.

Required before a release candidate:

- FastAPI route tests for authentication, ownership, forbidden access, reminders, activities, and safety.
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

## Recommendation

Keep NeuroX in prototype/demo status. Do not use real clinical or continuous location data until ownership authorization, offline synchronization, safety workflows, secret enforcement, migrations, audit logging, and test coverage are complete and reviewed.

## Recommended next milestone

Implement the complete FastAPI safety domain—SOS, contacts, locations, safe zones, alerts, and escalation—then connect the caregiver dashboard to those protected APIs and add route-level tests.
