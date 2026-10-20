from functools import wraps
import logging
import random
import re
import uuid
from urllib.parse import quote

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import auth
from .branch_tool_catalog import BRANCH_TOOL_CATALOG
from .branch_tool_views import branch_tool_groups
from .storage import (
    StorageUploadError,
    sign_storage_references,
    upload_project_file,
)
from .forms import (
    BookListingForm,
    HelpRequestForm,
    ProfileForm,
    ProjectForm,
    SkillForm,
    SkillFeedbackForm,
    SkillRequestForm,
)
from .models import (
    Announcement,
    Book,
    BookRequest,
    Branch,
    HelpRequest,
    Note,
    Project,
    Skill,
    SkillFeedback,
    SkillRequest,
    Subject,
    Tool,
    User,
)
from .idea_catalog import IDEAS

logger = logging.getLogger(__name__)
STAFF_ROLES = {"teacher", "moderator", "admin", "super_admin"}
ADMIN_ROLES = {"admin", "super_admin"}
SUPPORTED_TOOL_ROUTES = {"/compiler", "/compiler/", "/project-ideas", "/project-ideas/"}
SUPPORTED_TOOL_ROUTES.update(
    path
    for slug in (
        "percentage", "cgpa", "units", "python", "sql", "linux", "subnet",
        "ohms-law", "power", "logic-gates", "mechanical-units", "area-volume",
        "mlt-dilution",
    )
    for path in (f"/tools/{slug}", f"/tools/{slug}/")
)

SEARCH_CATEGORIES = (
    ("all", "Everything"),
    ("subjects", "Subjects"),
    ("resources", "Study resources"),
    ("tools", "Tools"),
    ("books", "BookShare"),
    ("skills", "SkillSwap"),
    ("projects", "Projects"),
    ("help", "Help board"),
    ("announcements", "Announcements"),
    ("branches", "Branches"),
    ("ideas", "Project ideas"),
)


def _search_terms(query):
    return re.findall(r"[\w'-]+", query, flags=re.UNICODE)[:8]


def _search_filter(terms, fields):
    combined = Q()
    for term in terms:
        term_match = Q()
        for field in fields:
            term_match |= Q(**{f"{field}__icontains": term})
        combined &= term_match
    return combined


def signed_in_user(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        session_user = request.session.get("campushub_user")
        user_id = session_user.get("id") if isinstance(session_user, dict) else None
        if not user_id:
            messages.info(request, "Please log in to your CampuZHub account first.")
            return redirect("login")
        user_id = _uuid_or_none(user_id)
        if not user_id:
            request.session.flush()
            messages.error(request, "Your account session is invalid. Please log in again.")
            return redirect("login")
        user = User.objects.filter(id=user_id).first()
        if not user:
            request.session.flush()
            messages.error(request, "Your account session has expired. Please log in again.")
            return redirect("login")
        request.campushub_user = user
        return view(request, *args, **kwargs)

    return wrapped


def role_required(roles):
    def decorate(view):
        @wraps(view)
        @signed_in_user
        def wrapped(request, *args, **kwargs):
            if request.campushub_user.role not in roles:
                messages.error(request, "You do not have permission to access this section.")
                return redirect("home")
            return view(request, *args, **kwargs)

        return wrapped

    return decorate


def _uuid_or_none(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _session_user(request):
    session_user = request.session.get("campushub_user")
    user_id = session_user.get("id") if isinstance(session_user, dict) else None
    user_id = _uuid_or_none(user_id)
    return User.objects.filter(id=user_id).first() if user_id else None


def branchhub(request):
    branches = list(Branch.objects.all())
    selected_branch_id = _uuid_or_none(request.GET.get("branch"))
    selected_branch = None
    subjects = Subject.objects.select_related("branch")
    if selected_branch_id:
        selected_branch = next(
            (branch for branch in branches if branch.id == selected_branch_id),
            None,
        )
        if selected_branch:
            subjects = subjects.filter(branch_id=selected_branch_id)
    page_obj = Paginator(subjects, 18).get_page(request.GET.get("page"))
    return render(
        request,
        "portal/branchhub.html",
        {
            "branches": branches,
            "subjects": page_obj,
            "page_obj": page_obj,
            "selected_branch": selected_branch,
            "branch_filter": str(selected_branch.id) if selected_branch else "",
            "branch_tool_groups": branch_tool_groups(branches, selected_branch),
        },
    )


@signed_in_user
def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject.objects.select_related("branch"), id=subject_id)
    teacher_notes = Note.objects.filter(
        subject=subject,
        source_type=Note.SOURCE_TEACHER,
    ).select_related("created_by")
    ai_notes = Note.objects.filter(
        subject=subject,
        source_type=Note.SOURCE_AI,
    ).select_related("created_by")
    unavailable_teacher_files = sign_storage_references(teacher_notes, "file_url")
    unavailable_ai_files = sign_storage_references(ai_notes, "file_url")
    if unavailable_teacher_files or unavailable_ai_files:
        messages.error(
            request,
            "One or more study-resource files are temporarily unavailable. Please contact an administrator.",
        )
    tools = Tool.objects.filter(Q(subject=subject) | Q(branch=subject.branch) | Q(branch__isnull=True))
    return render(
        request,
        "portal/subject_detail.html",
        {
            "subject": subject,
            "teacher_notes": teacher_notes,
            "ai_notes": ai_notes,
            "tools": tools,
        },
    )


@require_http_methods(["GET", "POST"])
@signed_in_user
def profile(request):
    user = request.campushub_user
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            auth.set_user_session(request, user)
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=user)
    skills = Skill.objects.filter(user=user)
    return render(request, "portal/profile.html", {"form": form, "skills": skills})


@require_http_methods(["GET", "POST"])
@signed_in_user
def bookshare(request):
    user = request.campushub_user
    if request.method == "POST":
        form = BookListingForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.owner = user
            book.status = "available"
            book.created_at = timezone.now()
            book.save()
            messages.success(request, "Your book listing has been published.")
            return redirect("bookshare")
    else:
        form = BookListingForm(initial={"branch": user.branch_id})

    query = request.GET.get("q", "").strip()[:120]
    branch_id = _uuid_or_none(request.GET.get("branch", "").strip())
    today = timezone.localdate()
    listings = (
        Book.objects.select_related("owner", "branch")
        .exclude(status="closed")
        .filter(
            Q(available_until__isnull=True)
            | Q(available_until__gte=today)
            | Q(owner=user)
        )
    )
    if query:
        listings = listings.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(subject__icontains=query)
        )
    if branch_id:
        listings = listings.filter(branch_id=branch_id)
    listing_count = listings.count()
    listings = list(listings[:100])
    for book in listings:
        book.is_expired = bool(book.available_until and book.available_until < today)

    own_requests = (
        BookRequest.objects.filter(requester=user)
        .select_related("book", "book__owner")
    )
    own_requests = list(own_requests[:100])
    received_requests = (
        BookRequest.objects.filter(book__owner=user)
        .select_related("book", "requester")
    )
    received_requests = list(received_requests[:100])
    return render(
        request,
        "portal/bookshare.html",
        {
            "form": form,
            "listings": listings,
            "listing_count": listing_count,
            "branches": list(Branch.objects.all()),
            "query": query,
            "selected_branch": str(branch_id) if branch_id else "",
            "own_requests": own_requests,
            "received_requests": received_requests,
        },
    )


@require_POST
@signed_in_user
def request_book(request, book_id):
    user = request.campushub_user
    try:
        with transaction.atomic():
            book = get_object_or_404(Book.objects.select_for_update(), id=book_id)
            if book.owner_id == user.id:
                messages.error(request, "You cannot request your own listing.")
            elif book.available_until and book.available_until < timezone.localdate():
                messages.error(request, "This listing has expired and is no longer available.")
            elif book.status != "available":
                messages.error(request, "This listing is no longer available.")
            else:
                previous_request = (
                    BookRequest.objects.select_for_update()
                    .filter(book=book, requester=user)
                    .first()
                )
                if previous_request and previous_request.status in {"pending", "accepted"}:
                    messages.error(request, "You already have an active request for this book.")
                    return redirect("bookshare")
                if previous_request:
                    previous_request.status = "pending"
                    previous_request.created_at = timezone.now()
                    previous_request.save(update_fields=["status", "created_at"])
                else:
                    BookRequest.objects.create(
                        book=book,
                        requester=user,
                        status="pending",
                        created_at=timezone.now(),
                    )
                book.status = "requested"
                book.save(update_fields=["status"])
                messages.success(request, "Your request has been sent to the owner.")
    except IntegrityError:
        if BookRequest.objects.filter(
            book_id=book_id,
            requester=user,
            status__in=["pending", "accepted"],
        ).exists():
            messages.error(request, "You already have an active request for this book.")
        else:
            logger.exception("Could not save a BookShare request")
            messages.error(request, "We could not send your request. Please try again.")
    return redirect("bookshare")


@require_POST
@signed_in_user
def update_book_request(request, request_id):
    user = request.campushub_user
    action = request.POST.get("action", "")
    with transaction.atomic():
        request_ref = get_object_or_404(
            BookRequest.objects.only("book_id"),
            id=request_id,
        )
        book = Book.objects.select_for_update().get(id=request_ref.book_id)
        book_request = get_object_or_404(
            BookRequest.objects.select_for_update(),
            id=request_id,
        )
        if book.owner_id == user.id and action in {"accept", "reject"} and book_request.status == "pending":
            if (
                action == "accept"
                and book.available_until
                and book.available_until < timezone.localdate()
            ):
                messages.error(request, "This listing has expired and can no longer be accepted.")
            elif action == "accept" and book.status == "requested":
                book_request.status = "accepted"
                book.status = "lent"
                BookRequest.objects.filter(book=book, status="pending").exclude(
                    id=book_request.id
                ).update(status="rejected")
                messages.success(request, "Request accepted. The book is now marked as lent.")
            elif action == "reject":
                book_request.status = "rejected"
                if not BookRequest.objects.filter(
                    book=book, status__in=["pending", "accepted"]
                ).exclude(id=book_request.id).exists():
                    book.status = "available"
                messages.success(request, "Request declined.")
            else:
                messages.error(request, "This listing is no longer available to accept.")
            book_request.save(update_fields=["status"])
            book.save(update_fields=["status"])
        elif (
            user.id in {book.owner_id, book_request.requester_id}
            and book_request.status == "accepted"
            and action == "complete"
        ):
            book_request.status = "completed"
            book.status = "available" if book.action == "borrow" else "closed"
            book_request.save(update_fields=["status"])
            book.save(update_fields=["status"])
            if book.action == "borrow":
                messages.success(request, "Book returned. The listing is available again.")
            else:
                messages.success(request, "Book handoff completed. The listing is now closed.")
        elif (
            user.id == book_request.requester_id
            and book_request.status == "pending"
            and action == "cancel"
        ):
            book_request.status = "rejected"
            book_request.save(update_fields=["status"])
            if not BookRequest.objects.filter(
                book=book, status__in=["pending", "accepted"]
            ).exists():
                book.status = "available"
                book.save(update_fields=["status"])
            messages.success(request, "Your request has been cancelled.")
        else:
            messages.error(request, "This request cannot be updated by your account in its current state.")
    return redirect("bookshare")


@require_http_methods(["GET", "POST"])
@signed_in_user
def skillswap(request):
    user = request.campushub_user
    if request.method == "POST":
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = user
            skill.created_at = timezone.now()
            skill.save()
            messages.success(request, "Your skill has been added to your profile.")
            return redirect("skillswap")
    else:
        form = SkillForm()

    query = request.GET.get("q", "").strip()[:80]
    skill_type = request.GET.get("type", "").strip()
    level = request.GET.get("level", "").strip()
    branch_id = _uuid_or_none(request.GET.get("branch", "").strip())
    listings = (
        Skill.objects.select_related("user", "user__branch")
        .annotate(
            average_rating=Avg("user__received_feedback__rating"),
            rating_count=Count("user__received_feedback", distinct=True),
        )
        .exclude(user=user)
    )
    if query:
        listings = listings.filter(skill_name__icontains=query)
    if skill_type in {"teach", "learn"}:
        listings = listings.filter(type=skill_type)
    if level in {"beginner", "intermediate", "advanced"}:
        listings = listings.filter(level=level)
    if branch_id:
        listings = listings.filter(user__branch_id=branch_id)
    listing_count = listings.count()

    requests = (
        SkillRequest.objects.filter(Q(requester=user) | Q(skill__user=user))
        .select_related("skill", "skill__user", "requester", "offered_skill")
    )
    requests = list(requests[:100])
    feedback = SkillFeedback.objects.filter(reviewee=user).select_related("reviewer")
    feedback_ids = set(
        SkillFeedback.objects.filter(reviewer=user).values_list("request_id", flat=True)
    )
    own_skills = list(Skill.objects.filter(user=user))
    branches = list(Branch.objects.all())
    return render(
        request,
        "portal/skillswap.html",
        {
            "form": form,
            "listings": listings[:100],
            "listing_count": listing_count,
            "own_skills": own_skills,
            "own_teach_skills": [skill for skill in own_skills if skill.type == "teach"],
            "branches": branches,
            "query": query,
            "selected_type": skill_type,
            "selected_level": level,
            "selected_branch": str(branch_id) if branch_id else "",
            "requests": requests,
            "feedback": feedback,
            "feedback_ids": feedback_ids,
        },
    )


@require_POST
@signed_in_user
def request_skill(request, skill_id):
    user = request.campushub_user
    skill = get_object_or_404(Skill.objects.select_related("user"), id=skill_id)
    form = SkillRequestForm(request.POST, requester_id=user.id)
    if skill.type != "teach" or skill.user_id == user.id:
        messages.error(request, "You can only request a skill that another student is offering to teach.")
    elif form.is_valid():
        try:
            SkillRequest.objects.create(
                skill=skill,
                requester=user,
                offered_skill=form.cleaned_data["offered_skill"],
                message=form.cleaned_data["message"].strip(),
                status="pending",
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
        except IntegrityError:
            messages.error(request, "You already have an active request for this skill.")
        else:
            messages.success(request, "Your learning request has been sent.")
    else:
        messages.error(request, "Please check the details in your request.")
    return redirect("skillswap")


@require_POST
@signed_in_user
def update_skill_request(request, request_id):
    user = request.campushub_user
    action = request.POST.get("action", "")
    with transaction.atomic():
        skill_request = get_object_or_404(
            SkillRequest.objects.select_for_update().select_related("skill"),
            id=request_id,
        )
        is_owner = skill_request.skill.user_id == user.id
        is_requester = skill_request.requester_id == user.id
        if action in {"accept", "reject"} and is_owner and skill_request.status == "pending":
            skill_request.status = "accepted" if action == "accept" else "rejected"
            skill_request.updated_at = timezone.now()
            skill_request.save(update_fields=["status", "updated_at"])
            messages.success(request, "The learning request has been updated.")
        elif action == "confirm-completed" and (is_owner or is_requester) and skill_request.status == "accepted":
            now = timezone.now()
            if is_requester and not skill_request.requester_completed_at:
                skill_request.requester_completed_at = now
            if is_owner and not skill_request.owner_completed_at:
                skill_request.owner_completed_at = now
            if skill_request.requester_completed_at and skill_request.owner_completed_at:
                skill_request.status = "completed"
            skill_request.updated_at = now
            skill_request.save(
                update_fields=[
                    "requester_completed_at",
                    "owner_completed_at",
                    "status",
                    "updated_at",
                ]
            )
            messages.success(request, "Your completion has been confirmed.")
        else:
            messages.error(request, "This request cannot be updated by your account in its current state.")
    return redirect("skillswap")


@require_POST
@signed_in_user
def submit_skill_feedback(request, request_id):
    user = request.campushub_user
    skill_request = get_object_or_404(
        SkillRequest.objects.select_related("skill"), id=request_id
    )
    is_participant = user.id in {skill_request.requester_id, skill_request.skill.user_id}
    if not is_participant or skill_request.status != "completed":
        messages.error(request, "Only participants in a completed SkillSwap connection can leave feedback.")
        return redirect("skillswap")
    form = SkillFeedbackForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a rating from 1 to 5 and keep your feedback under 500 characters.")
        return redirect("skillswap")
    reviewee_id = (
        skill_request.skill.user_id
        if skill_request.requester_id == user.id
        else skill_request.requester_id
    )
    try:
        SkillFeedback.objects.create(
            request=skill_request,
            reviewer=user,
            reviewee_id=reviewee_id,
            rating=form.cleaned_data["rating"],
            comment=form.cleaned_data["comment"].strip(),
            created_at=timezone.now(),
        )
    except IntegrityError:
        messages.error(request, "You have already left feedback for this connection.")
    else:
        messages.success(request, "Your feedback has been submitted.")
    return redirect("skillswap")


@require_POST
@signed_in_user
def close_help_request(request, request_id):
    user = request.campushub_user
    help_request = get_object_or_404(HelpRequest, id=request_id)
    if help_request.user_id == user.id or user.role in STAFF_ROLES:
        help_request.status = "resolved"
        help_request.save(update_fields=["status"])
        messages.success(request, "The help request has been marked as resolved.")
    else:
        messages.error(request, "Only the request owner or authorized staff can resolve this request.")
    return redirect("help_requests")


@require_http_methods(["GET", "POST"])
@signed_in_user
def help_requests(request):
    user = request.campushub_user
    if request.method == "POST":
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.user = user
            help_request.status = "open"
            help_request.created_at = timezone.now()
            help_request.save()
            messages.success(request, "Your help request has been shared with the campus.")
            return redirect("help_requests")
    else:
        form = HelpRequestForm()
    items = HelpRequest.objects.select_related("user", "branch")
    if user.branch_id:
        items = items.filter(Q(branch_id=user.branch_id) | Q(branch__isnull=True))
    query = request.GET.get("q", "").strip()[:120]
    terms = _search_terms(query)
    if terms:
        items = items.filter(
            _search_filter(terms, ("title", "description", "status", "branch__name", "branch__code"))
        )
    return render(
        request,
        "portal/help_requests.html",
        {"form": form, "help_requests": items[:100]},
    )


@require_http_methods(["GET", "POST"])
def project_ideas(request):
    if request.method == "POST":
        session_user = request.session.get("campushub_user")
        user_id = session_user.get("id") if isinstance(session_user, dict) else None
        user_id = _uuid_or_none(user_id) if user_id else None
        user = User.objects.filter(id=user_id).first() if user_id else None
        if not user:
            messages.info(request, "Please log in before sharing a project idea.")
            return redirect("login")
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            values = form.cleaned_data
            attachment_url, attachment_name = None, None
            if values["attachment"]:
                try:
                    attachment_url, attachment_name = upload_project_file(
                        values["attachment"]
                    )
                except StorageUploadError as error:
                    form.add_error("attachment", str(error))
            if not form.errors:
                _create_project(user, values, attachment_url, attachment_name)
                messages.success(request, "Your project has been published to the campus directory.")
                return redirect("project_ideas")

    else:
        form = ProjectForm()

    selected_branch = request.GET.get("branch", "").strip().upper()
    selected_level = request.GET.get("level", "").strip().lower()
    ideas = [
        idea for idea in IDEAS
        if (not selected_branch or idea["branch"] == selected_branch)
        and (not selected_level or idea["level"] == selected_level)
    ]
    selected_idea_title = request.GET.get("pick", "").strip()[:160]
    idea = next(
        (item for item in ideas if item["title"] == selected_idea_title),
        ideas[0] if ideas else None,
    )
    surprise_widened_filters = False
    if request.GET.get("next") and ideas:
        previous_title = request.GET.get("exclude", "").strip()[:160]
        alternatives = [item for item in ideas if item["title"] != previous_title]
        if not alternatives and selected_branch:
            branch_ideas = [
                item
                for item in IDEAS
                if item["branch"] == selected_branch and item["title"] != previous_title
            ]
            if branch_ideas:
                ideas = branch_ideas
                alternatives = branch_ideas
                selected_level = ""
                surprise_widened_filters = True
        if not alternatives:
            alternatives = [item for item in IDEAS if item["title"] != previous_title]
            ideas = IDEAS
            selected_branch = ""
            selected_level = ""
            surprise_widened_filters = True
        idea = random.choice(alternatives or ideas)
    if idea:
        selected_idea_title = idea["title"]
    projects = Project.objects.select_related("created_by").all()
    if selected_branch:
        projects = projects.filter(branches__contains=[selected_branch])
    if selected_level in {"beginner", "intermediate", "advanced"}:
        projects = projects.filter(difficulty=selected_level)
    projects = list(projects[:50])
    if sign_storage_references(projects, "attachment_url"):
        messages.error(
            request,
            "One or more project files are temporarily unavailable. Please try again later.",
        )
    return render(
        request,
        "portal/project_ideas.html",
        {
            "form": form,
            "branches": Branch.objects.all(),
            "ideas": ideas,
            "idea": idea,
            "idea_count": len(ideas),
            "projects": projects,
            "selected_branch": selected_branch,
            "selected_level": selected_level,
            "selected_idea_title": selected_idea_title,
            "surprise_widened_filters": surprise_widened_filters,
        },
    )


def _create_project(user, values, attachment_url, attachment_name):
    skills = [
        skill.strip()[:80]
        for skill in values["required_skills"].split(",")
        if skill.strip()
    ][:8]
    Project.objects.create(
        created_by=user,
        title=values["title"].strip(),
        description=values["description"].strip(),
        difficulty=values["difficulty"],
        required_skills=skills,
        branches=[values["branch"].code],
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        created_at=timezone.now(),
    )


def global_search(request):
    query = request.GET.get("q", "").strip()[:120]
    selected_category = request.GET.get("category", "all")
    category_values = {value for value, _label in SEARCH_CATEGORIES}
    if selected_category not in category_values:
        selected_category = "all"

    category_labels = dict(SEARCH_CATEGORIES)
    results = []
    has_more_results = False
    search_user = _session_user(request)
    terms = _search_terms(query)
    if terms:
        def take_first_results(matches):
            nonlocal has_more_results
            matches = list(matches[:11])
            if len(matches) > 10:
                has_more_results = True
            return matches[:10]

        def include(category):
            return selected_category in {"all", category}

        def add_result(kind, title, description, detail, url):
            title_text = str(title or "")
            normalized_title = title_text.casefold()
            normalized_query = query.casefold()
            priority = 0 if normalized_title == normalized_query else (
                1 if normalized_query in normalized_title else 2
            )
            results.append(
                {
                    "kind": kind,
                    "title": title_text,
                    "description": str(description or ""),
                    "detail": str(detail or ""),
                    "url": url,
                    "priority": priority,
                }
            )

        if include("subjects"):
            subject_matches = Subject.objects.select_related("branch").filter(
                _search_filter(terms, ("name", "slug", "branch__name", "branch__code"))
            )
            if search_user and search_user.role not in ADMIN_ROLES:
                subject_matches = (
                    subject_matches.filter(branch_id=search_user.branch_id)
                    if search_user.branch_id
                    else subject_matches.none()
                )
            subjects = take_first_results(subject_matches)
            for subject in subjects:
                add_result(
                    "Subject",
                    subject.name,
                    subject.branch.name,
                    f"{subject.branch.code} · Subject hub",
                    f"/branchhub/subjects/{subject.id}/",
                )

        if include("resources") and search_user:
            note_matches = Note.objects.select_related("subject", "subject__branch").filter(
                    _search_filter(
                        terms,
                        (
                            "title",
                            "description",
                            "file_name",
                            "source_type",
                            "subject__name",
                            "subject__branch__name",
                            "subject__branch__code",
                        ),
                    )
                )
            if search_user.role not in ADMIN_ROLES:
                note_matches = (
                    note_matches.filter(subject__branch_id=search_user.branch_id)
                    if search_user.branch_id
                    else note_matches.none()
                )
            notes = take_first_results(note_matches)
            for note in notes:
                source = "Teacher upload" if note.source_type == Note.SOURCE_TEACHER else "AI study material"
                add_result(
                    "Study resource",
                    note.title,
                    note.description or f"Study material for {note.subject.name}.",
                    f"{source} · {note.subject.name} · {note.subject.branch.code}",
                    f"/branchhub/subjects/{note.subject_id}/",
                )

        if include("tools"):
            tools = take_first_results(
                Tool.objects.select_related("branch", "subject").filter(
                    _search_filter(
                        terms,
                        (
                            "name",
                            "description",
                            "category",
                            "branch__name",
                            "branch__code",
                            "subject__name",
                        ),
                    )
                )
            )
            for tool in tools:
                route = tool.route
                if route not in SUPPORTED_TOOL_ROUTES:
                    route = "/branchhub/"
                context = [tool.category]
                if tool.subject_id:
                    context.append(tool.subject.name)
                if tool.branch_id:
                    context.append(tool.branch.code)
                add_result("Tool", tool.name, tool.description, " · ".join(context), route)
            for branch_code, branch_data in BRANCH_TOOL_CATALOG.items():
                for name, description, route in branch_data["tools"]:
                    searchable = " ".join(
                        (branch_code, branch_data["name"], name, description)
                    ).casefold()
                    if (
                        all(term.casefold() in searchable for term in terms)
                        and not any(
                            item["kind"] == "Tool" and item["title"] == name
                            for item in results
                        )
                    ):
                        add_result(
                            "Tool",
                            name,
                            description,
                            f"{branch_code} · Branch toolkit",
                            route,
                        )

        if include("books"):
            book_matches = (
                Book.objects.select_related("branch")
                .exclude(status="closed")
                .filter(
                    Q(available_until__isnull=True)
                    | Q(available_until__gte=timezone.localdate())
                    | Q(owner=search_user)
                )
                .filter(
                    _search_filter(
                        terms,
                        (
                            "title",
                            "author",
                            "subject",
                            "location",
                            "action",
                            "branch__name",
                            "branch__code",
                        ),
                    )
                )
            )
            books = take_first_results(book_matches)
            for book in books:
                branch = book.branch.code if book.branch else "All branches"
                add_result(
                    "BookShare",
                    book.title,
                    f"{book.author or 'Author not listed'} · {book.subject or 'General'}",
                    f"{book.get_action_display()} · {branch} · {book.status.title()}",
                    f"/bookshare/?q={quote(book.title)}",
                )

        if include("skills"):
            skill_matches = Skill.objects.select_related("user", "user__branch")
            if search_user:
                skill_matches = skill_matches.exclude(user=search_user)
            skills = take_first_results(
                skill_matches.filter(
                    _search_filter(
                        terms,
                        (
                            "skill_name",
                            "type",
                            "level",
                            "user__branch__name",
                            "user__branch__code",
                        ),
                    )
                )
            )
            for skill in skills:
                branch = skill.user.branch.code if skill.user.branch else "All branches"
                add_result(
                    "SkillSwap",
                    skill.skill_name,
                    f"{skill.get_type_display()} · {skill.get_level_display()}",
                    f"{branch} · Connect through SkillSwap",
                    f"/skillswap/?q={quote(skill.skill_name)}",
                )

        if include("projects"):
            projects = take_first_results(
                Project.objects.filter(
                    _search_filter(terms, ("title", "description", "difficulty"))
                )
            )
            for project in projects:
                skills_detail = ", ".join(project.required_skills or [])
                add_result(
                    "Student project",
                    project.title,
                    project.description,
                    f"{str(project.difficulty).replace('_', ' ').title()} · Skills: {skills_detail or 'Not specified'}",
                    "/project-ideas/#community-projects",
                )

        if include("help") and search_user:
            requests = HelpRequest.objects.select_related("branch").filter(
                _search_filter(
                    terms,
                    ("title", "description", "status", "branch__name", "branch__code"),
                )
            )
            if search_user.branch_id:
                requests = requests.filter(
                    Q(branch_id=search_user.branch_id) | Q(branch__isnull=True)
                )
            requests = take_first_results(requests)
            for help_request in requests:
                branch = help_request.branch.code if help_request.branch else "All branches"
                add_result(
                    "Help board",
                    help_request.title,
                    help_request.description,
                    f"{help_request.status.title()} · {branch}",
                    f"/help/?q={quote(help_request.title)}",
                )

        if include("announcements"):
            announcements = take_first_results(
                Announcement.objects.select_related("target_branch").filter(
                    _search_filter(
                        terms,
                        ("title", "message", "target_branch__name", "target_branch__code"),
                    )
                )
            )
            for announcement in announcements:
                branch = announcement.target_branch.code if announcement.target_branch else "Campus-wide"
                add_result(
                    "Announcement",
                    announcement.title,
                    announcement.message,
                    branch,
                    "/",
                )

        if include("branches"):
            branches = take_first_results(
                Branch.objects.filter(_search_filter(terms, ("name", "code")))
            )
            for branch in branches:
                add_result(
                    "Branch",
                    branch.name,
                    f"{branch.code} course community",
                    "Browse subjects, resources and classmates",
                    f"/branchhub/?branch={branch.id}",
                )

        if include("ideas"):
            matching_ideas = []
            for idea in IDEAS:
                searchable = " ".join(
                    [
                        idea["title"],
                        idea["description"],
                        idea["branch"],
                        idea["level"],
                        *idea["skills"],
                        *idea["tools"],
                        *idea["build_steps"],
                    ]
                ).casefold()
                if all(term.casefold() in searchable for term in terms):
                    matching_ideas.append(idea)
            for idea in take_first_results(matching_ideas):
                add_result(
                    "Project idea",
                    idea["title"],
                    idea["description"],
                    f"{idea['branch']} · {idea['level'].title()} · {idea['effort']}",
                    f"/project-ideas/?pick={quote(idea['title'])}#featured-idea",
                )

        results.sort(key=lambda result: result["priority"])
        result_limit = 60
        has_more_results = has_more_results or len(results) > result_limit
        results = results[:result_limit]

    return render(
        request,
        "portal/search.html",
        {
            "query": query,
            "results": results,
            "result_count": len(results),
            "has_more_results": has_more_results,
            "categories": SEARCH_CATEGORIES,
            "selected_category": selected_category,
            "selected_category_label": category_labels[selected_category],
            "search_empty_hint": (
                "Log in to search help requests visible to your branch."
                if selected_category == "help"
                and not getattr(request, "campushub_user", None)
                else ""
            ),
        },
    )
