from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.ai.personalization.adaptive_difficulty import PerformanceInput, recommend_difficulty
from app.auth import REFRESH_TOKEN_EXPIRE_DAYS, create_access_token, create_refresh_token, decode_access_token, hash_password, verify_password
from app.database import Base, engine, get_db
from app.models import RefreshSession, User
from app.schemas import ActivityCompletion, AuthResponse, GoogleLoginRequest, LoginRequest, RefreshRequest, RegisterRequest, Role
from app.services.google_auth import verify_google_credential

app = FastAPI(title="NeuroX API", version="0.3.0", description="Supportive engagement APIs — not clinical diagnosis.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
ACTIVITIES = [{"id":"memory-match","title":"Memory Match","description":"Match two familiar objects.","difficulty":2},{"id":"object-recall","title":"Remember the Objects","description":"Look, listen, then remember.","difficulty":2},{"id":"pattern","title":"Pattern Completion","description":"Choose what comes next.","difficulty":2}]

@app.on_event("startup")
def initialise_database():
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        if not db.query(User).filter(User.email == "anita@neurox.demo").first():
            db.add(User(id="caregiver-anita", name="Anita Devi", email="anita@neurox.demo", role=Role.CAREGIVER.value, password_hash=hash_password("NeuroXDemo!2026")))
            db.commit()

def public_user(user: User) -> dict: return {"id":user.id,"name":user.name,"email":user.email,"role":user.role}
def session_for(user: User, db: Session) -> AuthResponse:
    session_id = str(uuid4())
    db.add(RefreshSession(id=session_id, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)))
    db.commit()
    return AuthResponse(access_token=create_access_token(user), refresh_token=create_refresh_token(user, session_id), user=public_user(user))
def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(status_code=401, detail="Sign in is required.")
    payload = decode_access_token(authorization.removeprefix("Bearer "))
    if payload.get("type") != "access": raise HTTPException(status_code=401, detail="An access token is required.")
    user = db.get(User, payload["sub"])
    if not user: raise HTTPException(status_code=401, detail="Account not found.")
    return user
def caregiver_only(user: User = Depends(current_user)) -> User:
    if user.role not in {Role.CAREGIVER.value, Role.ADMIN.value}: raise HTTPException(status_code=403, detail="Caregiver access is required.")
    return user

@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    if db.query(User).filter(User.email == email).first(): raise HTTPException(status_code=409, detail="An account already exists for this email.")
    user = User(name=request.name.strip(), email=email, role=request.role.value, password_hash=hash_password(request.password)); db.add(user); db.commit(); db.refresh(user)
    return session_for(user, db)
@app.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.strip().lower()).first()
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash): raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return session_for(user, db)
@app.post("/auth/google", response_model=AuthResponse)
def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    identity = verify_google_credential(request.credential)
    user = db.query(User).filter(User.email == identity["email"]).first()
    if not user:
        user = User(name=identity["name"], email=identity["email"], role=Role.CAREGIVER.value, google_subject=identity["google_subject"]); db.add(user); db.commit(); db.refresh(user)
    elif user.google_subject not in {None, identity["google_subject"]}: raise HTTPException(status_code=409, detail="This email is linked to another Google account.")
    elif not user.google_subject: user.google_subject = identity["google_subject"]; db.commit()
    return session_for(user, db)
@app.post("/auth/refresh", response_model=AuthResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(request.refresh_token)
    if payload.get("type") != "refresh": raise HTTPException(status_code=401, detail="A refresh token is required.")
    token_session = db.get(RefreshSession, payload.get("sid"))
    if not token_session or token_session.revoked or token_session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc): raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    user = db.get(User, token_session.user_id)
    token_session.revoked = True; db.commit()
    return session_for(user, db)
@app.get("/auth/me")
def me(user: User = Depends(current_user)): return public_user(user)
@app.get("/patients/{patient_id}")
def patient(patient_id: str, _: User = Depends(caregiver_only)): return {"id":patient_id,"name":"Maya Devi","age":72,"preferredLanguage":"Assamese","caregiver":"Anita Devi"}
@app.get("/activities")
def activities(_: User = Depends(current_user)): return ACTIVITIES
@app.post("/activities/{activity_id}/complete")
def complete_activity(activity_id: str, session: ActivityCompletion, _: User = Depends(current_user)):
    next_level, score = recommend_difficulty(PerformanceInput(session.accuracy, session.response_time, 1 if session.completion_status == "completed" else 0, session.difficulty_level)); return {"saved":True,"event_id":session.event_id,"next_difficulty":next_level,"performance_score":score,"message":"Your next activity is adjusted to your performance."}
@app.get("/patients/{patient_id}/performance")
def performance(patient_id: str, _: User = Depends(caregiver_only)): return {"patientId":patient_id,"note":"Supportive activity performance, not a medical assessment.","accuracy":.80,"responseTime":4.2,"difficulty":2,"completion":[80,100,80,90]}
@app.get("/patients/{patient_id}/safety")
def safety(patient_id: str, _: User = Depends(caregiver_only)): return {"status":"At Home • Safe","gpsAccuracy":"±18 m","lastUpdated":"2 minutes ago","expectedReturn":"6:00 PM","connection":"Online"}
@app.post("/sync/events")
def sync(events: list[dict], _: User = Depends(current_user)): return {"accepted":[event.get("event_id") for event in events],"syncedAt":datetime.now(timezone.utc)}
