
# NeuroX Project Plan

## Product guardrails

NeuroX is a supportive cognitive-engagement, daily-assistance, and caregiver-visibility platform. It is not a diagnostic, treatment, clinical prediction, or guaranteed emergency-response system.

The patient experience must remain voice-first, accessible, regional-language aware, and usable with intermittent connectivity. The caregiver experience must provide clear, minimal, consented visibility without overloading users with data.

## Current status

**Last updated:** 2026-09-06

### Completed

The following phases have substantial core implementations, but are not release-complete until their missing behavior and validation are finished:

- 🟡 Phase 1 foundation: Android prototype, caregiver dashboard shell, FastAPI service, authentication, persistence, and deterministic personalization foundation. Build and broader automated-test evidence is still pending.
- 🟡 Phase 2 patient MVP: API-backed activities and reminders, patient/caregiver ownership models, emergency contacts, and UI loading/error/offline states. Durable offline writes and reconnect synchronization are still Phase 5 work.
- 🟡 Phase 3 performance and personalization: persisted activity metrics, recent-history difficulty adjustment, Android next-level updates, and caregiver performance chart data. Route-level API tests and independent PostgreSQL/dashboard verification are still pending.
- ✅ Phase 4 voice and language: `SpeechProvider` interface with `MockSpeechProvider` / `AndroidSpeechProvider` / `BHASHINISpeechProvider` / `WhisperSpeechProvider` implementations; `LanguageConfig` registry (`bhashinSupported` field, Assamese/English/Hindi); `VoiceIntent` sealed hierarchy with deterministic `IntentParser`; `VoiceListeningScreen` with mic button, animated waveform, transcript, intent routing, BHASHINI capability pill, and touch equivalents; language card on Home/Profile/dashboard; `GET /language-config` endpoint with `bhashinSupported` field; and Assamese TTS fallback. Runtime provider capability checks, real audio capture for BHASHINI, Assamese TTS, and Android build validation are still pending.

### Remaining

- ⏳ Phase 5: Room-backed offline entities, idempotent sync queue, queued activity/safety events, and reconnect synchronization.
- ⏳ Phase 6: SOS workflow, emergency-contact actions, location updates, safe zones, late-return alerts, and alert escalation.
- ⏳ Phase 7: complete caregiver routes, protected dashboard data flows, alert acknowledgement, and patient reports.
- ⏳ Phase 8: comprehensive API/auth/sync/UI tests, accessibility review, environment/security review, demo script, and limitations documentation.

Immediate next step: finish the backend safety and alert domain while closing the Phase 1–4 validation gaps, then complete end-to-end automated tests and a production-readiness review.

Phase 1 core foundation is implemented; build and broader automated verification remain:

- Android Jetpack Compose patient-app scaffold with home screen and persistent navigation
- React caregiver dashboard shell with responsive layout and authentication screen
- FastAPI service with SQLAlchemy, PostgreSQL-ready configuration, SQLite local fallback, demo data, and protected APIs
- Email/password authentication, Google Identity token verification, JWT access tokens, and rotating refresh sessions
- Deterministic adaptive-difficulty service
- Project documentation, Docker PostgreSQL service, environment template, MIT license, and Git repository setup

Phase 2 core patient flows are implemented; durable offline synchronization remains in Phase 5:

- Patient Activities, Reminders, Safety, and Profile navigation destinations are implemented as Android prototype screens.
- Memory Match and Remember the Objects are playable, with large controls, progress, completion feedback, attempts, and response-time display.
- Activity sessions are persisted through FastAPI with idempotent event IDs and start, complete, and history APIs.
- Reminder records are persisted through FastAPI with list, create, update, delete, and completion-state support.
- Android patient app authenticates against FastAPI, loads activities and reminders, sends activity start/completion metrics, and marks reminders complete through the API.
- Android screens show loading, empty, error, offline, and sync status states; emulator API traffic uses `10.0.2.2:8000`.
- Patient, caregiver, caregiver-patient assignment, and emergency-contact models are persisted with patient ownership checks on patient-scoped routes.

## Phase 2 — Patient MVP 🟡 Core implementation present; offline completion pending

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

## Phase 3 — Performance and personalization 🟡 Core implementation present; verification pending

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

## Phase 4 — Voice and language 🟡 Core implementation present; provider integration pending

Goal: make core interactions usable by speaking naturally to a nearby phone.

1. Define `SpeechProvider`, `MockSpeechProvider`, `WhisperSpeechProvider`, and `BHASHINISpeechProvider` interfaces.
2. Add a listening screen with a large microphone, waveform, transcript, Speak Again, and Continue actions.
3. Add intent handling for starting activities, hearing reminders, and requesting help.
4. Create shared language configuration: `languageCode`, `languageName`, `speechSupported`, and `ttsSupported`.
5. Support Assamese first; show a clear fallback when speech or TTS is unavailable for a selected language.

Exit criteria:

- The app never claims speech support for a language that the selected provider cannot support.
- Voice controls have an equivalent large touch action.

## Phase 5 — Offline-first support

Goal: keep core patient support working when connectivity is unavailable.

1. Add Room entities for profile, reminders, activity sessions, emergency contacts, and sync events.
2. Create an idempotent event queue using unique event IDs.
3. Queue activity completions and safety updates while offline.
4. Sync queued events through `POST /sync/events` when a connection returns.
5. Show “Working Offline,” “Syncing your data…,” and “Synced successfully” states.

Exit criteria:

- Activities, local history, reminders, and emergency contacts work without backend availability.
- Repeated synchronization never creates duplicate activity events.

## Phase 6 — Safety support

Goal: provide transparent, permission-aware caregiver safety support.

1. Add emergency contacts, SOS event creation, and caregiver acknowledgement APIs.
2. Add a patient Safety screen with status, GPS accuracy, expected return time, contacts, “I Need Help,” and SOS.
3. Add safe-zone and expected-return configuration to the caregiver dashboard.
4. Add location updates, last-known-location state, safe-zone exit checks, and late-return alerts.
5. Implement prototype alert escalation: primary caregiver, then secondary caregiver when unacknowledged.

Exit criteria:

- Location always displays its freshness, accuracy, and connection state.
- Offline users see “Last known location,” not real-time claims.
- SOS is clearly described as a caregiver workflow, not direct government/emergency-service integration.

## Phase 7 — Caregiver dashboard completion

Goal: make caregiver tasks fast, clear, and secure.

1. Implement patient list, patient profile, activities, alerts, location, reports, and settings routes.
2. Connect dashboard widgets to protected FastAPI APIs.
3. Enforce caregiver-patient assignment checks for every patient-specific API.
4. Add alert priority hierarchy: routine, medium, high, and critical.
5. Add simple reports for activity completion, accuracy, response time, performance trend, and difficulty progression.

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
3. Caregiver patient/profile/activity routes
4. Offline queue and sync events
5. Voice provider abstraction and Assamese prototype flow
6. SOS, contacts, location, and safe zones
7. Tests, accessibility, and demo polish

## Definition of done

A feature is done when it has a simple user flow, secure authorization where applicable, loading/error/offline handling, appropriate tests or build verification, and language that accurately reflects NeuroX’s supportive—not clinical—role.
