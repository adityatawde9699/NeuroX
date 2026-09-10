# Phase 9 verification record — hackathon prototype

Verified locally on 10 September 2026:

- Backend: `PYTHONPATH=. .venv/bin/pytest -q` — 149 tests passed.
- Android: `:app:testDebugUnitTest`, debug APK, and unsigned release APK built
  successfully with JDK 17.
- Release APK scan: no demo credentials, development URLs, token literals, or
  unsafe manifest settings were found.
- Caregiver dashboard: TypeScript check passed, 44 Vitest tests passed, and
  the production Vite bundle built successfully.

## Demonstration boundary

This record verifies source code and local builds for a hackathon demonstration.
It is not evidence of clinical effectiveness, notification delivery reliability,
accessibility acceptance, language accuracy, penetration-test completion, or
pilot readiness. No participant may rely on NeuroX as their only reminder,
tracking, or emergency mechanism.

## Required before a real pilot or release

- Obtain appropriate ethics, legal/privacy, clinical-safety, and community
  language review.
- Run supervised usability and accessibility sessions with intended patients and
  caregivers, including Assamese voice/copy validation.
- Test real-device GPS, microphone, notifications, offline recovery, reboot,
  and low-battery behavior.
- Configure and measure real caregiver notification delivery and escalation.
- Complete staging/production separation, signing, secrets, monitoring,
  incident response, restore drills, dependency/security scans, and a scoped
  penetration test.
