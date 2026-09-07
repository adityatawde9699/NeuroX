# Known Limitations and Post-Hackathon Validation Needs

This document records honest constraints in the current NeuroX build.
All items below are understood and intentional given the hackathon scope.

---

## Prototype-only features

| Area | Current state | Production path |
|------|--------------|-----------------|
| **SOS / alert delivery** | Alert state is API-visible only. No SMS, WhatsApp, push, or website notification is sent. | Integrate Twilio / Firebase Cloud Messaging and configure delivery credentials. |
| **Background safety evaluation** | Safe-zone and late-return checks run only when an API request incidentally triggers them. | Add a scheduled background worker (APScheduler or Celery) that runs checks every few minutes. |
| **BHASHINI speech** | `BHASHINISpeechProvider` is wired but guarded behind an API-key check. Audio capture is mock-only. | Obtain BHASHINI API credentials and integrate real audio capture + streaming transcription. |
| **Assamese TTS** | TTS is marked `supported = false` for Assamese until the provider is confirmed. | Probe BHASHINI TTS availability at runtime and update `ttsSupported` accordingly. |
| **Google Sign-In** | `google-auth` package is installed; credential verification is implemented but end-to-end browser sign-in requires a real Google OAuth client ID in the environment. | Set `GOOGLE_CLIENT_ID` in `.env` and register the OAuth origin. |

---

## Environment and security

| Item | Status |
|------|--------|
| **Secret management** | No secrets are committed to git. The `.env.example` file documents all required variables. Actual credentials must be provided via environment variables. |
| **CORS** | Configured via `CORS_ORIGINS` environment variable. Defaults to `http://localhost:5173` for development; must be set to the production origin before deployment. |
| **JWT secret** | Reads from `JWT_SECRET` environment variable. A strong random value must be generated for production (`openssl rand -hex 32`). |
| **Password hashing** | Uses bcrypt via Passlib. No plaintext passwords are stored or logged. |
| **Logging** | Uvicorn access log is enabled. No PII (patient name, location coordinates, tokens) is written to application logs. |
| **HTTPS** | Not enforced in the FastAPI app itself. Must be terminated at the reverse proxy (nginx, Caddy) in production. |

---

## Testing coverage gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| Android end-to-end emulator tests | Medium | Compose UI tests are written; running them requires a connected device or emulator and the Android SDK toolchain. |
| BHASHINI provider integration test | Low | Skipped without API credentials; mock provider is always used in CI. |
| PostgreSQL migration smoke test | Medium | `verify_postgres.py` exists; run it against a real PostgreSQL instance before production deployment. |
| Load / performance testing | Low | Not required for hackathon; needed before public release. |

---

## Clinical and ethical limitations

- **NeuroX is not a diagnostic tool.** No output should be interpreted as a clinical assessment of cognitive state.
- **Adaptive difficulty** adjusts activity presentation based on recent engagement patterns only. It is not a validated cognitive measurement instrument.
- **Activity reports** use supportive language ("engagement trend", "activity performance") and must never be presented to users as medical data.
- **Location sharing** requires explicit patient consent and is described to users as "caregiver coordination," not surveillance.
- **SOS workflows** notify configured caregivers. They do not contact government or emergency services.

---

## Post-hackathon validation priorities

1. Clinical review of supportive-language guidelines with an occupational therapist.
2. Accessibility audit with actual elderly users (WCAG 2.1 AA compliance).
3. DPDP Act (India) compliance review for consent, data minimisation, and deletion flows.
4. Penetration test of authentication and patient-data ownership APIs.
5. End-to-end BHASHINI speech integration test with real Assamese audio samples.
6. PostgreSQL schema evolution and migration verification for production.
