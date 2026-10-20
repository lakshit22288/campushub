from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .features import (
    _for_visible_campus_branch,
    _session_user,
    _uuid_or_none,
    signed_in_user,
)
from .forms import AssignmentEntryForm, ScheduleEntryForm
from .models import Announcement, AssignmentEntry, CampusEvent, ScheduleEntry
from .storage import sign_storage_references


def campus_board(request):
    if not settings.SUPABASE_DATABASE_CONFIGURED:
        return render(
            request,
            "portal/campus_board.html",
            {
                "notices": [],
                "events": [],
                "database_configured": False,
            },
        )

    user = _session_user(request)
    notices = Announcement.objects.select_related("target_branch")
    events = CampusEvent.objects.select_related("target_branch").filter(
        ends_at__gte=timezone.now()
    )
    notices = _for_visible_campus_branch(notices, user)
    events = _for_visible_campus_branch(events, user)
    notices = list(notices.order_by("-created_at")[:30])
    if sign_storage_references(notices, "attachment_url"):
        messages.error(
            request,
            "One or more notice attachments are temporarily unavailable. Please contact an administrator.",
        )
    return render(
        request,
        "portal/campus_board.html",
        {
            "notices": notices,
            "events": events.select_related("target_branch").order_by("starts_at")[:30],
            "database_configured": True,
        },
    )


@require_http_methods(["GET", "POST"])
@signed_in_user
def planner(request):
    user = request.campushub_user
    schedule_form = ScheduleEntryForm()
    assignment_form = AssignmentEntryForm()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "add_schedule":
            schedule_form = ScheduleEntryForm(request.POST)
            if schedule_form.is_valid():
                entry = schedule_form.save(commit=False)
                entry.user = user
                entry.created_at = timezone.now()
                entry.save()
                messages.success(request, "Class added to your weekly timetable.")
                return redirect("planner")
        elif action == "add_assignment":
            assignment_form = AssignmentEntryForm(request.POST)
            if assignment_form.is_valid():
                assignment = assignment_form.save(commit=False)
                assignment.user = user
                assignment.created_at = timezone.now()
                assignment.save()
                messages.success(request, "Assignment added to your tracker.")
                return redirect("planner")
        elif action in {"delete_schedule", "delete_assignment"}:
            entry_id = _uuid_or_none(request.POST.get("entry_id"))
            model = ScheduleEntry if action == "delete_schedule" else AssignmentEntry
            if entry_id:
                deleted, _ = model.objects.filter(id=entry_id, user=user).delete()
            else:
                deleted = 0
            if deleted:
                messages.success(request, "Your planner item has been removed.")
            else:
                messages.error(request, "That planner item could not be found.")
            return redirect("planner")
        elif action == "toggle_assignment":
            entry_id = _uuid_or_none(request.POST.get("entry_id"))
            assignment = (
                AssignmentEntry.objects.filter(id=entry_id, user=user).first()
                if entry_id
                else None
            )
            if assignment:
                assignment.completed = not assignment.completed
                assignment.save(update_fields=["completed"])
                messages.success(
                    request,
                    "Assignment marked complete."
                    if assignment.completed
                    else "Assignment marked as not complete.",
                )
            else:
                messages.error(request, "That assignment could not be found.")
            return redirect("planner")
        else:
            messages.error(request, "That planner action is not recognized.")
            return redirect("planner")

    return render(
        request,
        "portal/planner.html",
        {
            "schedule_form": schedule_form,
            "assignment_form": assignment_form,
            "schedule_entries": ScheduleEntry.objects.filter(user=user).order_by(
                "day_of_week", "start_time"
            ),
            "assignments": AssignmentEntry.objects.filter(user=user),
            "today": timezone.localdate(),
        },
    )
