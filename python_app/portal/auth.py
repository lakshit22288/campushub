import base64
import hashlib
import logging
import secrets
import time
from urllib.parse import urlencode

import bcrypt
import httpx
from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)


class SupabaseAuthError(Exception):
    pass


def _supabase_config():
    url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
    key = getattr(settings, "SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise SupabaseAuthError("Google sign-in is not configured for the Python app.")
    return url, key


def begin_google_oauth(request):
    supabase_url, _ = _supabase_config()
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    callback_path = reverse("google_callback")
    callback = f"{settings.DJANGO_PUBLIC_URL}{callback_path}" if settings.DJANGO_PUBLIC_URL else request.build_absolute_uri(callback_path)
    request.session["google_pkce_verifier"] = verifier
    request.session["google_started_at"] = int(time.time())
    request.session.set_expiry(600)
    authorize_url = f"{supabase_url}/auth/v1/authorize?" + urlencode(
        {
            "provider": "google",
            "redirect_to": callback,
            "code_challenge": challenge,
            "code_challenge_method": "s256",
        }
    )
    return authorize_url


def _auth_headers(api_key, access_token=None):
    headers = {"apikey": api_key, "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def exchange_google_code(request, code):
    supabase_url, api_key = _supabase_config()
    verifier = request.session.pop("google_pkce_verifier", None)
    started_at = request.session.pop("google_started_at", 0)
    if not verifier or not started_at or int(time.time()) - started_at > 600:
        raise SupabaseAuthError("Google sign-in expired. Please start again.")

    try:
        with httpx.Client(timeout=12) as client:
            token_response = client.post(
                f"{supabase_url}/auth/v1/token",
                params={"grant_type": "pkce"},
                headers=_auth_headers(api_key),
                json={"auth_code": code, "code_verifier": verifier},
            )
            if token_response.status_code != 200:
                raise SupabaseAuthError("Google sign-in could not be completed. Please try again.")
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise SupabaseAuthError("Google did not return a valid sign-in session.")
            user_response = client.get(
                f"{supabase_url}/auth/v1/user",
                headers=_auth_headers(api_key, access_token),
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out during Google OAuth exchange: %s", error)
        raise SupabaseAuthError("Google sign-in timed out. Please try again.") from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed during Google OAuth exchange")
        raise SupabaseAuthError("Could not reach the sign-in service. Please try again.") from error

    if user_response.status_code != 200:
        raise SupabaseAuthError("Google could not verify this account. Please try again.")
    identity = user_response.json()
    providers = {identity.get("app_metadata", {}).get("provider")}
    providers.update(
        item.get("provider")
        for item in identity.get("identities", [])
        if isinstance(item, dict)
    )
    email = identity.get("email")
    if (
        "google" not in providers
        or not isinstance(email, str)
        or not email.strip()
        or not identity.get("email_confirmed_at")
    ):
        raise SupabaseAuthError("Google could not verify this account. Please try again.")
    return {
        "email": email.strip().lower(),
        "name": str(
            identity.get("user_metadata", {}).get("full_name")
            or identity.get("user_metadata", {}).get("name")
            or email.split("@", 1)[0]
        ).strip(),
    }


def find_user_by_email(email):
    return User.objects.filter(email__iexact=email.strip()).first()


def set_user_session(request, user):
    request.session.flush()
    request.session["campushub_user"] = {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "branch_id": str(user.branch_id) if user.branch_id else None,
        "semester": user.semester,
    }
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)


def create_google_user(profile, branch, semester):
    random_password = secrets.token_bytes(48)
    unusable_password_hash = bcrypt.hashpw(random_password, bcrypt.gensalt(rounds=12)).decode()
    try:
        with transaction.atomic():
            return User.objects.create(
                name=profile["name"] or profile["email"].split("@", 1)[0],
                email=profile["email"],
                password_hash=unusable_password_hash,
                branch=branch,
                semester=semester,
                role="student",
                created_at=timezone.now(),
            )
    except IntegrityError:
        user = find_user_by_email(profile["email"])
        if user:
            return user
        raise
