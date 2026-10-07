import logging

from django.conf import settings
from django.db import OperationalError, ProgrammingError, connection
from django.http import JsonResponse
from django.shortcuts import render

from .models import Announcement, Branch

logger = logging.getLogger(__name__)


def home(request):
    branches = []
    announcements = []
    if settings.SUPABASE_DATABASE_CONFIGURED:
        branches = Branch.objects.all()
        announcements = Announcement.objects.select_related("target_branch").all()[:4]
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
    return render(request, "portal/branches.html", {"branches": branches})


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
