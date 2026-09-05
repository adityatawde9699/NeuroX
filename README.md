# NeuroX

NeuroX is a voice-first cognitive support prototype for older adults living with dementia in North East India. It provides cognitive engagement, daily reminders, caregiver visibility, and safety support while respecting regional-language needs and intermittent connectivity.

> NeuroX provides supportive engagement insights only. It does not diagnose, predict, or treat dementia or any other medical condition.

## What is included

| Area | Current MVP capability |
| --- | --- |
| Patient Android app | Elder-friendly Jetpack Compose home screen, persistent navigation, large voice/activity/reminder/safety controls |
| Caregiver dashboard | Responsive React dashboard, caregiver sign-in, activity overview, alerts, safe-zone preview, and location status |
| Backend | FastAPI APIs, JWT role authorization, local/password accounts, Google Identity sign-in, refresh-token rotation, demo data |
| Personalization | Deterministic activity difficulty adjustment based on completion, accuracy, and response time |
| Persistence | SQLAlchemy models with PostgreSQL configuration and SQLite local-development fallback |

## Architecture

```text
Android patient app ──┐
                     ├── FastAPI ── PostgreSQL
Caregiver dashboard ──┘      │
                             ├── authentication and role checks
                             └── supportive activity personalization
```

## Repository layout

```text
android/NeuroX/              Jetpack Compose patient application
backend/app/                 FastAPI application
  ai/personalization/        Adaptive difficulty service
  services/                  External-service adapters (Google Identity)
web/caregiver-dashboard/     React + TypeScript caregiver application
docker-compose.yml           Local PostgreSQL service
.env.example                 Required environment variables
```

## Quick start

### 1. Configure environment

Copy `.env.example` values into your shell or a private `.env` file. Never commit real secrets.

For local development, SQLite is used when `DATABASE_URL` is omitted. To use PostgreSQL:

```bash
docker compose up -d db
export DATABASE_URL='postgresql+psycopg://neurox:neurox@localhost:5432/neurox'
export JWT_SECRET='replace-this-with-a-long-random-secret'
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. On first startup, the API creates database tables and the demo caregiver account:

```text
Email:    anita@neurox.demo
Password: NeuroXDemo!2026
```

### 3. Start the caregiver dashboard

```bash
cd web/caregiver-dashboard
npm install
npm run dev
```

Open `http://localhost:5173`.

### 4. Android app

Open `android/NeuroX` in a current stable Android Studio, allow Gradle sync, then run on an Android emulator or device with API 26+.

## Authentication

NeuroX supports email/password accounts and Google Identity Services for caregivers. Passwords are bcrypt-hashed; the backend creates short-lived access tokens plus rotating refresh tokens. Caregiver-only APIs require a valid JWT with an allowed role.

### Google sign-in setup

1. In Google Cloud Console, create an OAuth 2.0 **Web application** client.
2. Add `http://localhost:5173` to **Authorized JavaScript origins**.
3. Set the same client ID in both variables:

```bash
GOOGLE_OAUTH_CLIENT_ID='...apps.googleusercontent.com'
VITE_GOOGLE_CLIENT_ID='...apps.googleusercontent.com'
```

The dashboard sends Google’s ID credential to FastAPI. The backend verifies its signature, issuer, verified email, and configured client ID before issuing a NeuroX session. Do not place client secrets in the dashboard.

## Key API routes

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create a NeuroX account |
| POST | `/auth/login` | Email/password sign-in |
| POST | `/auth/google` | Exchange verified Google credential for NeuroX tokens |
| POST | `/auth/refresh` | Rotate a refresh token |
| GET | `/auth/me` | Current authenticated user |
| GET | `/activities` | Available supportive activities |
| GET | `/patients/{id}/performance` | Activity-performance trend, not a clinical assessment |
| GET | `/patients/{id}/safety` | Current reported safety state |

## Validation

```bash
cd web/caregiver-dashboard && npm run build
cd ../../backend && python -m compileall -q app
```

## Product limitations

- Location is last-known-location information and depends on permission, device availability, GPS accuracy, and network connectivity.
- SOS is a caregiver notification workflow in this prototype, not an emergency-service integration.
- Speech recognition support varies by regional language and provider.
- NeuroX must not be used for clinical decision-making or emergency response.

## License

Released under the [MIT License](LICENSE). Copyright © 2026 NeuroX Team.
