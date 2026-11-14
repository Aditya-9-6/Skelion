import os

try:
    import jwt
except ImportError:
    try:
        from jose import jwt
    except ImportError:
        jwt = None
import time
import requests

# Placeholder implementation for GitHub App token retrieval.
# In production, replace with real App ID and private key.


def _create_jwt(app_id: str, private_key: str) -> str:
    """Create a JWT for GitHub App authentication.
    The JWT is valid for 10 minutes.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_installation_access_token(installation_id: int) -> str:
    """Return a short‑lived installation access token (valid ~1 hour).
    Fails closed when GitHub App credentials are not configured.
    """
    app_id = os.getenv("GITHUB_APP_ID")
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
    if not app_id or not private_key or "placeholder" in private_key.lower():
        raise RuntimeError("GitHub App credentials are not configured")
    jwt_token = _create_jwt(app_id, private_key)
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    resp = requests.post(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["token"]
