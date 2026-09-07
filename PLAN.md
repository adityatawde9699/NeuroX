
# NeuroX Project Plan

## Product guardrails

NeuroX is a supportive cognitive-engagement, daily-assistance, and caregiver-visibility platform. It is not a diagnostic, treatment, clinical prediction, or guaranteed emergency-response system.

The patient experience must remain voice-first, accessible, regional-language aware, and usable with intermittent connectivity. The caregiver experience must provide clear, minimal, consented visibility without overloading users with data.

## Current status

- **Last updated:** 2026-09-07 (Phases 1–3 closed)

### Completed

The following phases have substantial core implementations. Release readiness still depends on the external integrations and Android toolchain called out below:

- ✅ Phase 1 foundation: Android prototype, caregiver dashboard, FastAPI service, authentication, persistence, production JWT/CORS configuration, logout revocation, Alembic initial migration + Phase 3 `next_difficulty` column migration, and backend smoke coverage are implemented and passing.
- ✅ Phase 2 patient MVP: API-backed activities/reminders, ownership checks, Room-backed profile/activity/reminder/history/contact/safety caches, idempotent `/sync/events`, offline queueing, reconnect scheduling, and full reminder CRUD / activity history / caregiver-ownership API tests are implemented.
- ✅ Phase 3 performance and personalization: persisted metrics, recent-history difficulty adjustment, next-level updates written back to the `patients.next_difficulty` column, truthful dashboard performance states, dedicated performance-route and report-route tests (including date-filter and boundary tests), and a PostgreSQL migration verification script are implemented.
- ✅ Phase 4 voice and language: provider abstractions, runtime provider selection, microphone permission flow, capability-aware voice UI, deterministic intents, language registry, backend language-config test, Assamese fallback, and BHASHINI API guard are implemented. Real BHASHINI audio capture, Assamese TTS probing/integration, provider credentials, and Android build validation remain environment-dependent.
- ✅ Phase 5 offline and sync: Room structured caches, pending-event storage, WorkManager reconnect scheduling, server conflict policy, retry classification, sync-state UI (pending counts, last synced label) are implemented. End-to-end Android sync verification remains environment-dependent.
- ✅ Phase 6 safety support: safety APIs, Android safety actions, Room-backed offline SOS/location queueing, browser geolocation, dashboard error states, migrations, route tests, freshness labels, safe-zone/late-return checks, escalation priority logic, acknowledge authorization tests, and prototype escalation are implemented. Background escalation scheduling and real SMS/WhatsApp/push/website delivery remain environment-dependent.
- ✅ Phase 7 caregiver dashboard: typed API client with refresh/logout handling, URL-backed patient-preserving navigation, modular auth/bootstrap/layout/API/type/page/hook/UI modules, assigned-patient selection, patient profile, activities, alerts, report filters/series, location history/settings, safety views, caregiver profile settings, password management, emergency-contact CRUD, backend report/history authorization coverage, Alert severity/escalation UI polish, and Vitest component coverage are implemented.

### Remaining

- ⏳ Phase 8: comprehensive API/auth/sync/UI tests, accessibility review, environment/security review, demo script, and limitations documentation.

Immediate next step: finish modular patient subroutes/settings and frontend tests, then run Android/PostgreSQL verification and the remaining accessibility/security review.

Phase 1 core foundation is implemented; backend/frontend verification and migration smoke checks pass, while Android build verification remains environment-dependent:

- Android Jetpack Compose patient-app scaffold with home screen and persistent navigation
- React caregiver dashboard shell with responsive layout and authentication screen
- FastAPI service with SQLAlchemy, PostgreSQL-ready configuration, SQLite local fallback, demo data, and protected APIs
- Email/password authentication, Google Identity token verification, JWT access tokens, and rotating refresh sessions
- Deterministic adaptive-difficulty service
- Project documentation, Docker PostgreSQL service, environment template, MIT license, and Git repository setup

Phase 2 core patient flows and durable offline synchronization are implemented; Android UI and end-to-end emulator verification remain:

- Patient Activities, Reminders, Safety, and Profile navigation destinations are implemented as Android prototype screens.
- Memory Match and Remember the Objects are playable, with large controls, progress, completion feedback, attempts, and response-time display.
- Activity sessions are persisted through FastAPI with idempotent event IDs and start, complete, and history APIs.
- Reminder records are persisted through FastAPI with list, create, update, delete, and completion-state support.
- Android patient app authenticates against FastAPI, loads activities and reminders, sends activity start/completion metrics, and marks reminders complete through the API.
- Android screens show loading, empty, error, offline, and sync status states; emulator API traffic uses `10.0.2.2:8000`.
- Patient, caregiver, caregiver-patient assignment, and emergency-contact models are persisted with patient ownership checks on patient-scoped routes.

## Phase 2 — Patient MVP ✅ Complete

Goal: deliver the essential elderly-user experience with simple, usable activity and reminder flows.

1. ✅ Build patient navigation destinations: Activities, Reminders, Safety, and Profile.
2. ✅ Implement Memory Match and Remember the Objects with large controls, progress, and completion screens. Voice instructions remain part of Phase 4.
3. ✅ Persist activity ID, timestamps, accuracy, response time, attempts, completion status, difficulty, offline origin, and event ID through FastAPI.
4. ✅ Implement persistent reminder records and simple patient reminder cards.
5. ✅ Add Android-to-API integration plus loading, empty, error, offline, and sync-success states to every patient screen.

Exit criteria:

- ✅ A patient can complete an activity and see a supportive completion result.
- ✅ A patient can see today’s reminders without navigating a complex interface.
- No activity or UI describes a score as medical information.

## Phase 3 — Performance and personalization ✅ Complete

Goal: use activity data to choose an appropriate next activity level.

1. ✅ Persist activity sessions and performance summaries in PostgreSQL.
2. ✅ Connect the Android app to `POST /activities/{id}/complete`.
3. ✅ Expand the deterministic adaptive-difficulty service with recent-history inputs.
4. ✅ Display the transparent message: “Your next activity is adjusted to your performance.”
5. ✅ Add caregiver activity completion, accuracy, response-time, and difficulty charts.

Exit criteria:

- ✅ Difficulty remains within levels 1–5.
- ✅ The system lowers difficulty after consistently low completion/performance and raises it after consistently strong performance.
- ✅ Dashboard labels use “Activity Performance” and “Engagement Trend,” never clinical labels.

## Phase 4 — Voice and language 🟡 Core implementation present; audio/TTS integration pending

Goal: make core interactions usable by speaking naturally to a nearby phone.

1. ✅ Define `SpeechProvider`, `MockSpeechProvider`, `WhisperSpeechProvider`, and `BHASHINISpeechProvider` interfaces.
2. ✅ Add a listening screen with a large microphone, waveform, transcript, Speak Again, and Continue actions.
3. ✅ Add intent handling for starting activities, hearing reminders, and requesting help.
4. ✅ Create shared language configuration: `languageCode`, `languageName`, `speechSupported`, and `ttsSupported`.
5. ✅ Support Assamese first; show a clear fallback when speech or TTS is unavailable for a selected language.

Exit criteria:

- The app never claims speech support for a language that the selected provider cannot support.
- Voice controls have an equivalent large touch action.

## Phase 5 — Offline-first support 🟡 Queue, structured cache, conflict handling, and reconnect scheduling implemented; verification pending

Goal: keep core patient support working when connectivity is unavailable.

1. ✅ Add Room-backed pending sync storage with migration-safe failure states and structured profile/reminder/history/contact/safety caches.
2. ✅ Create an idempotent event queue using unique event IDs.
3. ✅ Queue activity completions, reminder updates, location updates, and SOS events while offline.
4. ✅ Sync queued events through `POST /sync/events` when the app refreshes after connectivity returns.
5. ✅ Add WorkManager reconnect scheduling with network constraints and retry classification; complete syncing-state presentation remains.

Exit criteria:

- Activity/reminder/SOS/location writes survive backend outages in the Room queue.
- Repeated synchronization never creates duplicate activity events or safety events.
- Stale location uploads are rejected as conflicts rather than replacing newer data.
- Cached profile, activities, reminders, history, contacts, and safety state remain available after a process restart without backend access.
- Full sync-state presentation and Android end-to-end verification remain.

## Phase 6 — Safety support 🟡 Core implementation present; delivery and background verification pending

Goal: provide transparent, permission-aware caregiver safety support.

1. ✅ Add emergency contacts, SOS event creation, and caregiver acknowledgement APIs.
2. ✅ Add a patient Safety screen with status, GPS accuracy, expected return time, contacts, “I Need Help,” and SOS.
3. ✅ Add safe-zone and expected-return configuration to the caregiver dashboard.
4. ✅ Add location updates, last-known-location state, safe-zone exit checks, and late-return alerts.
5. ✅ Implement prototype alert escalation: primary caregiver, then secondary caregiver when unacknowledged.

Exit criteria:

- ✅ Location always displays its freshness, accuracy, and connection state.
- ✅ Offline users see “Last known location,” not real-time claims.
- ✅ SOS is clearly described as a caregiver workflow, not direct government/emergency-service integration.

Remaining validation and production gaps:

- Add route tests for safe-zone exit, late-return, and escalation authorization paths.
- Run the initial Alembic migration against PostgreSQL and add schema evolution migrations as models change.
- Connect real SMS, WhatsApp, app-push, and website delivery channels; current escalation remains API-visible prototype state.
- Add a background worker so safety evaluation does not depend on incidental API requests.

## Phase 7 — Caregiver dashboard completion

Goal: make caregiver tasks fast, clear, and secure.

1. ✅ Implement modular patient list, patient profile, activities, alerts, location, reports, and settings routes.
2. ✅ Connect dashboard widgets and modular pages to protected FastAPI APIs.
3. ✅ Enforce caregiver-patient assignment checks on current patient-specific APIs.
4. ✅ Add separate alert severity and escalation-priority presentation across all alert views.
5. ✅ Add activity report data for completion, accuracy, response time, performance trend, and difficulty progression.

Exit criteria:

- Unrelated caregivers cannot read another patient’s data.
- Alerts can be acknowledged and show state changes.
- Reports use supportive, non-clinical language.

## Phase 8 — Polish, quality, and demo readiness

Goal: prepare a reliable Smart India Hackathon demonstration.

1. Add API, authentication, adaptive-difficulty, and synchronization tests.
2. Add Android UI tests for primary patient flows.
3. Add dashboard component and route tests.
4. Run accessibility review: text size, contrast, 48dp targets, icon-plus-label controls, and clear error states.
5. Verify environment setup, no committed secrets, CORS configuration, and safe logging.
6. Prepare a one-minute demo script using fictional data for Maya Devi and Anita Devi.
7. Document known limitations and post-hackathon validation needs.

Exit criteria:

- Web production build, backend tests, and Android build pass.
- Demo works with seeded fictional data and no external AI service required.
- README provides reproducible setup instructions.

## Suggested implementation order

1. Patient activities and session persistence
2. Reminder APIs and Android reminder screens
3. Caregiver patient/profile/activity routes and modular dashboard extraction
4. Offline queue and sync events
5. Voice provider abstraction and Assamese prototype flow
6. SOS, contacts, location, and safe zones
7. Frontend tests, accessibility, and demo polish

## Definition of done

A feature is done when it has a simple user flow, secure authorization where applicable, loading/error/offline handling, appropriate tests or build verification, and language that accurately reflects NeuroX’s supportive—not clinical—role.
