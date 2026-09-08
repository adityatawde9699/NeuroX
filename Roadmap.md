# AI/ML & Cognitive Games Plan — NeuroX

Scope: the personalization/ML layer and game catalog only, under Plan A (Android patient app stays native; caregiver dashboard + backend go live as the web-facing pieces). Extends `PLAN.md` and `LIMITATIONS.md` rather than replacing them.

Current as of September 8, 2026.

## 1. Current state (baseline)

- Personalization is **not ML**. `adaptive_difficulty.py` is a deterministic formula: `score = 0.6×accuracy + 0.2×response_time + 0.2×completion_rate`, difficulty moves up/down/stays on two fixed thresholds. No training, no model file, no inference.
- 3 activities are listed in the catalog; only 2 are actually playable. **Pattern Completion has no implemented screen** — it's a stub entry.
- BHASHINI is integrated at the API layer but speech capture/recognition is currently mocked.
- No trained model — on-device or server-side — exists anywhere in the codebase today.

## 2. AI/ML plan

### Online (backend, connected)

| Component | Approach | Notes |
|---|---|---|
| Activity/difficulty personalization | Contextual bandit — Thompson Sampling, Beta-Bernoulli per (activity × difficulty) arm | Replaces the linear formula. Learns from live session feedback with no upfront training set. ~40 lines server-side (`numpy.random.beta` does the core work), or use `mabwiser` for a packaged library. |
| Cognitive-decline prediction / diagnostic scoring | **Explicitly out of scope** | Demo-scale data, no clinical validation, and it contradicts the product's own "supportive engagement only, never a diagnosis" framing. Not defensible if a judge or reviewer asks how it was validated. |
| Speech (ASR + TTS) | BHASHINI | Already the right choice — covers Assamese and other NER languages at the platform level. Work remaining is finishing the integration (currently mocked), not picking a different service. |
| Caregiver performance trend | Simple rolling average / trend line, not a model | Interpretability matters more than sophistication here — it's meant to be a conversation-starter for a caregiver, not an algorithmic verdict. |

### Offline (on-device — must run on minimal-hardware Android phones)

Hardware assumption: entry-level/older Android devices common in the target region — as little as ~2GB RAM, no guaranteed GPU/NPU, limited storage, extended stretches with no connectivity. Every offline component below is sized against that, not a flagship device.

| Component | Approach | Hardware footprint |
|---|---|---|
| Activity/difficulty personalization | Same bandit, running as plain Kotlin arithmetic on a handful of float parameters (Beta α/β counters) stored in the existing Room database; synced via the existing WorkManager queue when connectivity returns | Negligible — a few KB, no ML runtime needed at all |
| On-device model *file* (optional, demo value only) | Package the same bandit (or a small logistic model) as a `.tflite` file via **LiteRT** — Google's current on-device runtime, the rebranded TensorFlow Lite (`com.google.ai.edge.litert`) | Still KB-scale; CPU-only inference is instant at this size. Buys "on-device ML" as a talking point, not additional capability over the plain-Kotlin version — don't spend real time on this unless the demo specifically needs it |
| Offline speech recognition | **Not recommended right now** | Vosk (the standard offline Android ASR toolkit) ships ~50MB per-language models and needs continuous CPU decoding — workable on budget hardware, but has no model for any North-East regional language today, only Hindi/Indian English. Heavier general options (quantized Whisper-tiny, Meta MMS subsets) run 100–400MB+ with noticeably higher CPU/battery draw — a real problem on 2GB-RAM devices — and still have no ready-made model for most NER languages regardless of size |
| Offline voice fallback | Text/icon-based input, explicit "voice needs internet" UI state | Stated plainly in the product rather than silently failing. Voice stays connectivity-gated until a low-resource NER speech model exists that's both accurate and small enough for entry-level hardware — that's a research gap, not a library-integration gap |

**General offline hardware guardrails:** no offline task should hold more than a few MB of model/dataset in memory at once; if any offline background inference is ever added, gate it so it doesn't run concurrently with the safety/location background job against the same limited CPU/battery budget.

## 3. Cognitive games — current and planned

### Currently implemented

| Game | Cognitive domain | Status |
|---|---|---|
| Memory Match | Visual recognition memory | Built and playable |
| Object Recall | Visual/associative memory | Built and playable |
| Pattern Completion | Non-verbal reasoning | In the catalog, no screen implemented — not actually playable |

### Planned additions (each fills a domain not yet covered)

| Game | Cognitive domain | Notes |
|---|---|---|
| Finish Pattern Completion | Non-verbal reasoning | Highest priority — already promised in the catalog/API, currently missing |
| Orientation prompt | Orientation (time of day / season / place) | Familiar regional photo as the cue; this is typically the domain that erodes earliest in dementia and isn't covered at all yet |
| Naming/categorization | Language / word-finding | Regionally familiar objects or foods, spoken response — the natural showcase for the BHASHINI voice feature once it's real |
| Daily-routine sequencing | Executive function / sequencing | Order the steps of a familiar routine (making tea, getting dressed); source the routines regionally rather than using generic examples |

### Design constraints (apply to every game, existing and new)

- No "wrong answer" framing — always a supportive redirection, never a failure state.
- Content and cues sourced regionally (NER-specific objects, food, routines, imagery), not generic defaults.
- Large touch targets, low-literacy-friendly UI, consistent with the rest of the patient app.
- No game result is ever surfaced to caregivers as a clinical or diagnostic signal — only as a supportive engagement trend.

## 4. Next tasks (this layer)

1. Implement the Pattern Completion screen — closes an already-promised, currently-missing game.
2. Replace the linear formula in `adaptive_difficulty.py` with the Thompson Sampling bandit; keep the old formula available for comparison during testing.
3. Finish the real BHASHINI integration (ASR + TTS) — currently mocked.
4. Build the explicit offline voice-fallback UI state, rather than a silent failure.
5. Build the Orientation, Naming/Categorization, and Sequencing games, each localized with NER-relevant content.
6. Add a low-end-device test pass (e.g., a 2GB-RAM / older Android API emulator profile) covering offline personalization sync and any on-device model file, before treating "offline" as done.

## 5. Known limitations (this layer)

- No cognitive-decline prediction or diagnostic scoring exists or is planned — by design, not omission.
- No offline speech recognition exists for any North-East regional language; current offline ASR options (Vosk and equivalents) only cover Hindi/Indian English.
- The bandit's exploration behavior is unvalidated against real patients — needs monitoring once live, since a poorly-tuned bandit could plateau a patient at a difficulty that's too easy or too hard.
- Regional game content (photos, food items, routine steps) doesn't exist yet and needs to be sourced/localized per NER community before the new games can ship — this is content work, not engineering work, and can run in parallel with the code above.