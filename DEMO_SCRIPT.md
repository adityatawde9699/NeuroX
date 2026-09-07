# NeuroX — One-Minute Demo Script

**Occasion:** Smart India Hackathon 2026  
**Fictional data:** Maya Devi (patient, 72, Assamese) · Anita Devi (caregiver)  
**No external AI service required.** All demo data is seeded automatically on first startup.

---

## Setup (before presenting)

```bash
# 1. Start the backend
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload          # seeds Maya Devi + Anita Devi automatically

# 2. Start the dashboard
cd ../web/caregiver-dashboard
npm install && npm run dev             # opens http://localhost:5173
```

Sign in as **Anita Devi** using:  
- Email: `anita@neurox.demo`  
- Password: `NeuroXDemo!2026`

---

## Presenter Script (~60 seconds)

### 0 – 10 s  |  The problem
> "India has over 5 crore people living with dementia. Their caregivers need a simple, regional-language tool to stay connected — not a clinical dashboard full of numbers."

### 10 – 25 s  |  Caregiver dashboard
> "Anita logs in and immediately sees Maya's status — her safe zone, expected return time, and engagement trend — all in one glance. No medical jargon."
- *Point to the stats row and the patient panel.*

### 25 – 40 s  |  Alert with severity + escalation
> "When Maya steps outside the safe zone, an alert appears with a severity badge and priority level. Anita acknowledges it in one tap and the state updates instantly."
- *Navigate to Alerts, click Acknowledge.*

### 40 – 50 s  |  Activity report
> "The activity report shows Maya's completion rate, average engagement, and how her difficulty level adapted over the week — all described supportively, never as a score."
- *Navigate to Reports, show summary cards and trend line.*

### 50 – 60 s  |  Offline-first patient app
> "Maya's Android app works even without internet. Activities and reminders load from local cache, and any data syncs automatically when connectivity returns."
- *Show the Android emulator on the Activities screen.*

---

## Key Talking Points

| Feature | Message |
|---|---|
| Adaptive difficulty | "The next activity is gently adjusted to Maya's recent performance." |
| Safe-zone alert | "Caregivers are notified, not emergency services." |
| SOS workflow | "A caregiver workflow — not direct government integration." |
| Language support | "Assamese-first, with transparent fallback when TTS is unavailable." |
| Offline sync | "Maya's app keeps working; Anita's dashboard catches up automatically." |

---

## Reset between demos

```bash
# Delete the SQLite database so seed data runs fresh
del backend\neurox-session-*.sqlite3 2>nul
# Or set a new path:
set DATABASE_URL=sqlite:///./neurox-demo-fresh.db
uvicorn app.main:app --reload
```

---

*NeuroX is a supportive engagement platform, not a diagnostic or emergency-response system.*
