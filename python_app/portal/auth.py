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
        raise SupabaseAuthError("Supabase sign-in is not configured for the Python app.")
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


def _auth_headers(api_key):
    return {"apikey": api_key, "Accept": "application/json"}


def _user_auth_headers(api_key, access_token):
    headers = _auth_headers(api_key)
    headers["Authorization"] = "Bearer " + access_token
    return headers


def _email_confirmation_url(request):
    callback_path = reverse("email_confirmation")
    if settings.DJANGO_PUBLIC_URL:
        return f"{settings.DJANGO_PUBLIC_URL}{callback_path}"
    return request.build_absolute_uri(callback_path)


def _password_reset_url(request):
    callback_path = reverse("password_reset_confirm")
    if settings.DJANGO_PUBLIC_URL:
        return f"{settings.DJANGO_PUBLIC_URL}{callback_path}"
    return request.build_absolute_uri(callback_path)


def begin_email_signup(request, email, password, metadata):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(
                f"{supabase_url}/auth/v1/signup",
                params={"redirect_to": _email_confirmation_url(request)},
                headers=_auth_headers(api_key),
                json={"email": email, "password": password, "data": metadata},
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while starting email registration")
        raise SupabaseAuthError(
            "Email verification could not be started right now. Please try again."
        ) from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while starting email registration")
        raise SupabaseAuthError(
            "Could not reach the email verification service. Please try again."
        ) from error

    if response.status_code not in (200, 201):
        logger.warning(
            "Supabase Auth rejected email registration with status %s",
            response.status_code,
        )
        raise SupabaseAuthError(
            "We could not start email verification. Check your email address and try again."
        )

    result = response.json()
    if not isinstance(result, dict):
        raise SupabaseAuthError(
            "The email verification service returned an invalid response."
        )
    user = result.get("user") or result
    if not isinstance(user, dict) or not user.get("id"):
        raise SupabaseAuthError(
            "The email verification service returned an invalid response."
        )
    if result.get("session") or user.get("email_confirmed_at"):
        raise SupabaseAuthError(
            "Email verification is not enabled for CampuZHub yet. Please contact an administrator."
        )
    if user.get("identities") == []:
        raise SupabaseAuthError(
            "This email is already registered. Log in or use the sign-in method linked to it."
        )


def resend_email_confirmation(request, email):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(
                f"{supabase_url}/auth/v1/resend",
                headers=_auth_headers(api_key),
                json={
                    "type": "signup",
                    "email": email,
                    "options": {"emailRedirectTo": _email_confirmation_url(request)},
                },
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while resending email confirmation")
        raise SupabaseAuthError(
            "The verification email could not be resent right now. Please try again."
        ) from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while resending email confirmation")
        raise SupabaseAuthError(
            "Could not reach the email verification service. Please try again."
        ) from error

    if response.status_code not in (200, 201):
        logger.warning(
            "Supabase Auth rejected email confirmation resend with status %s",
            response.status_code,
        )
        raise SupabaseAuthError(
            "The verification email could not be resent. Please try again later."
        )


def request_password_reset(request, email):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(
                f"{supabase_url}/auth/v1/recover",
                params={"redirect_to": _password_reset_url(request)},
                headers=_auth_headers(api_key),
                json={"email": email},
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while requesting password recovery")
        raise SupabaseAuthError(
            "We could not send a password reset email right now. Please try again."
        ) from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while requesting password recovery")
        raise SupabaseAuthError(
            "We could not send a password reset email right now. Please try again."
        ) from error

    if response.status_code != 200:
        logger.warning(
            "Supabase Auth rejected a password recovery request with status %s",
            response.status_code,
        )
        raise SupabaseAuthError(
            "We could not send a password reset email right now. Please try again later."
        )


def update_password_with_recovery_token(access_token, password):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.put(
                f"{supabase_url}/auth/v1/user",
                headers=_user_auth_headers(api_key, access_token),
                json={"password": password},
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while updating a recovered password")
        raise SupabaseAuthError(
            "Password reset timed out. Please try the link again."
        ) from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while updating a recovered password")
        raise SupabaseAuthError(
            "Could not reach the password reset service. Please try again."
        ) from error

    if response.status_code in (400, 401, 403):
        raise SupabaseAuthError(
            "This password reset link is invalid or expired. Request a new one."
        )
    if response.status_code != 200:
        logger.warning(
            "Supabase Auth rejected a recovered password update with status %s",
            response.status_code,
        )
        raise SupabaseAuthError(
            "The password could not be updated right now. Please try again."
        )


def sign_in_with_email_password(email, password):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(
                f"{supabase_url}/auth/v1/token",
                params={"grant_type": "password"},
                headers=_auth_headers(api_key),
                json={"email": email, "password": password},
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out during email/password sign-in")
        raise SupabaseAuthError("Sign-in timed out. Please try again.") from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed during email/password sign-in")
        raise SupabaseAuthError(
            "Could not reach the sign-in service. Please try again."
        ) from error

    if response.status_code == 400:
        payload = response.json()
        code = str(payload.get("code", "")).lower()
        message = str(payload.get("msg") or payload.get("message") or "").lower()
        if code == "email_not_confirmed" or "email not confirmed" in message:
            raise SupabaseAuthError(
                "Please verify your email before signing in. We can send you another verification link."
            )
        if code in {"invalid_credentials", "user_not_found"} or "invalid login credentials" in message:
            return None
    if response.status_code != 200:
        logger.warning(
            "Supabase Auth email/password sign-in returned status %s",
            response.status_code,
        )
        raise SupabaseAuthError(
            "Sign-in could not be completed right now. Please try again."
        )

    result = response.json()
    access_token = result.get("access_token")
    if not access_token:
        raise SupabaseAuthError("The sign-in service did not return a valid session.")
    try:
        with httpx.Client(timeout=12) as client:
            user_response = client.get(
                f"{supabase_url}/auth/v1/user",
                headers=_user_auth_headers(api_key, access_token),
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while checking a signed-in email")
        raise SupabaseAuthError("Sign-in timed out. Please try again.") from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while checking a signed-in email")
        raise SupabaseAuthError(
            "Could not verify the sign-in session. Please try again."
        ) from error

    if user_response.status_code != 200:
        raise SupabaseAuthError("The sign-in session could not be verified. Please try again.")
    identity = user_response.json()
    if not identity.get("email_confirmed_at"):
        raise SupabaseAuthError(
            "Please verify your email before signing in. We can send you another verification link."
        )
    return identity


def get_verified_email_identity(access_token):
    supabase_url, api_key = _supabase_config()
    try:
        with httpx.Client(timeout=12) as client:
            response = client.get(
                f"{supabase_url}/auth/v1/user",
                headers=_user_auth_headers(api_key, access_token),
            )
    except httpx.TimeoutException as error:
        logger.warning("Supabase Auth timed out while verifying an email confirmation")
        raise SupabaseAuthError(
            "Email verification timed out. Please open the link again."
        ) from error
    except httpx.RequestError as error:
        logger.exception("Supabase Auth request failed while verifying an email confirmation")
        raise SupabaseAuthError(
            "Could not reach the email verification service. Please try again."
        ) from error

    if response.status_code != 200:
        raise SupabaseAuthError(
            "This verification link is invalid or expired. Request a new one and try again."
        )
    identity = response.json()
    if not identity.get("email_confirmed_at"):
        raise SupabaseAuthError("This email address has not been verified.")
    return identity


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
                headers=_user_auth_headers(api_key, access_token),
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
