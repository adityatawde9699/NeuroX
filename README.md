# NeuroX

NeuroX is a voice-first cognitive support prototype for older adults living with dementia in North East India. It provides cognitive engagement, daily reminders, caregiver visibility, and safety support while respecting regional-language needs and intermittent connectivity.

> NeuroX provides supportive engagement insights only. It does not diagnose, predict, or treat dementia or any other medical condition.

## What is included

| Area | Current MVP capability |
| --- | --- |
| Patient Android app | Elder-friendly Jetpack Compose home screen, persistent navigation, large voice/activity/reminder/safety controls; offline-first Room cache and WorkManager sync |
| Caregiver dashboard | Modular React dashboard with patient list, profile, activities, alerts (severity + escalation priority), location history, reports, and settings routes |
| Backend | FastAPI APIs, JWT role authorization, caregiver-patient ownership enforcement, local/password accounts, Google Identity sign-in, refresh-token rotation and revocation, demo data |
| Personalization | Deterministic activity difficulty adjustment based on recent completion, accuracy, and response time history |
| Persistence | SQLAlchemy models with PostgreSQL configuration and SQLite local-development fallback; Alembic migrations |
| Tests | Backend pytest suite (auth, sync, safety, adaptive difficulty, smoke); web Vitest component suite (Alerts, Reports, Patients pages); Android Compose UI tests |

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
  services/                  Auth, patients, reminders, activities, reports, safety, sync, alerts
  routers/                   HTTP bindings for each domain
  access.py                  Shared role and assignment authorization
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

Open `android/NeuroX` in Android Studio with JDK 17, allow Gradle sync, then run
on an Android emulator or device with API 26+. First launch asks for the server
address and patient email/password. Debug builds suggest `http://10.0.2.2:8000/`
for the emulator; on a physical device enter the development machine's LAN
address. Release builds start with an empty server field and require HTTPS.

For local demo testing, enter `maya@neurox.demo` / `NeuroXDemo!2026` manually.
Patient sign-in requires a provisioned patient profile; public registration
alone does not create one. The app retains its patient/server binding across
session expiry to protect offline records. It does not support switching
patients or servers on an existing installation. Prototype upgrades require
sign-in again; if the binding cannot be recovered, cached/queued records need
supervised recovery before reconnecting. Do not clear application data to bypass
that guard if unsynced records need to be preserved.

## Authentication

NeuroX supports email/password accounts and Google Identity Services for caregivers.
Passwords are bcrypt-hashed. Native clients use the `/auth/login`, `/auth/refresh`,
and `/auth/logout` token APIs. Android encrypts its session using an Android
Keystore key and refreshes expired access tokens during requests and background sync.

The dashboard uses `/auth/browser/login`, `/auth/browser/google`,
`/auth/browser/refresh`, and `/auth/browser/logout`. Refresh tokens are kept in
an HttpOnly, SameSite=Strict cookie, marked Secure outside development. Access
tokens and user data stay in memory; old localStorage session entries are removed.
Reloading restores the session through the cookie. Browser session endpoints
require an exact allowed Origin, including login/logout. Native token endpoints
remain compatible with existing clients.

Deploy the API at the host root and serve the dashboard/API on the same site
(for example `care.example.com` and `api.example.com`), both over HTTPS. The
cookie path is `/auth/browser`; a cross-site deployment or API path-prefix proxy
needs a reviewed cookie/proxy configuration. Configure `CORS_ORIGINS` with the
exact dashboard origin. `APP_ENV=staging` or `production` requires PostgreSQL,
explicit HTTPS origins, and a non-placeholder JWT secret of at least 32 characters.
Those environments neither create tables nor seed demo accounts at startup;
run Alembic migrations before starting the service.

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

Android patient screens observe `PatientViewModel` through StateFlow. The
`PatientRepository` interface permits offline and failure-path tests without a
device or live server. `PatientScreens.kt` contains presentation components;
`MainActivity.kt` handles startup and navigation. Game progress recovery after
process death and device workflow validation remain outstanding.

`PatientDependencies` wires encrypted sessions, `PatientLocalDataSource` (Room),
`PatientRemoteDataSource` (Retrofit), and `NeuroXRepository`. Patient mutation
use cases live in `PatientUseCases.kt`; the ViewModel owns observable UI state.
Backend `main.py` is now only application composition. Notification services
expose the existing alert feed; this refactor does not add push/SMS delivery.

GitHub Actions runs backend tests, dashboard tests/build, PostgreSQL migration
upgrade/rollback on a disposable database, and Android debug/release compilation, unit
tests, lint, and instrumentation-test compilation. The Android job uploads a
debug APK; device/emulator tests still need to be run separately.
Security gates include Ruff, Bandit, pip-audit, npm audit, OSV scanning of the
resolved Android release graph, and release credential/manifest checks.
These checks have passed locally; remote CI must pass before Phase 0 is accepted.

## Phase 1 privacy controls

Patients can turn location sharing on or off, record or withdraw purpose-specific
consent, revoke a caregiver's access immediately, download their data, and submit
a deletion request. These controls are available through the patient privacy API
and the patient web safety screen. A deletion request is deliberately not an
automatic erasure: retention and legal-review rules must be approved before any
irreversible deletion workflow is enabled.

Use JDK 17 for the Android Gradle build. HTTP access to the emulator's local
backend is permitted only in debug builds; release builds reject cleartext
traffic. The Android setup/sign-in flow and encrypted session storage are
implemented; the broader production gates in `PLAN.md` remain open.

### Backend tests

```bash
cd backend
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

### Web dashboard tests

```bash
cd web/caregiver-dashboard
npm install
npm run test          # runs Vitest in CI mode
npm run build         # verifies TypeScript compiles and Vite bundles
```

### Android build and UI tests

```bash
cd android/NeuroX
# Build debug APK (requires Android SDK)
./gradlew assembleDebug
# Run Compose UI tests on a connected device or emulator
./gradlew connectedAndroidTest
```

### Schema migrations

```bash
cd backend
alembic upgrade head
```

For destructive upgrade/rollback verification, use an **empty disposable**
PostgreSQL database, never the application database:

```bash
POSTGRES_URL=postgresql+psycopg://user:password@localhost/neurox_migration_test python tests/verify_postgres.py
```

The verifier refuses nonempty databases and overrides `DATABASE_URL` explicitly.
PostgreSQL 18.6 has passed locally; CI verifies PostgreSQL 16. Revision 001 is now
frozen instead of importing current models. Existing databases created by the
old prototype's `create_all` need schema inspection before stamping or applying
migrations; do not use this disposable-database verifier to repair them.

### Security checks

```bash
cd backend
python -m pip install -r requirements-security.txt
ruff check app --select F
bandit -r app
pip-audit
```

From `android/NeuroX`, run `./gradlew exportReleaseDependencies`, then
`python ../../scripts/check_android_dependencies.py app/build/reports/release-dependencies.json`.
The advisory check requires network access and fails on lookup errors or any
reported vulnerability. See `.github/workflows/ci.yml` for the complete gates.

## Demo

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the one-minute Smart India Hackathon demo flow using fictional data (Maya Devi and Anita Devi).

## Product limitations

See [LIMITATIONS.md](LIMITATIONS.md) for a full list of known constraints, prototype-only features, and post-hackathon validation priorities.

- Location is last-known-location information and depends on permission, device availability, GPS accuracy, and network connectivity.
- SOS is a caregiver notification workflow in this prototype, not an emergency-service integration.
- Speech recognition support varies by regional language and provider.
- NeuroX must not be used for clinical decision-making or emergency response.

## License

Released under the [MIT License](LICENSE). Copyright © 2026 NeuroX Team.
