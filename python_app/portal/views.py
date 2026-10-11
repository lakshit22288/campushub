import logging
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
            {"ok": False, "service": "CampusHub Python", "database": "not_configured"},
            status=503,
        )
    try:
        connection.ensure_connection()
    except (OperationalError, ProgrammingError):
        logger.exception("Python app health check could not connect to PostgreSQL")
        return JsonResponse(
            {"ok": False, "service": "CampusHub Python", "database": "disconnected"},
            status=503,
        )
    return JsonResponse(
        {"ok": True, "service": "CampusHub Python", "database": "connected"}
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
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            user = auth.find_user_by_email(email)
            password = form.cleaned_data["password"].encode("utf-8")[:72]
            try:
                password_matches = user and bcrypt.checkpw(
                    password,
                    user.password_hash.encode("ascii"),
                )
            except (ValueError, TypeError):
                password_matches = False
            if password_matches:
                auth.set_user_session(request, user)
                return redirect("branchhub")
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
                    password_hash = bcrypt.hashpw(
                        values["password"].encode("utf-8"),
                        bcrypt.gensalt(rounds=12),
                    ).decode()
                    try:
                        with transaction.atomic():
                            user = User.objects.create(
                                name=values["name"].strip(),
                                email=email,
                                password_hash=password_hash,
                                branch=values["branch"],
                                semester=values["semester"],
                                role="student",
                                created_at=timezone.now(),
                            )
                    except IntegrityError:
                        if auth.find_user_by_email(email):
                            form.add_error("email", "An account with this email address already exists.")
                        else:
                            logger.exception("Database rejected a new student registration")
                            form.add_error(
                                None,
                                "We could not create your account. Check your details and try again.",
                            )
                    else:
                        auth.set_user_session(request, user)
                        return redirect("branchhub")
    else:
        form = RegistrationForm()
    return render(
        request,
        "portal/register.html",
        {"form": form, "database_configured": True},
    )


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
                logger.exception("Could not create a CampusHub student after verified Google sign-in")
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
