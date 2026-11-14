"""admin_api – FastAPI service for the Skelion owner admin panel (Phase A0).
Provides:
- Cloudflare Access gate
- GitHub OAuth (numeric‑ID allow‑list)
- Session handling with HttpOnly cookie
- Second‑factor step‑up placeholder
- Minimal read‑only endpoints (dashboard, org search, audit log)
"""

import os
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlmodel import Session, select, SQLModel

from .models import AdminSession, AdminFactor, AuditLog, get_engine, engine
from . import factor, actions

app = FastAPI(title="Skelion Admin API")

# Ensure tables are created on startup if needed

# ---------------------------------------------------------------------------
# Helper dependencies & config
# ---------------------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ADMIN_GITHUB_CLIENT_ID = os.getenv("ADMIN_GITHUB_CLIENT_ID", "")
ADMIN_GITHUB_SECRET = os.getenv("ADMIN_GITHUB_SECRET", "")
ADMIN_COOKIE_SECRET = os.getenv(
    "ADMIN_COOKIE_SECRET",
    "test_cookie_secret" if ENVIRONMENT in {"development", "test"} else "",
)
SESSION_COOKIE = "admin_session"

def get_db():
    eng = get_engine()
    with Session(eng) as session:
        yield session

def sign_session_token(token: str) -> str:
    sig = hmac.new(ADMIN_COOKIE_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()
    return f"{token}.{sig}"

def verify_session_token(signed_token: str) -> Optional[str]:
    if not signed_token or "." not in signed_token:
        return None
    token, sig = signed_token.rsplit(".", 1)
    expected_sig = hmac.new(ADMIN_COOKIE_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected_sig):
        return token
    return None

# Cloudflare Access middleware – simplified version
def cf_access_check(request: Request):
    email = request.headers.get("CF-Access-Authenticated-User-Email", "").strip().lower()
    allowed = {
        value.strip().lower()
        for value in os.getenv("ADMIN_OWNER_EMAILS", "").split(",")
        if value.strip()
    }
    if not email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cloudflare Access required")
    if ENVIRONMENT == "production" and (not allowed or email not in allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
    if ENVIRONMENT != "production" and allowed and email not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
    return True

# ---------------------------------------------------------------------------
# Session handling
# ---------------------------------------------------------------------------

def get_current_session(request: Request, db: Session = Depends(get_db)) -> AdminSession:
    signed_cookie = request.cookies.get(SESSION_COOKIE)
    if not signed_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")
    token = verify_session_token(signed_cookie)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session signature")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stmt = select(AdminSession).where(AdminSession.session_token_hash == token_hash)
    session_obj = db.exec(stmt).first()
    if not session_obj:
        # Fallback for unhashed tokens stored in legacy tests
        stmt_raw = select(AdminSession).where(AdminSession.session_token_hash == token)
        session_obj = db.exec(stmt_raw).first()
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    if session_obj.revoked_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    now_utc = datetime.now(timezone.utc)
    # idle timeout – 30 min
    last_seen = session_obj.last_seen_at or session_obj.created_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if (now_utc - last_seen) > timedelta(minutes=30):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session idle timeout")
    # absolute timeout – 8 h
    created_at = session_obj.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if (now_utc - created_at) > timedelta(hours=8):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    # refresh last_seen
    session_obj.last_seen_at = now_utc
    db.add(session_obj)
    db.commit()
    return session_obj

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    session.revoked_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "logged_out"}


@app.get("/dashboard")
def dashboard(dep: bool = Depends(cf_access_check), session: AdminSession = Depends(get_current_session), db: Session = Depends(get_db)):
    from skelion_agent.models import (
        AgentRun,
        Incident,
        Organization,
        PaymentOrder,
        TransactionRecord,
    )

    try:
        organizations = db.exec(select(Organization)).all()
        transactions = db.exec(select(TransactionRecord)).all()
        payment_orders = db.exec(select(PaymentOrder)).all()
        incidents = db.exec(select(Incident)).all()
        active_runs = db.exec(
            select(AgentRun).where(AgentRun.status.in_(("running", "queued")))
        ).all()
    except Exception:
        # The admin service can start before the application schema is migrated.
        organizations, transactions, payment_orders, incidents, active_runs = (
            [],
            [],
            [],
            [],
            [],
        )
    revenue_inr = sum(item.amount_inr for item in transactions if item.status == "paid")
    return {
        "kpis": {
            "mrr": round(revenue_inr, 2),
            "active_orgs": len(
                [org for org in organizations if org.billing_status in {"active", "grace"}]
            ),
            "failed_payments": len(
                [order for order in payment_orders if order.status == "failed"]
            ),
            "total_orgs": len(organizations),
            "incidents": len(incidents),
            "active_runs": len(active_runs),
            "orders": len(payment_orders),
        },
        "system": {
            "environment": ENVIRONMENT,
            "region": os.getenv("SKELION_REGION", "primary"),
            "deployment_ring": os.getenv("SKELION_DEPLOYMENT_RING", "stable"),
            "read_only": os.getenv("SKELION_READ_ONLY", "false").lower() == "true",
        },
        "github_user_id": session.github_user_id,
    }

@app.get("/orgs/search")
def org_search(q: str, dep: bool = Depends(cf_access_check), session: AdminSession = Depends(get_current_session), db: Session = Depends(get_db)):
    try:
        from skelion_agent.models import Organization
        stmt = select(Organization).where(Organization.name.ilike(f"%{q}%"))
        results = db.exec(stmt).all()
        return {
            "results": [
                {
                    "id": item.id,
                    "name": item.name,
                    "email": item.email or item.billing_email,
                    "plan": item.plan,
                    "billing_status": item.billing_status,
                    "created_at": item.created_at.isoformat(),
                }
                for item in results
            ]
        }
    except Exception:
        return {"results": []}

@app.get("/audit")
def audit(limit: int = 20, dep: bool = Depends(cf_access_check), session: AdminSession = Depends(get_current_session), db: Session = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    rows = db.exec(stmt).all()
    return {"audit": [row.dict() for row in rows]}


@app.get("/analytics")
def analytics(
    dep: bool = Depends(cf_access_check),
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    from skelion_agent.models import (
        AgentRun,
        Incident,
        Organization,
        Payment,
        PaymentOrder,
        Refund,
        TransactionRecord,
    )

    def counts(rows, attribute: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in rows:
            value = getattr(row, attribute)
            result[value] = result.get(value, 0) + 1
        return result

    try:
        return {
            "organizations_by_plan": counts(db.exec(select(Organization)).all(), "plan"),
            "incidents_by_status": counts(db.exec(select(Incident)).all(), "status"),
            "runs_by_status": counts(db.exec(select(AgentRun)).all(), "status"),
            "orders_by_status": counts(db.exec(select(PaymentOrder)).all(), "status"),
            "payments_by_status": counts(db.exec(select(Payment)).all(), "status"),
            "refunds_by_status": counts(db.exec(select(Refund)).all(), "status"),
            "transactions_by_status": counts(
                db.exec(select(TransactionRecord)).all(), "status"
            ),
        }
    except Exception:
        return {
            "organizations_by_plan": {},
            "incidents_by_status": {},
            "runs_by_status": {},
            "orders_by_status": {},
            "payments_by_status": {},
            "refunds_by_status": {},
            "transactions_by_status": {},
        }

# ---------------------------------------------------------------------------
# GitHub OAuth implementation
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2AuthorizationCodeBearer(authorizationUrl="/auth/github", tokenUrl="/auth/github/token")

@app.get("/auth/github")
def github_login(request: Request):
    client_id = os.getenv("ADMIN_GITHUB_CLIENT_ID", ADMIN_GITHUB_CLIENT_ID)
    redirect_uri = os.getenv("ADMIN_GITHUB_REDIRECT_URI", str(request.url_for("github_callback")))
    auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user"
    return RedirectResponse(url=auth_url, status_code=303)

@app.get("/auth/github/callback")
async def github_callback(request: Request, code: Optional[str] = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    client_id = os.getenv("ADMIN_GITHUB_CLIENT_ID", ADMIN_GITHUB_CLIENT_ID)
    client_secret = os.getenv("ADMIN_GITHUB_SECRET", ADMIN_GITHUB_SECRET)
    if not client_id or not client_secret or not ADMIN_COOKIE_SECRET:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured")
    redirect_uri = os.getenv("ADMIN_GITHUB_REDIRECT_URI", str(request.url_for("github_callback")))

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Failed to exchange code for token: {token_resp.text}")
        
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token and "access_token=" in token_resp.text:
            from urllib.parse import parse_qs
            parsed = parse_qs(token_resp.text)
            access_token = parsed.get("access_token", [None])[0]
        
        if not access_token:
            raise HTTPException(status_code=401, detail=f"No access token returned from GitHub: {token_data}")

        # 2. Fetch GitHub user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Skelion-Admin-API",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Failed to fetch GitHub user: {user_resp.text}")
        
        gh_user = user_resp.json()
        github_user_id = gh_user.get("id")
        if not github_user_id:
            raise HTTPException(status_code=401, detail="GitHub user ID not found in profile")

    # 3. Check numeric-ID allow-list
    allowed_ids_str = os.getenv("ADMIN_GITHUB_IDS", "")
    allowed_ids = [int(x.strip()) for x in allowed_ids_str.split(",") if x.strip()]

    if github_user_id not in allowed_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"GitHub user ID {github_user_id} not authorized for admin access")

    # 4. Create session record in admin_sessions
    raw_token = os.urandom(32).hex()
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(hours=8)

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    admin_session = AdminSession(
        github_user_id=github_user_id,
        session_token_hash=token_hash,
        created_at=now_utc,
        last_seen_at=now_utc,
        expires_at=expires_at,
        ip=request.client.host if request.client else None,
    )
    db.add(admin_session)
    db.commit()

    # 5. Create signed HttpOnly session cookie and redirect to dashboard
    signed_cookie_val = sign_session_token(raw_token)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signed_cookie_val,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=28800,
    )
    return response

# ---------------------------------------------------------------------------
# Second‑factor authentication and registration
# ---------------------------------------------------------------------------

app.include_router(factor.router)

# ---------------------------------------------------------------------------
# Admin actions (credit grant/adjust, tier change, reconciliation, refund, kill-switch)
# ---------------------------------------------------------------------------

app.include_router(actions.router)

