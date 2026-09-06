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

### 1. Install prerequisites

Install Git, Python 3.11+, Node.js 20+, npm, and Docker Desktop (optional, only required for PostgreSQL). Android development additionally requires Android Studio.

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nodejs npm docker.io docker-compose-plugin
git clone https://github.com/adityatawde9699/NeuroX.git
cd NeuroX
```

#### macOS

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git python node
brew install --cask docker
git clone https://github.com/adityatawde9699/NeuroX.git
cd NeuroX
```

#### Windows (PowerShell)

Install Git, Python, Node.js, and Docker Desktop from their official installers, or use `winget`:

```powershell
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS Docker.DockerDesktop
git clone https://github.com/adityatawde9699/NeuroX.git
Set-Location NeuroX
```

### 2. Configure environment and database

Copy `.env.example` values into your shell or a private `.env` file. Never commit real secrets. SQLite is used when `DATABASE_URL` is omitted. To use PostgreSQL, run:

Linux/macOS:

```bash
docker compose up -d db
export DATABASE_URL='postgresql+psycopg://neurox:neurox@localhost:5432/neurox'
export JWT_SECRET='replace-this-with-a-long-random-secret'
```

Windows PowerShell:

```powershell
docker compose up -d db
$env:DATABASE_URL = 'postgresql+psycopg://neurox:neurox@localhost:5432/neurox'
$env:JWT_SECRET = 'replace-this-with-a-long-random-secret'
```

### 3. Start the backend

Linux/macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. On first startup, the API creates database tables and the demo caregiver account:

```text
Email:    anita@neurox.demo
Password: NeuroXDemo!2026
```

### 4. Start the caregiver dashboard

Linux/macOS:

```bash
cd web/caregiver-dashboard
npm install
npm run dev
```

Windows PowerShell:

```powershell
Set-Location web\caregiver-dashboard
npm install
npm run dev
```

Open `http://localhost:5173`.

### 5. Android app

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
| GET | `/patients/me` | Authenticated patient profile |
| GET | `/patients/{id}/reminders` | Assigned patient reminders |
| PUT | `/reminders/{id}` | Update reminder state |
| GET | `/patients/{id}/emergency-contacts` | Assigned patient emergency contacts |
| GET | `/caregivers/me/patients` | Patients assigned to the caregiver |
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
