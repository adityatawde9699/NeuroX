# NeuroX Production Development Plan

**Version:** 2.0

**Updated:** 2026-09-09

**Status:** Hackathon prototype moving toward a controlled pilot

## 1. Mission and boundaries

NeuroX is a voice-first Android application for people living with dementia and a web application for their caregivers. It supports cognitive engagement, reminders, daily routines, caregiver coordination, and location-aware safety workflows. It must remain usable on low-cost Android devices and during intermittent connectivity, with particular attention to Assamese and other North Eastern Region languages.

NeuroX does not diagnose dementia, measure dementia severity, predict clinical decline, prescribe treatment, or guarantee continuous tracking or emergency response. AI may personalize supportive activities and improve speech interaction, but it must never replace clinical judgement or make autonomous emergency decisions.

## 2. Production principles

1. **Person first:** preserve dignity, autonomy, consent, familiar routines, and caregiver trust.
2. **Safety by design:** SOS and geofence rules remain deterministic. AI may assist prioritization but cannot suppress, close, or delay critical alerts.
3. **Offline by default:** activities, reminders, profile, contacts, and queued safety actions work without the server.
4. **Voice plus touch:** every voice action has a large, clear touch equivalent.
5. **Truthful capability:** show last-known location, speech confidence, offline state, and provider limitations accurately.
6. **Privacy minimization:** collect only data needed for the feature, retain it for a defined period, and give users meaningful control.
7. **Evidence before automation:** personalization progresses from rules to shadow-mode models and only then to constrained production decisions.
8. **No clinical claims:** caregiver reports use “activity performance,” “engagement,” and “supportive insight.”

## 3. Current implementation baseline

The repository already contains:

- A Compose Android prototype with activities, reminders, voice UI, safety screens, Room caching, Retrofit, and WorkManager sync.
- A React/TypeScript caregiver dashboard with authentication, patients, activities, reports, alerts, location, contacts, and settings.
- A FastAPI/SQLAlchemy backend with JWT and Google authentication, refresh sessions, caregiver-patient assignments, activities, reminders, performance reports, sync events, locations, safe zones, alerts, and SOS records.
- Deterministic adaptive difficulty based on recent activity sessions.
- Alembic migrations and backend, frontend, and Android test scaffolding.

The current code is still prototype-grade. Production work must begin with the verified blockers below rather than adding more surface area.

## 4. Phase 0 — Stabilize and secure the prototype

**Target:** 2–3 weeks

**Release gate:** all builds and tests pass in CI; no known critical security issue

### Required work

- Restrict public registration to approved roles. Public input must never create `ADMIN` or `HEALTHCARE_WORKER` accounts.
- Fix the current Kotlin compilation error in the unknown voice-intent message.
- Fix frontend TypeScript test matcher configuration so `npm run build` passes.
- Replace the hardcoded Android demo URL and credentials with build configurations and a real setup/sign-in flow.
- Permit cleartext traffic only in the debug Android build; require HTTPS in release builds.
- Move Android tokens to encrypted platform-backed storage.
- Replace browser refresh-token `localStorage` with a secure session design, preferably short-lived access tokens plus an `HttpOnly`, `Secure`, `SameSite` refresh cookie or a backend-for-frontend.
- Refactor the 1,300+ line FastAPI module into routers and services: auth, patients, activities, reminders, safety, sync, reports, and notifications.
- Refactor the large Android activity into MVVM screens, repositories, use cases, dependency injection, and observable UI state.
- Run Alembic against a real PostgreSQL instance and verify upgrade and rollback.

### Acceptance criteria

- Backend tests, dashboard tests/build, Android unit tests, debug APK, and lint pass in CI.
- Authorization tests prove unrelated caregivers cannot access or mutate patient data.
- No production secret, demo password, API URL, or token is embedded in a release binary.
- Static analysis and dependency scanning report no unresolved critical finding.

## 5. Phase 1 — Governance, consent, and patient-centered discovery

**Target:** 4–6 weeks, parallel with Phase 0

**Release gate:** approved pilot protocol and documented product claims

### Required work

- Form a review group including a neurologist or geriatric clinician, occupational therapist, dementia-care specialist, accessibility expert, caregivers, and people living with early-stage dementia.
- Conduct contextual research in at least two NER communities, including rural/low-connectivity households.
- Define supported use cases, contraindications, escalation expectations, caregiver responsibilities, and failure messages.
- Design consent and supported-decision flows for location, voice recordings, caregiver access, notifications, and personalization.
- Obtain legal review against India’s DPDP Act 2023 and applicable DPDP Rules, including notice, consent, access, correction, deletion, grievance handling, breach response, processors, retention, and cross-border processing.
- Establish incident response, vulnerability disclosure, clinical-safety review, and change-control policies.

### Acceptance criteria

- Every data field has a documented purpose, lawful basis/consent path, retention period, and deletion behavior.
- A patient or authorized representative can revoke caregiver access and location sharing.
- Marketing, UI, reports, and support material contain no diagnostic or guaranteed-safety claims.

## 6. Phase 2 — Production platform foundation

**Target:** 6–8 weeks

### Backend and infrastructure

- Deploy versioned FastAPI APIs behind HTTPS with PostgreSQL, Redis, background workers, object storage, and managed secrets.
- Add structured migrations, transactional service boundaries, pagination, consistent error responses, API versioning, and OpenAPI contract tests.
- Add rate limiting, account lockout protections, email/phone verification, password reset, session/device management, token reuse detection, and administrative access controls.
- Add immutable audit events for consent, assignment, patient-data access, safety configuration, acknowledgements, and administrative changes. Audit logs must exclude raw secrets and unnecessary health/location content.
- Add encrypted backups, restore drills, database point-in-time recovery, key rotation, retention jobs, and deletion workflows.
- Add OpenTelemetry traces, metrics, safe structured logs, uptime checks, alerting, and error reporting with PII scrubbing.

### Android foundation

- Use MVVM with Compose, coroutines/Flow, Room, WorkManager, Retrofit, dependency injection, and build variants.
- Separate local and remote data sources behind repositories; make Room the source of truth for patient screens.
- Add encrypted token storage, certificate-aware HTTPS configuration, database migration tests, and corruption recovery.
- Support low-memory devices, battery-aware background work, process death, reboot recovery, and clock/time-zone changes.

### Caregiver dashboard foundation

- Add route guards, session expiry handling, responsive navigation, accessible authentication, error boundaries, and consistent query caching.
- Add server-side authorization for every operation; frontend visibility is never an authorization mechanism.
- Implement notification preferences, caregiver availability, relationship revocation, and device/session management.

### Reliability targets for pilot

- API availability target: 99.5% monthly during the pilot.
- P95 read latency below 500 ms and P95 write latency below 800 ms under expected pilot load.
- Crash-free Android sessions above 99.5%.
- No acknowledged safety event or sync event may be silently lost.

## 7. Phase 3 — Complete the patient cognitive-support experience

**Target:** 6–8 weeks

### Activities

- Stabilize Memory Match and Object Recall.
- Complete Pattern Completion, Sequence Recall, Daily Routine Recall, and Story Recall.
- Add regionally familiar, reviewed content without culturally inappropriate assumptions.
- Add clear introduction, practice round, pause/resume, simple progress, supportive correction, and completion feedback.
- Preserve activity state after process death and while offline.
- Record event ID, activity/content version, difficulty, timestamps, attempts, accuracy, response time, completion, interruptions, accessibility mode, offline origin, and app/model version.

### Reminders and routines

- Implement medication, hydration, appointment, and activity reminders using Android notification channels.
- Support snooze, done, missed, repeat schedules, local time zones, reboot restoration, and offline operation.
- Require caregiver confirmation for schedule changes that could affect medication routines.
- Never provide dosage advice or infer whether medication was actually consumed.

### Patient experience quality

- Use large text, 48dp-or-larger targets, high contrast, stable navigation, TalkBack semantics, and minimal reading.
- Test font scaling, tremor/imprecise touch, low vision, hearing impairment, and cognitive load.
- Provide calm recovery paths; avoid punishment, countdown pressure, streaks, and “failure” language.

## 8. Phase 4 — Reliable offline synchronization

**Target:** 4–6 weeks

- Define an event schema with idempotency keys, schema versions, device time, server time, attempt count, and origin.
- Use an append-only local outbox and transactional writes so local state and queued events cannot diverge.
- Classify retries: transient, authentication, validation, conflict, and permanent failure.
- Refresh expired sessions safely during background synchronization.
- Define conflict policies for reminders, profile updates, safety settings, and caregiver edits.
- Add backoff, battery/network constraints, manual retry, pending/failed visibility, and safe dead-letter handling.
- Test airplane mode, intermittent 2G/3G, server outage, duplicate delivery, reordered events, clock drift, token expiry, app upgrades, and device reboot.

### Acceptance criteria

- Core patient activities and reminders work for at least seven days without connectivity.
- Reconnect produces no duplicate sessions, reminders, SOS events, or locations.
- The patient sees “Working Offline” and the caregiver sees the last successful update time.

## 9. Phase 5 — Voice and NER language production track

**Target:** 8–12 weeks, dependent on provider access and field validation

### Speech architecture

- Keep `SpeechProvider` and `TtsProvider` contracts independent of UI and business logic.
- Support Android speech, BHASHINI, and an optional server speech provider through capability discovery.
- Implement actual microphone capture, audio format conversion, request cancellation, timeout, confidence scores, and provider fallback.
- Process speech ephemerally by default. Do not retain raw audio unless the user gives separate, revocable consent for quality improvement.
- Cache voice instructions locally where licensing and consent allow.

### Language quality

- Validate Assamese first, then add Bodo, Manipuri, Khasi, and other languages only when provider capability and field testing meet release thresholds.
- Build consented evaluation sets across dialect, gender, age, speaking rate, device quality, and background noise.
- Measure word error rate, intent accuracy, fallback rate, correction rate, and task-completion rate by language subgroup.
- Use deterministic, allowlisted intents for activities, reminders, profile, and help. An LLM may clarify phrasing only inside a constrained intent schema; it must not give clinical or emergency advice.
- Always show “I heard,” Speak Again, and Continue. Low confidence must trigger confirmation.

### Initial release thresholds

- At least 95% intent accuracy for SOS/help phrases on the validated test set.
- At least 90% intent accuracy for activity and reminder commands.
- Zero help intents routed to a non-safety action in safety testing.
- Clear touch fallback whenever voice is unavailable or confidence is low.

## 10. Phase 6 — Safety and caregiver delivery

**Target:** 8–10 weeks

### Deterministic safety core

- Keep SOS initiation, safe-zone calculation, stale-location labeling, late-return rules, and escalation timing deterministic and fully testable.
- Add a durable background scheduler for late-return checks, stale-device detection, and unacknowledged-event escalation.
- Add Firebase Cloud Messaging as the primary caregiver notification channel and an approved SMS/voice provider as a configurable fallback.
- Track queued, sent, delivered, opened, acknowledged, escalated, failed, and expired states.
- Add retry policies and an operator view for undelivered critical events.
- Support primary and secondary caregiver escalation. External emergency services remain a manually configured contact action unless a verified integration is implemented.

### Location safeguards

- Make sharing opt-in, visible, revocable, and time-bounded where appropriate.
- Store accuracy, capture time, receive time, provider, connection state, and device permission state.
- Suppress misleading geofence conclusions when accuracy is too poor; report “Location accuracy is low.”
- Use configurable retention and reduce precision in historical views when exact coordinates are unnecessary.

### Safety acceptance criteria

- SOS is locally recorded immediately, even offline.
- When connected, 99% of pilot SOS notifications reach at least one configured caregiver channel within 30 seconds; failures are visible and retried.
- Escalation continues without the dashboard being open.
- UI and documentation clearly state that tracking and response are not guaranteed.

## 11. Phase 7 — Supportive personalization and AI/ML

**Target:** begins with instrumentation; model rollout only after sufficient consented pilot data

### 11.1 Deterministic baseline

- Keep the existing explainable rule engine as the default and fallback.
- Normalize response time per activity and per patient rather than comparing unlike games or users.
- Use rolling history with minimum sample requirements, maximum one-level changes, cooldown periods, and caregiver/patient override.
- Treat fatigue, interruptions, offline delays, motor limitations, and accessibility settings as context—not evidence of cognitive change.

### 11.2 Data and evaluation foundation

- Create a versioned event dictionary, feature definitions, data-quality checks, consent flags, lineage, and deletion propagation.
- Separate operational data from consented model-development datasets.
- Label outcomes as engagement signals: completion, voluntary continuation, assistance requested, repeated errors, abandonment, and reported frustration.
- Never use a “dementia score,” inferred diagnosis, or predicted deterioration label.
- Establish evaluation slices by language, device tier, connectivity, age band, activity, and accessibility mode.

### 11.3 Constrained personalization model

- Start with offline evaluation of simple interpretable models and a constrained contextual bandit; do not assume the bandit is automatically safer or more accurate than rules.
- The action space is limited to activity choice, content variation, instruction repetition, and difficulty levels 1–5.
- Hard constraints override the model: no jump larger than one level, no repeated increase after frustration signals, no unsafe content, and no change to reminders or safety rules.
- Run new policies in shadow mode first, comparing recommendations with the deterministic baseline.
- Promote only after predefined improvements in completion and reduced frustration without subgroup regressions.
- Preserve instant rollback to the deterministic engine and record the policy/model version for every recommendation.

### 11.4 AI-assisted caregiver insights

- Generate summaries only from verified structured facts, such as activities completed, reminder acknowledgements, and location freshness.
- Use templates first. If an LLM is added, require structured output, source attribution, prohibited-claim filters, uncertainty language, and human-visible underlying data.
- Do not generate medical advice, causal explanations, risk predictions, or emergency decisions.

### 11.5 MLOps and AI governance

- Maintain model cards, dataset documentation, intended-use statements, excluded uses, subgroup metrics, approval history, and rollback instructions.
- Apply the NIST AI RMF functions: Govern, Map, Measure, and Manage.
- Monitor missing data, drift, outcome changes, speech confidence, fallback rate, subgroup performance, and model overrides.
- Require product, engineering, privacy, and clinical-safety approval for every production model change.

### AI release criteria

- The model beats the deterministic baseline on predefined engagement metrics in retrospective evaluation and a monitored pilot.
- No evaluated language, device, or accessibility subgroup experiences a material safety or usability regression.
- Recommendations are explainable to caregivers in plain language.
- A rollback drill demonstrates restoration of the deterministic policy without data loss.

## 12. Phase 8 — Caregiver and healthcare-worker experience

**Target:** 6–8 weeks

- Complete multi-patient workflows, patient invitations/consent, relationship revocation, alert inbox, acknowledgement notes, notification preferences, and safe-zone setup.
- Add activity, reminder, response-time, completion, and difficulty reports with date and activity filters.
- Show data freshness, missing-data periods, offline intervals, and model/policy changes so trends are not misleading.
- Add accessible PDF/CSV exports with explicit “supportive information, not diagnosis” labeling.
- Keep healthcare-worker access read-only initially and require explicit patient authorization and organizational controls.
- Add caregiver education, respite/support links, and clear instructions for urgent situations outside NeuroX.

## 13. Phase 9 — Verification, pilot, and release

**Target:** 10–14 weeks

### Automated verification

- Backend: unit, integration, authorization matrix, migration, property-based sync, concurrency, background worker, notification-provider contract, load, and recovery tests.
- Android: unit, Room migration, WorkManager, Compose UI, accessibility, process-death, offline, battery, and low-memory tests on API 26+.
- Web: unit, integration, routed workflow, accessibility, browser, session expiry, and error-state tests.
- Security: SAST, dependency and secret scanning, mobile/web penetration tests, API abuse tests, and restore drills.
- AI: data validation, offline evaluation, subgroup analysis, shadow comparison, drift alarms, and rollback tests.

### Human validation

- Conduct iterative usability sessions with people living with dementia and caregivers; obtain ethics/legal review appropriate to the study design.
- Test Assamese copy and voice with native speakers from relevant communities.
- Validate reminder comprehension, recovery from mistakes, SOS understanding, and caregiver response expectations.
- Target WCAG 2.2 AA for the dashboard and Android accessibility requirements, including TalkBack and at least 48dp touch targets.

### Pilot stages

1. Internal dogfood using synthetic data.
2. Supervised lab usability study with no emergency reliance.
3. Small caregiver-patient pilot with parallel existing care processes.
4. Wider regional pilot after safety, reliability, privacy, and language gates pass.

No pilot participant should rely on NeuroX as the sole reminder, tracking, or emergency mechanism.

## 14. Deployment and operations

- Separate development, staging, and production projects, databases, OAuth clients, signing keys, and notification credentials.
- Use infrastructure as code, protected branches, required reviews, signed Android releases, SBOM generation, and automated deployment with rollback.
- Run database migrations as controlled release jobs, not application startup behavior.
- Define on-call ownership, severity levels, notification-provider failover, breach response, and patient/caregiver support procedures.
- Publish service status, privacy notice, retention schedule, accessibility statement, and known limitations.

## 15. Production metrics

### Patient benefit and usability

- Activity start-to-completion rate.
- Reminder acknowledgement rate without treating acknowledgement as medication consumption.
- Voice task-completion and correction rates.
- Voluntary continued use, reported frustration, and caregiver-reported usefulness.

### Reliability and safety

- Crash-free sessions, sync success/latency, queued event age, notification delivery latency, acknowledgement latency, stale-location rate, and failed escalation count.
- False and missed safe-zone alert reviews, segmented by GPS accuracy and device.

### AI quality

- Personalization acceptance/override rate, completion improvement against baseline, frustration signals, model coverage, fallback rate, drift, and subgroup performance.

Metrics are operational and supportive. None may be renamed or interpreted as a measure of dementia severity or clinical progression.

## 16. Definition of production-ready

NeuroX is production-ready for a limited, controlled release only when:

- All Phase 0 security/build blockers are closed.
- Consent, caregiver authorization, deletion, retention, and incident processes are implemented and reviewed.
- Android works reliably offline and recovers safely after reconnect, reboot, and process death.
- Real caregiver notifications and background escalation pass delivery tests.
- Voice meets language-specific thresholds or clearly falls back to touch.
- Personalization has a deterministic fallback, documented evaluation, subgroup review, monitoring, and rollback.
- Accessibility and supervised user testing pass agreed thresholds.
- No interface or model makes diagnostic, treatment, guaranteed-location, or guaranteed-response claims.

## 17. Immediate next 30 days

1. Fix role escalation, Android syntax/network configuration, and frontend TypeScript build.
2. Establish CI for backend, dashboard, and Android builds/tests.
3. Refactor FastAPI routers/services and Android MVVM boundaries without changing behavior.
4. Add secure token storage, production environment validation, and authorization-matrix tests.
5. Draft consent, retention, deletion, caregiver-assignment, and incident-response specifications.
6. Validate Pattern Completion requirements and complete its patient flow.
7. Prepare a supervised usability protocol with dementia-care and Assamese-language reviewers.

## 18. Authoritative references

- [WHO dementia fact sheet](https://www.who.int/news-room/fact-sheets/detail/dementia)
- [WHO ethics and governance of AI for health](https://www.who.int/publications/i/item/9789240029200)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [Digital Personal Data Protection Act, 2023](https://www.indiacode.nic.in/indiacode/handle/123456789/22037)
- [Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Android accessibility guidance](https://developer.android.com/guide/topics/ui/accessibility/apps)
