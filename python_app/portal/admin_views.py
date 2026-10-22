import secrets
import time

from django.contrib import messages
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from .features import ADMIN_ROLES, STAFF_ROLES, _uuid_or_none, role_required
from .forms import AnnouncementForm, CampusEventForm, NoteForm, SubjectForm
from .models import (
    Announcement,
    Book,
    Branch,
    Note,
    Skill,
    Subject,
    User,
)
from .storage import (
    StorageUploadError,
    create_admin_upload_url,
    delete_admin_upload,
    upload_announcement_file,
    upload_note_file,
    verify_admin_upload,
)

CONTENT_ROLES = {"teacher", "admin", "super_admin"}
ROLE_CHOICES = {"student", "teacher", "moderator", "admin", "super_admin"}
PENDING_UPLOAD_SESSION_KEY = "pending_admin_uploads"
PENDING_UPLOAD_TTL_SECONDS = 30 * 60


def _take_admin_upload(request, upload_id, folder):
    pending = request.session.get(PENDING_UPLOAD_SESSION_KEY, {})
    upload = pending.get(upload_id) if isinstance(pending, dict) else None
    if (
        not isinstance(upload, dict)
        or upload.get("folder") != folder
        or time.time() - upload.get("created_at", 0) > PENDING_UPLOAD_TTL_SECONDS
    ):
        raise StorageUploadError("The upload expired. Select the file and try again.")
    try:
        verify_admin_upload(
            upload["file_reference"],
            content_type=upload["content_type"],
            expected_size=upload["file_size"],
            folder=folder,
        )
    except StorageUploadError:
        delete_admin_upload(upload["file_reference"])
        pending.pop(upload_id, None)
        request.session[PENDING_UPLOAD_SESSION_KEY] = pending
        raise
    pending.pop(upload_id, None)
    request.session[PENDING_UPLOAD_SESSION_KEY] = pending
    return upload["file_reference"], upload["file_name"]


@require_POST
@role_required(CONTENT_ROLES)
def prepare_admin_upload(request):
    user = request.campushub_user
    action = request.POST.get("action", "")
    folder = {"note": "notes", "announcement": "announcements"}.get(action)
    if not folder:
        return JsonResponse({"error": "This upload action is not supported."}, status=400)
    if not settings.SUPABASE_ANON_KEY:
        return JsonResponse(
            {"error": "Browser uploads are not configured. Ask an administrator to check Supabase settings."},
            status=503,
        )

    if action == "note":
        form = NoteForm(request.POST, user_role=user.role)
    else:
        form = AnnouncementForm(request.POST, user_role=user.role)
    if not form.is_valid():
        return JsonResponse(
            {"errors": {name: errors.get_json_data() for name, errors in form.errors.items()}},
            status=400,
        )
    if action == "note" and user.role == "teacher":
        subject = form.cleaned_data["subject"]
        if not user.branch_id or subject.branch_id != user.branch_id:
            return JsonResponse(
                {"error": "Teachers can only publish content for their assigned branch."},
                status=403,
            )
    if action == "announcement" and user.role == "teacher":
        if not user.branch_id:
            return JsonResponse(
                {"error": "A branch must be assigned before publishing an announcement."},
                status=403,
            )
        selected_branch = form.cleaned_data["target_branch"]
        if selected_branch and selected_branch.id != user.branch_id:
            return JsonResponse(
                {"error": "Teachers can only send announcements to their assigned branch."},
                status=403,
            )

    try:
        upload = create_admin_upload_url(
            file_name=request.POST.get("file_name", ""),
            content_type=request.POST.get("content_type", ""),
            file_size=int(request.POST.get("file_size", "")),
            folder=folder,
        )
    except (StorageUploadError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)

    upload_id = secrets.token_urlsafe(24)
    pending = request.session.get(PENDING_UPLOAD_SESSION_KEY, {})
    if not isinstance(pending, dict):
        pending = {}
    pending = {
        key: value
        for key, value in pending.items()
        if isinstance(value, dict)
        and time.time() - value.get("created_at", 0) <= PENDING_UPLOAD_TTL_SECONDS
    }
    pending[upload_id] = {
        "file_reference": upload["file_reference"],
        "file_name": upload["file_name"],
        "content_type": upload["content_type"],
        "file_size": upload["file_size"],
        "folder": folder,
        "created_at": time.time(),
    }
    request.session[PENDING_UPLOAD_SESSION_KEY] = pending
    return JsonResponse(
        {
            "upload_id": upload_id,
            "upload_url": upload["upload_url"],
            "content_type": upload["content_type"],
            "api_key": settings.SUPABASE_ANON_KEY,
        }
    )


def _staff_form(request, user):
    action = request.POST.get("action", "")
    if action == "subject":
        if user.role not in ADMIN_ROLES:
            messages.error(request, "Only admins and super-admins can manage the subject catalog.")
            return redirect("admin")
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.slug = slugify(subject.name)
            try:
                subject.save()
            except IntegrityError:
                form.add_error("name", "This subject is already listed for this branch.")
            else:
                messages.success(request, "The subject has been added to the catalog.")
                return redirect("admin")
        return "subject", form

    if action == "note":
        if user.role not in CONTENT_ROLES:
            messages.error(request, "You do not have permission to publish academic content.")
            return redirect("admin")
        form = NoteForm(request.POST, request.FILES, user_role=user.role)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            if user.role == "teacher" and (
                not user.branch_id or subject.branch_id != user.branch_id
            ):
                form.add_error(
                    "subject",
                    "Teachers can only publish content for subjects in their assigned branch.",
                )
                return "note", form
            uploaded_file = form.cleaned_data["file"]
            file_url, file_name = None, None
            if uploaded_file:
                try:
                    file_url, file_name = upload_note_file(uploaded_file)
                except StorageUploadError as error:
                    form.add_error("file", str(error))
                    return "note", form
            elif form.cleaned_data["upload_id"]:
                try:
                    file_url, file_name = _take_admin_upload(
                        request, form.cleaned_data["upload_id"], "notes"
                    )
                except StorageUploadError as error:
                    form.add_error("file", str(error))
                    return "note", form
            Note.objects.create(
                subject=subject,
                title=form.cleaned_data["title"].strip(),
                description=form.cleaned_data["description"].strip(),
                file_url=file_url,
                file_name=file_name,
                source_type=form.cleaned_data["source_type"],
                created_by=user,
                created_at=timezone.now(),
            )
            messages.success(request, "The study resource has been published.")
            return redirect("admin")
        return "note", form

    if action == "announcement":
        if user.role not in CONTENT_ROLES:
            messages.error(request, "You do not have permission to publish announcements.")
            return redirect("admin")
        form = AnnouncementForm(request.POST, request.FILES, user_role=user.role)
        if form.is_valid():
            announcement = form.save(commit=False)
            if user.role == "teacher":
                if not user.branch_id:
                    form.add_error(
                        "target_branch",
                        "A branch must be assigned to your account before you can publish an announcement.",
                    )
                    return "announcement", form
                if announcement.target_branch_id not in {None, user.branch_id}:
                    form.add_error(
                        "target_branch",
                        "Teachers can only send announcements to their assigned branch.",
                    )
                    return "announcement", form
                announcement.target_branch_id = user.branch_id
            uploaded_file = form.cleaned_data["attachment"]
            if uploaded_file:
                try:
                    announcement.attachment_url, announcement.attachment_name = (
                        upload_announcement_file(uploaded_file)
                    )
                except StorageUploadError as error:
                    form.add_error("attachment", str(error))
                    return "announcement", form
            elif form.cleaned_data["upload_id"]:
                try:
                    (
                        announcement.attachment_url,
                        announcement.attachment_name,
                    ) = _take_admin_upload(
                        request, form.cleaned_data["upload_id"], "announcements"
                    )
                except StorageUploadError as error:
                    form.add_error("attachment", str(error))
                    return "announcement", form
            announcement.created_by = user
            announcement.created_at = timezone.now()
            announcement.save()
            messages.success(request, "The announcement has been published.")
            return redirect("admin")
        return "announcement", form

    if action == "event":
        if user.role not in CONTENT_ROLES:
            messages.error(request, "You do not have permission to publish campus events.")
            return redirect("admin")
        form = CampusEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            if user.role == "teacher":
                if not user.branch_id:
                    form.add_error(
                        "target_branch",
                        "A branch must be assigned to your account before you can publish an event.",
                    )
                    return "event", form
                if event.target_branch_id not in {None, user.branch_id}:
                    form.add_error(
                        "target_branch",
                        "Teachers can only publish events for their assigned branch.",
                    )
                    return "event", form
                event.target_branch_id = user.branch_id
            event.created_by = user
            event.created_at = timezone.now()
            event.save()
            messages.success(request, "The campus event has been published.")
            return redirect("admin")
        return "event", form

    if action == "role":
        if user.role != "super_admin":
            messages.error(request, "Only super-admins can manage account roles.")
            return redirect("admin")
        target_id = _uuid_or_none(request.POST.get("user_id"))
        role = request.POST.get("role", "")
        if not target_id:
            messages.error(request, "The account ID is invalid.")
        elif role not in ROLE_CHOICES:
            messages.error(request, "The selected account role is invalid.")
        else:
            with transaction.atomic():
                target = User.objects.select_for_update().filter(id=target_id).first()
                if not target:
                    messages.error(request, "The account could not be found.")
                elif target.id == user.id and role != "super_admin":
                    messages.error(request, "You cannot remove your own super-admin access here.")
                elif (
                    target.role == "super_admin"
                    and role != "super_admin"
                    and User.objects.filter(role="super_admin").count() <= 1
                ):
                    messages.error(request, "The platform's last super-admin cannot be demoted.")
                else:
                    target.role = role
                    target.save(update_fields=["role"])
                    messages.success(request, "The account role has been updated.")
        return redirect("admin")

    return None


@require_http_methods(["GET", "POST"])
@role_required(STAFF_ROLES)
def admin_dashboard(request):
    user = request.campushub_user
    selected_form = ""
    selected_value = None
    if request.method == "POST":
        result = _staff_form(request, user)
        if isinstance(result, tuple):
            selected_form, selected_value = result

    subjects = Subject.objects.select_related("branch")
    if user.role == "teacher":
        subjects = subjects.filter(branch_id=user.branch_id) if user.branch_id else subjects.none()
    teacher_default_subject = subjects.first() if user.role == "teacher" else None
    users = User.objects.select_related("branch").order_by("name")[:100] if user.role == "super_admin" else []
    stats = {
        "users": User.objects.count(),
        "subjects": Subject.objects.count(),
        "notes": Note.objects.count(),
        "books": Book.objects.count(),
        "skills": Skill.objects.count(),
        "announcements": Announcement.objects.count(),
    }
    return render(
        request,
        "portal/admin.html",
        {
            "stats": stats,
            "subjects": subjects,
            "branches": Branch.objects.all(),
            "users": users,
            "role_choices": sorted(ROLE_CHOICES),
            "subject_form": selected_value if selected_form == "subject" else SubjectForm(),
            "note_form": selected_value if selected_form == "note" else NoteForm(
                initial={"subject": teacher_default_subject} if teacher_default_subject else None,
                user_role=user.role,
            ),
            "announcement_form": selected_value if selected_form == "announcement" else AnnouncementForm(
                user_role=user.role,
            ),
            "event_form": selected_value if selected_form == "event" else CampusEventForm(),
            "selected_form": selected_form,
            "can_manage_content": user.role in CONTENT_ROLES,
            "can_manage_subjects": user.role in ADMIN_ROLES,
            "can_manage_users": user.role == "super_admin",
        },
    )
