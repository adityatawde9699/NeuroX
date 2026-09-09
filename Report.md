# Governance, Ethics & Data-Protection Report
## SIH26003 — AI-Based Cognitive Gaming & Memory Assistance Platform for Elderly Dementia Patients in North Eastern Region

---

## 1. Purpose of this Document

This report defines the governance framework required before any pilot or collection of real patient data. The repository already contains a prototype; dementia-care software carries clinical, legal, and ethical risk that a standard product-development process does not cover — a wrong reminder, a leaked location, or an unverified "safe" claim can cause real harm to a cognitively vulnerable user. Every requirement below exists to close a specific failure mode, not to satisfy a checklist.

---

## 2. Review Group

### 2.1 Composition
| Role | Why they're needed |
|---|---|
| Neurologist / geriatric clinician | Validates that game mechanics map to real cognitive domains (memory, attention, orientation) and that difficulty scaling doesn't mask genuine decline |
| Occupational therapist | Assesses whether daily-routine tasks in the app reflect realistic, safe activities of daily living |
| Dementia-care specialist | Reviews language, pacing, and escalation triggers against known dementia-stage behavior (confusion, agitation, sundowning) |
| Accessibility expert | Audits voice UI, contrast, font size, and interaction patterns against WCAG and elderly-specific usability standards |
| Caregivers (2–3, real or proxy) | Validate that the caregiver dashboard reflects what they actually need to act on, not just what's easy to display |
| People living with early-stage dementia (where ethically feasible) | The only source of truth for whether the interaction actually feels usable and dignified — proxy feedback from clinicians is not a substitute |

### 2.2 Operating Rule
No clinical-facing feature (game content, reminder logic, escalation message, or caregiver alert) ships without sign-off from at least the clinician and one caregiver representative. For a hackathon build, this group can be advisory/consulted rather than a formal board — but the sign-off checkpoint itself should still exist in the workflow.

---

## 3. Contextual Research

### 3.1 Scope
Conduct structured research in **at least two NER communities**, deliberately including at least one rural or low-connectivity household set — not just accessible urban households, since that population is the one existing solutions already fail to serve.

### 3.2 What to capture
- Language(s) actually spoken at home vs. official state language
- Literacy level and comfort with touchscreens vs. voice
- Connectivity reality (not "low network" in the abstract — actual hours/days of no signal)
- Existing caregiving arrangement (co-resident family, distant family, paid caregiver, none)
- Cultural reference points suitable for game content (festivals, food, folklore, daily routine)
- Trust barriers — willingness to have voice recorded, location tracked, or data shared with a distant relative

### 3.3 Output
A short findings document that directly feeds Section 4 (use-case definitions) and Section 5 (consent flows) — this research isn't decorative, it's the input to two other deliverables.

---

## 4. Use Case & Boundary Definition

Document the following explicitly, before writing feature code:

**4.1 Supported use cases**
- Pilot inclusion criteria only: people assessed by an appropriate clinician or referrer as having mild-to-moderate cognitive impairment, ambulatory, and able to respond verbally or via simple touch. The platform must not determine dementia stage itself.
- Presence of at least one designated caregiver (co-resident or remote) who can be escalated to

**4.2 Contraindications / out-of-scope**
- Advanced/late-stage dementia requiring full-time supervised care
- Patients with no identifiable caregiver or emergency contact
- Acute psychiatric crisis, active self-harm risk, or medical emergency — these require immediate human/clinical escalation, not app interaction

**4.3 Escalation expectations**
- Define trigger conditions (e.g., repeated distress signals, prolonged non-response, contradictory answers suggesting acute confusion) and exactly what the system does: notify caregiver, notify a designated backup contact, or — explicitly — what it does *not* do (it does not call emergency services autonomously, does not diagnose, does not give medical instructions)

**4.4 Caregiver responsibilities**
- State plainly what the caregiver is expected to do with alerts (e.g., check in within X hours) and what happens if they don't respond — this closes a real gap where "caregiver dashboard" quietly implies the platform has passed responsibility to someone who was never told they now bear it

**4.5 Failure messages**
- Every error, timeout, or "I didn't understand" moment must have a defined, calm, non-alarming message — a confused dementia patient encountering a generic error can become distressed. This needs actual scripted copy, not "handle gracefully" as a placeholder.

---

## 5. Consent & Supported-Decision Design

Because the primary user may have fluctuating capacity to consent, design **two parallel consent tracks**:

1. **Patient-facing consent** — simplified, voice-explained, revisited periodically (not a one-time click-through), covering: voice recording, location use, personalization/game data
2. **Authorized-representative consent** — for caregiver access, notification routing, and data sharing, with a clear record of who authorized what and when

**Required consent surfaces:**
- Location sharing (if used for check-in or safety features)
- Voice recording and storage (for ASR/personalization)
- Caregiver access to activity/cognitive data
- Notifications (what caregiver sees, how often, opt-out method)
- Personalization (whether game content adapts using stored behavioral data)

**Design rule:** every consent toggle must be independently revocable (see Acceptance Criteria, Section 8) — bundled all-or-nothing consent is not acceptable for a cognitively vulnerable user population.

---

## 6. DPDP Act 2023 Legal Review

Formal legal review against the Digital Personal Data Protection Act, 2023 and applicable DPDP Rules must cover:

| Area | What must be documented |
|---|---|
| Notice | Plain-language notice of what data is collected and why, provided in a form the patient/representative can actually understand (voice-explained, not just text) |
| Consent | Valid, specific, informed, and revocable consent per data category (see Section 5) |
| Access | Mechanism for patient/representative to view what data is held |
| Correction | Mechanism to correct inaccurate personal data |
| Deletion | Mechanism to request deletion, and defined system behavior on deletion (immediate vs. scheduled purge) |
| Grievance handling | A named grievance officer / redressal process, per DPDP requirements |
| Breach response | Defined notification timeline and process to the Data Protection Board and affected individuals |
| Data processors | If third parties (e.g., Bhashini, cloud hosting, SMS/voice gateway) process data, contracts must define their obligations under the Act |
| Retention | Defined retention period per data category, tied to purpose — not indefinite retention by default |
| Cross-border processing | If any vendor/service processes data outside India, confirm it's permitted under current DPDP Rules and government restrictions in effect at the time |

**Flag for the team:** this is the one section on this list that a student team cannot self-certify — it needs an actual legal review by someone qualified, even informally, before any real user data is collected beyond a hackathon demo.

**Implementation timing:** the DPDP Act and Rules have staggered commencement dates. This report is a pilot-readiness framework, not a statement that every obligation is already in force; qualified legal review must confirm the requirements applicable when the pilot begins.

---

## 7. Incident Response & Change Control

- **Incident response plan** — who is notified, within what timeframe, if patient data is exposed or a system malfunction causes harmful/incorrect guidance
- **Vulnerability disclosure process** — a defined channel (even a simple email) for security researchers or users to report issues
- **Clinical-safety review** — any change to game logic, escalation triggers, or reminder content must be reviewed against Section 4's use-case boundaries before release, not just tested for bugs
- **Change-control policy** — version-tracked changes to clinically relevant logic (escalation thresholds, medication reminder logic) with rollback capability

---

## 8. Acceptance Criteria

1. **Data field documentation** — every stored data field has a written purpose, lawful basis/consent path, retention period, and deletion behavior. No field exists "because it might be useful later."
2. **Revocability** — a patient or authorized representative can revoke caregiver access and location sharing at any time, and the system must honor this immediately, not on a delayed batch process.
3. **No overclaiming** — marketing material, in-app UI, caregiver reports, and support documentation contain **no diagnostic claims** (the platform does not diagnose dementia or its stage) and **no guaranteed-safety claims** (the platform does not guarantee it will detect every emergency or decline). This must be enforced as a content-review rule, not just a legal disclaimer buried in terms of service.

---

## 9. Practical Note for Hackathon Scope

A 36-hour build cannot fully implement all of the above — and it shouldn't claim to. The credible position for the pitch is: **"here is our governance and compliance framework, and here is what we've implemented as a proof-of-concept versus what requires a formal clinical/legal pilot phase before real deployment."** Presenting this as already-solved when it demonstrably requires a legal review (Section 6) and a real clinical board (Section 2) will read as overclaiming to any judge who checks — which is exactly the failure mode Section 8.3 exists to prevent you from committing on your own slide.
