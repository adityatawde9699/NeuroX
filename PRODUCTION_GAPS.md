# Production hardening: Phases 3–8

The earlier “complete for the hackathon prototype” labels describe a demo
milestone. They do not establish implementation completeness against PLAN.md.
Substantial coding work, as well as external validation, remains.

## Changes verified in this hardening pass

- Personalization now requires an affirmative latest personalization consent for
  automatic adjustment. Explicit human overrides remain available. Interrupted
  and offline timing is excluded; history is matched by content and accessibility
  mode as well as patient and activity.
- Geofence evaluation requires active sharing and a fresh, non-future location.
- Voice commands correctly distinguish reminders and all six games. Generic
  “open” commands and substrings such as “do” in “doctor” no longer launch games.
- The app now selects real Android recognition in debug as well as release.
  Leaving voice UI cancels recognition. Unimplemented remote speech adapters
  report unavailable. TTS selects the requested locale and supports shutdown.
- Sync ignores acknowledgements for unrelated IDs, retries incomplete responses,
  bounds wire retry counts, exposes failed records, and prevents a remote refresh
  overwriting the cache when queued delivery remains incomplete. Duplicate local
  event insertion fails instead of replacing immutable payloads.
- Android now captures a consent-gated foreground GPS fix using the platform
  location manager, requests coarse/fine permission, uploads it through the
  patient API, and queues it offline when the network is unavailable.
- Engagement trends use the latest 30 sessions. Reports reject reversed date
  ranges, expose truncation and generation time, and CSV includes offline and
  policy fields with spreadsheet formula protection.

## Remaining implementation work

| Phase | Remaining work before production acceptance |
| --- | --- |
| 3 | Validate process-death recovery, recurring reminder occurrence semantics, real-device notification scheduling and accessibility; obtain content review. |
| 4 | Atomic server domain mutation plus idempotency receipt, concurrent replay tests, outbox-first SOS and activities, reminder conflict/version policies, bounded queue delivery, durable local history, seven-day endurance tests. |
| 5 | Secure remote audio capture/provider integration, capability discovery per language, lifecycle/background cancellation, TTS guidance integration and caching, consented language evaluations. BHASHINI and Whisper adapters remain unavailable. |
| 6 | Background/continuous Android location policy, durable notification delivery records and retries, FCM and SMS adapters, stale-device monitoring, operator failure view, delivery measurements. The maintenance worker's default hourly cadence is insufficient for prompt escalation. |
| 7 | Per-activity persisted levels and cooldown, normalized timing, immutable recommendation lineage, override UI, consented dataset separation and deletion propagation, model evaluation/governance artifacts. |
| 8 | Consent-based invitation acceptance, acknowledgement-note persistence, authorized read-only healthcare-worker access, reminder reports, complete paginated exports, accessible PDF validation, caregiver education. |

These remaining coding items are not blocked solely by credentials. Real provider
delivery and field acceptance additionally require configuration and external
evidence. No notification, language accuracy, or production-readiness guarantee
is implied by passing local tests.
