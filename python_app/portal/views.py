import logging
import secrets
from uuid import UUID

import bcrypt
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, OperationalError, ProgrammingError, connection, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from . import auth
from .forms import GoogleProfileForm, LoginForm, RegistrationForm
from .models import Announcement, Branch
from .models import User
from .storage import sign_storage_references

logger = logging.getLogger(__name__)


def home(request):
    branches = []
    announcements = []
    if settings.SUPABASE_DATABASE_CONFIGURED:
        branches = Branch.objects.all()
        announcements = list(
            Announcement.objects.select_related("target_branch").all()[:4]
        )
        session_user = request.session.get("campushub_user")
        session_user_id = (
            session_user.get("id") if isinstance(session_user, dict) else None
        )
        try:
            session_user_id = UUID(str(session_user_id)) if session_user_id else None
        except (ValueError, TypeError, AttributeError):
            session_user_id = None
        current_user = (
            User.objects.filter(id=session_user_id).first()
            if session_user_id
            else None
        )
        unavailable_attachment = False
        for announcement in announcements:
            if not announcement.attachment_url:
                continue
            announcement_branch_id = getattr(
                announcement, "target_branch_id", None
            )
            if announcement_branch_id and (
                not current_user
                or (
                    current_user.role not in {"admin", "super_admin"}
                    and current_user.branch_id != announcement_branch_id
                )
            ):
                announcement.attachment_url = ""
                continue
            unavailable_attachment = (
                sign_storage_references([announcement], "attachment_url")
                or unavailable_attachment
            )
        if unavailable_attachment:
            messages.error(
                request,
                "One or more notice attachments are temporarily unavailable. Please contact an administrator.",
            )
    return render(
        request,
        "portal/home.html",
        {
            "branches": branches,
            "announcements": announcements,
            "database_configured": settings.SUPABASE_DATABASE_CONFIGURED,
        },
    )


def branch_list(request):
    branches = Branch.objects.all() if settings.SUPABASE_DATABASE_CONFIGURED else []
    return render(
        request,
        "portal/branches.html",
        {
            "branches": branches,
            "database_configured": settings.SUPABASE_DATABASE_CONFIGURED,
        },
    )


def health(request):
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return JsonResponse(
            {"ok": False, "service": "CampuZHub Python", "database": "not_configured"},
            status=503,
        )
    try:
        connection.ensure_connection()
    except (OperationalError, ProgrammingError):
        logger.exception("Python app health check could not connect to PostgreSQL")
        return JsonResponse(
            {"ok": False, "service": "CampuZHub Python", "database": "disconnected"},
            status=503,
        )
    return JsonResponse(
        {"ok": True, "service": "CampuZHub Python", "database": "connected"}
    )


def feature_status(request, feature):
    return render(request, "portal/feature_status.html", {"feature": feature})


def login(request):
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return render(
            request,
            "portal/login.html",
            {"database_configured": False},
            status=503,
        )
    if request.method == "POST":
        form = LoginForm(request.POST)
        error = ""
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            user = auth.find_user_by_email(email)
            password = form.cleaned_data["password"].encode("utf-8")[:72]
            try:
                identity = auth.sign_in_with_email_password(
                    email, form.cleaned_data["password"]
                )
            except auth.SupabaseAuthError as auth_error:
                error = str(auth_error)
                if "verify your email" in error.lower():
                    try:
                        auth.resend_email_confirmation(request, email)
                    except auth.SupabaseAuthError:
                        logger.exception(
                            "Could not resend the verification email during sign-in"
                        )
                        error = (
                            "Your email is not verified, and we could not resend the "
                            "verification link. Please try again later."
                        )
                identity = None
            else:
                if identity and user:
                    auth.set_user_session(request, user)
                    return redirect("branchhub")

            if not error:
                try:
                    password_matches = user and bcrypt.checkpw(
                        password,
                        user.password_hash.encode("ascii"),
                    )
                except (ValueError, TypeError):
                    password_matches = False
                if password_matches:
                    try:
                        auth.begin_email_signup(
                            request,
                            email,
                            form.cleaned_data["password"],
                            {
                                "campushub_signup": True,
                                "campushub_name": user.name,
                                "campushub_branch_id": (
                                    str(user.branch_id) if user.branch_id else None
                                ),
                                "campushub_semester": user.semester,
                            },
                        )
                    except auth.SupabaseAuthError as auth_error:
                        error = str(auth_error)
                    else:
                        return render(
                            request,
                            "portal/login.html",
                            {
                                "form": LoginForm(),
                                "notice": (
                                    "We sent a verification link to your email. "
                                    "Verify it to continue signing in."
                                ),
                                "database_configured": True,
                            },
                        )
                elif identity:
                    error = (
                        "This email has been verified, but no CampuZHub account is linked to it. "
                        "Please create an account."
                    )
                else:
                    error = "The email address or password is incorrect."
    else:
        form = LoginForm()
        error = ""
    return render(
        request,
        "portal/login.html",
        {"form": form, "error": error, "database_configured": True},
    )


def register(request):
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return render(
            request,
            "portal/register.html",
            {"database_configured": False},
            status=503,
        )
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            values = form.cleaned_data
            if len(values["password"].encode("utf-8")) > 72:
                form.add_error("password", "The password cannot exceed 72 bytes when encoded as UTF-8.")
            else:
                email = values["email"].strip().lower()
                if auth.find_user_by_email(email):
                    form.add_error("email", "An account with this email address already exists.")
                else:
                    try:
                        auth.begin_email_signup(
                            request,
                            email,
                            values["password"],
                            {
                                "campushub_signup": True,
                                "campushub_name": values["name"].strip(),
                                "campushub_branch_id": (
                                    str(values["branch"].id)
                                    if values["branch"]
                                    else None
                                ),
                                "campushub_semester": values["semester"],
                            },
                        )
                    except auth.SupabaseAuthError as error:
                        form.add_error(None, str(error))
                    else:
                        return render(
                            request,
                            "portal/register.html",
                            {
                                "form": RegistrationForm(),
                                "database_configured": True,
                                "confirmation_sent": True,
                                "confirmation_email": email,
                            },
                        )
    else:
        form = RegistrationForm()
    return render(
        request,
        "portal/register.html",
        {"form": form, "database_configured": True},
    )


def email_confirmation(request):
    return render(request, "portal/email_confirmation.html")


def complete_email_confirmation(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use the verification link in your email."}, status=405)
    access_token = request.POST.get("access_token", "")
    if not access_token or len(access_token) > 4096:
        return JsonResponse(
            {"error": "This verification link is invalid or expired. Request a new one."},
            status=400,
        )
    try:
        identity = auth.get_verified_email_identity(access_token)
    except auth.SupabaseAuthError as error:
        return JsonResponse({"error": str(error)}, status=400)

    email = identity.get("email")
    metadata = identity.get("user_metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    if (
        not isinstance(email, str)
        or not email.strip()
        or metadata.get("campushub_signup") is not True
    ):
        return JsonResponse(
            {"error": "This verified email is not linked to a CampuZHub signup."},
            status=400,
        )

    user = auth.find_user_by_email(email.strip().lower())
    if not user:
        name = metadata.get("campushub_name")
        if not isinstance(name, str) or not name.strip():
            return JsonResponse(
                {"error": "The signup details are incomplete. Please register again."},
                status=400,
            )
        branch_id = metadata.get("campushub_branch_id")
        branch = None
        if branch_id:
            try:
                branch = Branch.objects.filter(id=UUID(str(branch_id))).first()
            except (ValueError, TypeError, AttributeError):
                return JsonResponse(
                    {"error": "The selected branch is invalid. Please register again."},
                    status=400,
                )
            if not branch:
                return JsonResponse(
                    {"error": "The selected branch is no longer available. Please register again."},
                    status=400,
                )
        semester = metadata.get("campushub_semester")
        if semester is not None and (
            not isinstance(semester, int) or not 1 <= semester <= 12
        ):
            return JsonResponse(
                {"error": "The selected semester is invalid. Please register again."},
                status=400,
            )
        password_hash = bcrypt.hashpw(
            secrets.token_bytes(48), bcrypt.gensalt(rounds=12)
        ).decode()
        try:
            with transaction.atomic():
                user = User.objects.create(
                    name=name.strip(),
                    email=email.strip().lower(),
                    password_hash=password_hash,
                    branch=branch,
                    semester=semester,
                    role="student",
                    created_at=timezone.now(),
                )
        except IntegrityError:
            user = auth.find_user_by_email(email.strip().lower())
            if not user:
                logger.exception("Could not create a verified CampuZHub student")
                return JsonResponse(
                    {"error": "We could not finish account setup. Please try again."},
                    status=500,
                )

    auth.set_user_session(request, user)
    return JsonResponse({"redirect_url": reverse("branchhub")})


def google_sign_in(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("login"))
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return render(
            request,
            "portal/login.html",
            {"database_configured": False},
            status=503,
        )
    try:
        return redirect(auth.begin_google_oauth(request))
    except auth.SupabaseAuthError as error:
        return render(request, "portal/login.html", {"form": LoginForm(), "error": str(error)})


def google_callback(request):
    if request.GET.get("error"):
        request.session.pop("google_pkce_verifier", None)
        request.session.pop("google_started_at", None)
        return render(
            request,
            "portal/login.html",
            {"form": LoginForm(), "error": "Google sign-in was cancelled or failed. Please try again."},
        )
    code = request.GET.get("code")
    if not code:
        request.session.pop("google_pkce_verifier", None)
        request.session.pop("google_started_at", None)
        return render(
            request,
            "portal/login.html",
            {"form": LoginForm(), "error": "The Google sign-in response was incomplete. Please start sign-in again."},
        )
    try:
        profile = auth.exchange_google_code(request, code)
    except auth.SupabaseAuthError as error:
        return render(request, "portal/login.html", {"form": LoginForm(), "error": str(error)})

    user = auth.find_user_by_email(profile["email"])
    if user:
        auth.set_user_session(request, user)
        return redirect("branchhub")
    request.session["google_pending_profile"] = profile
    request.session.set_expiry(600)
    return redirect("google_profile")


def google_profile(request):
    profile = request.session.get("google_pending_profile")
    if not profile:
        return redirect("login")
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return render(
            request,
            "portal/google_profile.html",
            {"database_configured": False},
            status=503,
        )
    if request.method == "POST":
        form = GoogleProfileForm(request.POST)
        if form.is_valid():
            values = form.cleaned_data
            try:
                user = auth.create_google_user(
                    profile,
                    values["branch"],
                    values["semester"],
                )
            except IntegrityError:
                logger.exception("Could not create a CampuZHub student after verified Google sign-in")
                form.add_error(None, "We could not create your account. Please try again shortly.")
            else:
                auth.set_user_session(request, user)
                return redirect("branchhub")
    else:
        form = GoogleProfileForm()
    return render(
        request,
        "portal/google_profile.html",
        {
            "form": form,
            "profile": profile,
            "database_configured": True,
        },
    )


def logout(request):
    if request.method == "POST":
        request.session.flush()
    return redirect("home")
