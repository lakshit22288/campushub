import base64
import hashlib
import json
import time
import uuid
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

import bcrypt
import httpx
from django import forms
from django.db import IntegrityError, OperationalError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from portal import auth
from portal.branch_tool_catalog import BRANCH_TOOL_CATALOG, BRANCH_TOOL_SLUGS
from portal.branch_tool_views import BranchToolForm, branch_tool_groups
from portal.forms import (
    AnnouncementForm,
    AssignmentEntryForm,
    BookListingForm,
    CampusEventForm,
    NoteForm,
    ProjectForm,
    ScheduleEntryForm,
)
from portal.idea_catalog import IDEAS
from portal.storage import (
    StorageUploadError,
    upload_announcement_file,
    upload_note_file,
    upload_project_file,
    signed_storage_url,
)
from campushub.settings import postgres_settings


class PortalPageTests(SimpleTestCase):
    def set_logged_in_user(self, user_id):
        session = self.client.session
        session["campushub_user"] = {"id": str(user_id)}
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

    @patch("portal.views.Announcement.objects.select_related")
    @patch("portal.views.Branch.objects.all")
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_home_renders_campus_design_and_branch_data(self, branches_query, announcements_query):
        branches_query.return_value = [
            type("BranchRow", (), {"id": "branch-1", "name": "Computer Science / IT", "code": "CSE", "icon": ""})()
        ]
        announcements_query.return_value.all.return_value = []

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CampuZHub")
        self.assertContains(response, '<a class="brand" href="/" aria-label="CampuZHub home">')
        self.assertContains(response, '<img class="brand-wordmark" src="/static/python/campuzhub-wordmark.png" alt="CampuZHub">')
        self.assertContains(response, '<link rel="icon" type="image/svg+xml" href="/static/python/campuzhub-mark.svg">')
        self.assertNotContains(response, "Your campus, in one place.")
        self.assertContains(response, '"name":"CampuZHub"')
        self.assertContains(response, "YOUR CAMPUS, IN MOTION")
        self.assertContains(response, "Learn something.")
        self.assertContains(response, "QUICK START / PYTHON")
        self.assertContains(response, "Computer Science / IT")
        self.assertContains(response, "/static/styles/global.css")
        self.assertContains(response, "/static/styles/global.css?v=44")
        self.assertContains(response, "/static/python/python.css?v=44")
        self.assertContains(response, 'name="description"')
        self.assertContains(
            response,
            '<meta name="google-site-verification" content="NxuHJKI0DXW3RZZak_86nkclsPrbCCLeY8rQG4729Yc">',
        )
        self.assertContains(response, 'rel="canonical" href="https://campushub-python.vercel.app/"')
        self.assertContains(response, 'application/ld+json')

    def test_robots_txt_disallows_private_or_non_page_routes_and_links_sitemap(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /profile/")
        self.assertContains(
            response,
            "Sitemap: https://campushub-python.vercel.app/sitemap.xml",
        )

    def test_sitemap_contains_only_public_site_and_tool_pages(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertContains(response, "https://campushub-python.vercel.app/")
        self.assertContains(response, "https://campushub-python.vercel.app/tools/percentage/")
        self.assertContains(response, "https://campushub-python.vercel.app/branch-tools/stress-strain/")
        self.assertContains(response, "https://campushub-python.vercel.app/branch-tools/mlt-terminology/")
        self.assertNotContains(response, "/admin/")
        self.assertNotContains(response, "/profile/")

    def test_login_page_is_marked_noindex(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex,nofollow">')

    def test_email_confirmation_page_handles_supabase_redirect_tokens(self):
        response = self.client.get("/auth/email/confirm/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "window.location.hash.slice(1)")
        self.assertContains(response, "/auth/email/complete/")
        self.assertContains(response, "window.history.replaceState")

    def test_signup_confirmation_highlights_spam_folder_guidance(self):
        content = render_to_string(
            "portal/register.html",
            {
                "database_configured": True,
                "confirmation_sent": True,
                "confirmation_email": "student@example.edu",
            },
        )

        self.assertIn('class="notice notice-warning email-delivery-tip"', content)
        self.assertIn("Check your Spam or Junk folder", content)
        self.assertIn("mark it as “Not spam”", content)
        self.assertIn("request a new verification link", content)

    @patch("portal.features.Skill.objects.select_related")
    def test_global_search_splits_terms_and_shows_skill_context(self, skills_query):
        branch = SimpleNamespace(code="CSE")
        skill = SimpleNamespace(
            skill_name="Python",
            user=SimpleNamespace(branch=branch),
            get_type_display=lambda: "Teach",
            get_level_display=lambda: "Advanced",
        )
        skills_query.return_value.filter.return_value = [skill]

        response = self.client.get(
            "/search/", {"q": "Python design", "category": "skills"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matches for “Python design”")
        self.assertContains(response, "Python")
        self.assertContains(response, "Teach · Advanced")
        self.assertContains(response, "CSE · Connect through SkillSwap")
        self.assertContains(response, "/skillswap/?q=Python")
        search_filter = repr(skills_query.return_value.filter.call_args.args[0])
        self.assertIn("skill_name__icontains', 'Python'", search_filter)
        self.assertIn("skill_name__icontains', 'design'", search_filter)
        self.assertNotIn("Python design", search_filter)

    @patch("portal.features.Skill.objects.select_related")
    def test_global_search_category_filter_has_a_useful_empty_state(self, skills_query):
        skills_query.return_value.filter.return_value = []

        response = self.client.get(
            "/search/", {"q": "unknown topic", "category": "skills"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No matches in SkillSwap.")
        self.assertContains(response, 'name="category"')
        self.assertContains(response, "Everything")

    @patch("portal.features.HelpRequest.objects.select_related")
    def test_global_search_does_not_expose_help_requests_to_anonymous_users(
        self, help_requests_query
    ):
        response = self.client.get(
            "/search/", {"q": "exam help", "category": "help"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in to search help requests visible to your branch.")
        help_requests_query.assert_not_called()

    @patch("portal.views.Announcement.objects.select_related")
    @patch("portal.views.Branch.objects.all", return_value=[])
    def test_campus_notices_open_a_dialog_with_optional_attachment(
        self, branches_query, announcements_query
    ):
        announcement = SimpleNamespace(
            title="Library hours update",
            message="The library will stay open later during exam week.",
            target_branch=None,
            created_at=timezone.now(),
            attachment_url="https://files.example.invalid/announcements/hours.pdf",
            attachment_name="hours.pdf",
        )
        announcements_query.return_value.all.return_value = [announcement]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-haspopup="dialog"')
        self.assertContains(response, 'id="campus-notice-dialog"')
        self.assertContains(response, 'data-notice-title="Library hours update"')
        self.assertContains(response, 'data-notice-filename="hours.pdf"')
        self.assertContains(response, "dialog.showModal()")

    @patch("portal.features.Note.objects.select_related")
    @patch("portal.features._session_user")
    def test_global_search_limits_resources_to_the_signed_in_students_branch(
        self, user_query, notes_query
    ):
        branch_id = uuid.uuid4()
        user = SimpleNamespace(id=uuid.uuid4(), role="student", branch_id=branch_id)
        user_query.return_value = user
        notes_manager = MagicMock()
        searched_notes = MagicMock()
        notes_manager.filter.return_value = searched_notes
        searched_notes.filter.return_value = []
        notes_query.return_value = notes_manager

        response = self.client.get(
            "/search/", {"q": "private notes", "category": "resources"}
        )

        self.assertEqual(response.status_code, 200)
        searched_notes.filter.assert_called_once_with(subject__branch_id=branch_id)

    @patch("portal.features.Note.objects.select_related")
    def test_anonymous_global_search_does_not_search_study_resources(
        self, notes_query
    ):
        response = self.client.get(
            "/search/", {"q": "private notes", "category": "resources"}
        )

        self.assertEqual(response.status_code, 200)
        notes_query.assert_not_called()

    def test_code_lab_keeps_its_separate_existing_shell(self):
        response = self.client.get("/compiler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<body class="code-lab-page">')
        self.assertContains(response, '<img class="brand-wordmark" src="/static/python/campuzhub-wordmark.png" alt="CampuZHub">')
        self.assertContains(response, "CampuZHub • Open-source student ecosystem • Built for campus use")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_home_explains_database_is_not_configured(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect to CampuZHub to see your branch communities.")

    @patch("portal.features.Subject.objects.select_related", return_value=[])
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_branchhub_filter_has_an_explicit_submit_and_empty_state(
        self, branches_query, subjects_query
    ):
        response = self.client.get("/branchhub/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="branch-filter"')
        self.assertContains(response, "Explore subjects")
        self.assertContains(response, "No subjects are in the catalog yet.")
        self.assertNotContains(response, "onchange=")
        self.assertContains(response, "Branch toolkits.")
        self.assertContains(response, "HTML / CSS / JavaScript Playground")
        self.assertContains(response, "Lab Safety Practice")

    def test_branch_tool_groups_cover_every_live_branch(self):
        branches = [
            SimpleNamespace(code=code, name=name)
            for code, name in (
                ("CE", "Civil Engineering"),
                ("CSE", "Computer Science / IT"),
                ("EE", "Electrical Engineering"),
                ("ECE", "Electronics and Communication Engineering (ECE)"),
                ("ME", "Mechanical Engineering"),
                ("MLT", "Medical Laboratory Technology"),
            )
        ]

        groups = branch_tool_groups(branches)

        self.assertEqual({group["code"] for group in groups}, set(BRANCH_TOOL_CATALOG))
        self.assertTrue(all(len(group["tools"]) >= 5 for group in groups))
        cse_tools = next(group["tools"] for group in groups if group["code"] == "CSE")
        self.assertNotIn("/tools/subnet/", [tool["route"] for tool in cse_tools])

    def test_selected_student_branch_gets_only_its_toolkit(self):
        branches = [
            SimpleNamespace(code="CSE", name="Computer Science / IT"),
            SimpleNamespace(code="CE", name="Civil Engineering"),
        ]

        groups = branch_tool_groups(branches, branches[0])

        self.assertEqual([group["code"] for group in groups], ["CSE"])
        self.assertIn("/branch-tools/dsa-practice/", [tool["route"] for tool in groups[0]["tools"]])

    @patch("portal.views.Branch.objects.all")
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_branch_directory_links_to_the_selected_course(self, branches_query):
        branch_id = uuid.uuid4()
        branches_query.return_value = [
            type(
                "BranchRow",
                (),
                {
                    "id": branch_id,
                    "name": "Computer Science / IT",
                    "code": "CSE",
                },
            )()
        ]

        response = self.client.get("/branches/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"/branchhub/?branch={branch_id}")
        self.assertContains(response, "Find your people.")

    @patch("portal.features.Subject.objects.select_related", return_value=[])
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_branchhub_marks_the_current_navigation_link(
        self, branches_query, subjects_query
    ):
        response = self.client.get("/branchhub/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<a href="/branchhub/" class="active" aria-current="page">BranchHub</a>',
        )

    @patch("portal.features.Subject.objects.select_related")
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_branchhub_paginates_subjects_without_losing_page_context(
        self, branches_query, subjects_query
    ):
        branch = type(
            "BranchRow",
            (),
            {"id": uuid.uuid4(), "code": "CSE", "name": "Computer Science"},
        )()
        branches_query.return_value = [branch]
        class SubjectRows(list):
            def filter(self, **kwargs):
                return self

        subjects_query.return_value = SubjectRows([
            type(
                "SubjectRow",
                (),
                {"id": uuid.uuid4(), "name": f"Subject {index}", "branch": branch},
            )()
            for index in range(20)
        ])

        response = self.client.get(f"/branchhub/?branch={branch.id}&page=2")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, 'class="branchhub-hero"')
        self.assertContains(response, 'class="subject-tile"')
        self.assertContains(response, "OPEN STUDY SPACE")
        self.assertEqual(len(response.context["page_obj"].object_list), 2)
        self.assertContains(
            response,
            f"?branch={branch.id}&amp;page=1",
        )

    @patch("portal.features.User.objects.filter")
    @patch("portal.features.Branch.objects.all")
    @patch("portal.features.Subject.objects.select_related")
    def test_branchhub_allows_students_to_filter_another_branch(
        self, subjects_query, branches_query, user_query
    ):
        own_branch_id, other_branch_id = uuid.uuid4(), uuid.uuid4()
        own_branch = SimpleNamespace(id=own_branch_id, code="CSE", name="Computer Science")
        other_branch = SimpleNamespace(id=other_branch_id, code="EE", name="Electrical Engineering")
        own_subject = SimpleNamespace(
            id=uuid.uuid4(), branch_id=own_branch_id, branch=own_branch, name="Algorithms"
        )
        other_subject = SimpleNamespace(
            id=uuid.uuid4(), branch_id=other_branch_id, branch=other_branch, name="Circuits"
        )

        class SubjectRows(list):
            def filter(self, **kwargs):
                return SubjectRows(
                    subject for subject in self
                    if subject.branch_id == kwargs["branch_id"]
                )

            def none(self):
                return SubjectRows()

        user = SimpleNamespace(id=uuid.uuid4(), role="student", branch_id=own_branch_id)
        self.set_logged_in_user(user.id)
        user_query.return_value.first.return_value = user
        branches_query.return_value = [own_branch, other_branch]
        subjects_query.return_value = SubjectRows([own_subject, other_subject])

        response = self.client.get(f"/branchhub/?branch={other_branch_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [subject.name for subject in response.context["page_obj"].object_list],
            ["Circuits"],
        )
        self.assertEqual(response.context["branch_filter"], str(other_branch_id))

    @patch("portal.features.Tool.objects.filter", return_value=[])
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.Note.objects.filter")
    @patch("portal.features.get_object_or_404")
    def test_subject_detail_separates_teacher_and_ai_resources(
        self, get_subject, notes_filter, user_query, tools_filter
    ):
        subject = SimpleNamespace(
            id=uuid.uuid4(),
            branch_id=uuid.uuid4(),
            name="Circuit Analysis",
            branch=SimpleNamespace(name="Electrical Engineering", code="EE"),
        )
        get_subject.return_value = subject
        user = SimpleNamespace(
            id=uuid.uuid4(),
            role="student",
            branch_id=subject.branch_id,
        )
        self.set_logged_in_user(user.id)
        user_query.return_value.first.return_value = user
        teacher_note = SimpleNamespace(
            title="Faculty lecture notes",
            description="Classroom upload",
            created_at=timezone.now(),
            created_by=SimpleNamespace(name="A. Teacher", role="teacher"),
            file_url=None,
            file_name=None,
        )
        ai_note = SimpleNamespace(
            title="AI circuit revision guide",
            description="AI-generated overview",
            created_at=timezone.now(),
            created_by=None,
            file_url=None,
            file_name=None,
        )
        teacher_query, ai_query = MagicMock(), MagicMock()
        teacher_query.select_related.return_value = [teacher_note]
        ai_query.select_related.return_value = [ai_note]
        notes_filter.side_effect = [teacher_query, ai_query]

        response = self.client.get(f"/branchhub/subjects/{subject.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher uploads")
        self.assertContains(response, "AI study material")
        self.assertContains(response, "Faculty lecture notes")
        self.assertContains(response, "AI circuit revision guide")
        self.assertContains(response, "Electrical Engineering faculty")
        self.assertNotContains(response, "A. Teacher")
        self.assertEqual(notes_filter.call_args_list[0].kwargs["source_type"], "teacher")
        self.assertEqual(notes_filter.call_args_list[1].kwargs["source_type"], "ai")

    @patch("portal.features.Note.objects.filter")
    @patch("portal.features.get_object_or_404")
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.Tool.objects.filter", return_value=[])
    def test_subject_detail_allows_students_from_other_branches(
        self, tools_filter, user_query, get_subject, notes_filter
    ):
        user = SimpleNamespace(
            id=uuid.uuid4(),
            role="student",
            branch_id=uuid.uuid4(),
        )
        subject = SimpleNamespace(
            id=uuid.uuid4(),
            branch_id=uuid.uuid4(),
            branch=SimpleNamespace(name="Electrical Engineering", code="EE"),
        )
        self.set_logged_in_user(user.id)
        user_query.return_value.first.return_value = user
        get_subject.return_value = subject
        notes_filter.return_value.select_related.return_value = []

        response = self.client.get(f"/branchhub/subjects/{subject.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subject"], subject)
        self.assertEqual(notes_filter.call_count, 2)

    def test_teacher_note_form_cannot_choose_ai_material(self):
        teacher_form = NoteForm(user_role="teacher")
        admin_form = NoteForm(user_role="admin")

        self.assertEqual(
            [value for value, _ in teacher_form.fields["source_type"].choices],
            ["teacher"],
        )
        self.assertEqual(
            [value for value, _ in admin_form.fields["source_type"].choices],
            ["teacher", "ai"],
        )

    def test_notice_attachment_is_available_to_admins_but_not_teachers(self):
        admin_form = AnnouncementForm(user_role="admin")
        super_admin_form = AnnouncementForm(user_role="super_admin")
        teacher_form = AnnouncementForm(user_role="teacher")

        self.assertIn("attachment", admin_form.fields)
        self.assertIn("attachment", super_admin_form.fields)
        self.assertNotIn("attachment", teacher_form.fields)

    def test_event_form_rejects_end_time_before_start_time(self):
        form = CampusEventForm(
            data={
                "title": "Campus talk",
                "description": "Guest speaker",
                "location": "Auditorium",
                "starts_at": "2026-10-18T14:00",
                "ends_at": "2026-10-18T13:00",
                "target_branch": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("ends_at", form.errors)

    def test_schedule_form_rejects_end_time_before_start_time(self):
        form = ScheduleEntryForm(
            data={
                "course": "Database Systems",
                "day_of_week": "0",
                "start_time": "11:00",
                "end_time": "10:00",
                "location": "Room 101",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

    def test_assignment_form_accepts_due_date_and_notes(self):
        form = AssignmentEntryForm(
            data={
                "title": "Lab report",
                "subject": "Physics",
                "due_date": "2026-10-20",
                "notes": "Include the calculation steps.",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_planner_redirects_signed_out_visitors_to_login(self):
        response = self.client.get("/planner/")

        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

    @patch("portal.features.User.objects.filter")
    @patch("portal.planner_views.AssignmentEntry.objects.filter", return_value=[])
    @patch("portal.planner_views.ScheduleEntry.objects.filter")
    def test_signed_in_student_can_render_a_private_planner(
        self, schedule_filter, assignment_filter, user_filter
    ):
        user = SimpleNamespace(id=uuid.uuid4(), role="student", branch_id=None)
        self.set_logged_in_user(user.id)
        user_filter.return_value.first.return_value = user
        schedule_filter.return_value.order_by.return_value = []

        response = self.client.get("/planner/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your timetable is empty.")
        self.assertContains(response, "No assignments yet.")
        schedule_filter.assert_called_once_with(user=user)
        assignment_filter.assert_called_once_with(user=user)

    @patch("portal.features.User.objects.filter")
    @patch("portal.planner_views.AssignmentEntry.objects.filter")
    def test_planner_mutations_are_scoped_to_the_signed_in_user(
        self, assignment_filter, user_filter
    ):
        user = SimpleNamespace(id=uuid.uuid4(), role="student", branch_id=None)
        assignment_id = uuid.uuid4()
        self.set_logged_in_user(user.id)
        user_filter.return_value.first.return_value = user
        assignment_filter.return_value.delete.return_value = (1, {"portal.AssignmentEntry": 1})

        response = self.client.post(
            "/planner/",
            {"action": "delete_assignment", "entry_id": str(assignment_id)},
        )

        self.assertRedirects(response, "/planner/", fetch_redirect_response=False)
        assignment_filter.assert_called_once_with(id=assignment_id, user=user)

    @patch("portal.planner_views.CampusEvent.objects.select_related")
    @patch("portal.planner_views.Announcement.objects.select_related")
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_public_campus_board_limits_updates_to_campus_wide_posts(
        self, notices_query, events_query
    ):
        notices_query.return_value.filter.return_value.order_by.return_value.__getitem__.return_value = []
        events = events_query.return_value.filter.return_value
        events.filter.return_value = events
        events.select_related.return_value.order_by.return_value.__getitem__.return_value = []

        response = self.client.get("/campus/")

        self.assertEqual(response.status_code, 200)
        notices_query.return_value.filter.assert_called_once_with(target_branch__isnull=True)
        events_query.return_value.filter.assert_called_once_with(ends_at__gte=ANY)
        events.filter.assert_called_once_with(target_branch__isnull=True)

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_campus_board_renders_without_connecting_to_any_database(self):
        response = self.client.get("/campus/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect this local app to a safe development database")
        self.assertContains(response, "No upcoming events have been posted yet.")

    @patch("portal.admin_views.messages.success")
    @patch("portal.admin_views.upload_announcement_file")
    @patch("portal.admin_views.AnnouncementForm")
    def test_admin_notice_upload_saves_uploaded_attachment(
        self, form_factory, upload_file, success_message
    ):
        from portal.admin_views import _staff_form

        uploaded_file = SimpleUploadedFile(
            "campus-update.pdf",
            b"%PDF-1.7 notice",
            content_type="application/pdf",
        )
        announcement = SimpleNamespace(target_branch_id=None, save=MagicMock())
        form = MagicMock()
        form.is_valid.return_value = True
        form.cleaned_data = {"attachment": uploaded_file}
        form.save.return_value = announcement
        form_factory.return_value = form
        upload_file.return_value = (
            "https://files.example.invalid/announcements/update.pdf",
            "campus-update.pdf",
        )
        request = RequestFactory().post("/admin/", {"action": "announcement"})
        user = SimpleNamespace(
            role="admin",
            branch_id=None,
            id=uuid.uuid4(),
        )

        result = _staff_form(request, user)

        self.assertEqual(result["Location"], "/admin/")
        upload_file.assert_called_once_with(uploaded_file)
        self.assertEqual(
            announcement.attachment_url,
            "https://files.example.invalid/announcements/update.pdf",
        )
        self.assertEqual(announcement.attachment_name, "campus-update.pdf")
        announcement.save.assert_called_once()

    @patch("portal.features.Project.objects.select_related")
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_project_ideas_show_the_whole_filtered_library(
        self, branches_query, projects_query
    ):
        project_rows = MagicMock()
        project_rows.filter.return_value = project_rows
        project_rows.__getitem__.return_value = []
        projects_query.return_value.all.return_value = project_rows

        response = self.client.get("/project-ideas/?branch=CSE")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["idea_count"], 3)
        self.assertEqual(len(response.context["ideas"]), 3)
        self.assertContains(response, "Browse the collection")
        self.assertContains(response, "Study Group Matchmaker")
        self.assertContains(response, "Lab Equipment Tracker")
        self.assertContains(response, "How to build it")
        self.assertContains(response, "Sketch two screens")
        self.assertContains(response, "SUGGESTED TOOLS")

    @patch("portal.features.random.choice")
    @patch("portal.features.Project.objects.select_related")
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_project_ideas_surprise_selects_a_different_matching_idea(
        self, branches_query, projects_query, choose_idea
    ):
        project_rows = MagicMock()
        project_rows.filter.return_value = project_rows
        project_rows.__getitem__.return_value = []
        projects_query.return_value.all.return_value = project_rows
        current_idea = IDEAS[0]
        chosen_idea = IDEAS[1]
        choose_idea.return_value = chosen_idea

        response = self.client.get(
            "/project-ideas/",
            {"next": "1", "exclude": current_idea["title"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["idea"], chosen_idea)
        candidates = choose_idea.call_args.args[0]
        self.assertIn(chosen_idea, candidates)
        self.assertNotIn(current_idea, candidates)

    @patch("portal.features.random.choice")
    @patch("portal.features.Project.objects.select_related")
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_project_ideas_surprise_expands_when_filters_have_only_one_match(
        self, branches_query, projects_query, choose_idea
    ):
        project_rows = MagicMock()
        project_rows.filter.return_value = project_rows
        project_rows.__getitem__.return_value = []
        projects_query.return_value.all.return_value = project_rows
        current_idea = IDEAS[0]
        chosen_idea = IDEAS[1]
        choose_idea.return_value = chosen_idea

        response = self.client.get(
            "/project-ideas/",
            {
                "branch": current_idea["branch"],
                "level": current_idea["level"],
                "next": "1",
                "exclude": current_idea["title"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["idea"], chosen_idea)
        self.assertEqual(response.context["selected_branch"], current_idea["branch"])
        self.assertEqual(response.context["selected_level"], "")
        self.assertTrue(response.context["surprise_widened_filters"])
        self.assertContains(response, "we widened your selection")

    @patch("portal.features.Project.objects.select_related")
    @patch("portal.features.Branch.objects.all", return_value=[])
    def test_project_idea_cards_open_the_selected_idea(
        self, branches_query, projects_query
    ):
        project_rows = MagicMock()
        project_rows.filter.return_value = project_rows
        project_rows.__getitem__.return_value = []
        projects_query.return_value.all.return_value = project_rows

        response = self.client.get("/project-ideas/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pick=Campus%20Lost%20%26%20Found%20Board")
        self.assertEqual(len(response.context["ideas"]), len(IDEAS))
        self.assertTrue(
            all(
                len(idea["build_steps"]) >= 3 and idea["tools"]
                for idea in response.context["ideas"]
            )
        )

    def test_project_upload_requires_one_branch_selection(self):
        form = ProjectForm(
            {
                "title": "Campus Sensor",
                "description": "A student-built sensor project.",
                "difficulty": "beginner",
                "required_skills": "",
                "branch": "",
            }
        )

        self.assertTrue(form.fields["branch"].required)
        self.assertNotIsInstance(form.fields["branch"].widget, forms.SelectMultiple)
        self.assertFalse(form.is_valid())
        self.assertIn("branch", form.errors)

    @patch("portal.features.render")
    @patch("portal.features.Branch.objects.all", return_value=[])
    @patch("portal.features.Project.objects.select_related")
    @patch("portal.features.Project.objects.create")
    @patch("portal.features.upload_project_file", return_value=("https://files.test/project.zip", "project.zip"))
    @patch("portal.features.User.objects.filter")
    def test_student_project_upload_is_saved_and_linked(
        self, user_query, upload, create_project, projects_query, branches_query, render
    ):
        user = SimpleNamespace(id=uuid.uuid4())
        branch = SimpleNamespace(id=uuid.uuid4(), code="CSE")
        user_query.return_value.first.return_value = user
        project_rows = MagicMock()
        project_rows.__getitem__.return_value = []
        projects_query.return_value.all.return_value = project_rows
        uploaded_file = SimpleUploadedFile(
            "project.zip",
            b"PK\x03\x04project",
            content_type="application/zip",
        )
        session_request = RequestFactory().post(
            "/project-ideas/",
            {
                "title": "Campus Sensor",
                "description": "A student-built sensor project.",
                "difficulty": "beginner",
                "required_skills": "Python, Electronics",
                "branch": str(branch.id),
                "attachment": uploaded_file,
            },
        )
        SessionMiddleware(lambda request: None).process_request(session_request)
        session_request.session["campushub_user"] = {"id": str(user.id)}
        session_request.session.save()
        session_request._messages = FallbackStorage(session_request)
        project_form = MagicMock()
        project_form.is_valid.return_value = True
        project_form.cleaned_data = {
            "title": "Campus Sensor",
            "description": "A student-built sensor project.",
            "difficulty": "beginner",
            "required_skills": "Python, Electronics",
            "branch": branch,
            "attachment": uploaded_file,
        }
        project_form.errors = {}

        from portal.features import project_ideas

        with patch("portal.features.ProjectForm", return_value=project_form):
            response = project_ideas(session_request)

        self.assertEqual(response.status_code, 302)
        upload.assert_called_once()
        self.assertEqual(
            create_project.call_args.kwargs["branches"],
            ["CSE"],
        )
        create_project.assert_called_once()
        self.assertEqual(
            create_project.call_args.kwargs["attachment_url"],
            "https://files.test/project.zip",
        )
        self.assertEqual(create_project.call_args.kwargs["attachment_name"], "project.zip")

    @patch("portal.views.connection.ensure_connection")
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_health_reports_database_connected(self, ensure_connection):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")

    @patch("portal.views.connection.ensure_connection", side_effect=OperationalError("offline"))
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_health_reports_database_unavailable(self, ensure_connection):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "disconnected")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_health_reports_database_not_configured(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "not_configured")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_login_explains_database_is_not_configured(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "existing Supabase database", status_code=503)

class DatabaseConfigurationTests(SimpleTestCase):
    def test_supabase_connection_url_enables_ssl_without_changing_schema(self):
        config = postgres_settings(
            "postgresql://aws-0-us-east-1.pooler.supabase.com:5432/postgres"
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["PASSWORD"], "")
        self.assertEqual(config["OPTIONS"]["sslmode"], "require")
        self.assertEqual(config["CONN_MAX_AGE"], 0)

    def test_rejects_non_postgres_database_urls(self):
        with self.assertRaises(ValueError):
            postgres_settings("https://database.example")


class GoogleOAuthTests(SimpleTestCase):
    def make_request(self):
        request = RequestFactory().get("/auth/google/")
        SessionMiddleware(lambda current_request: None).process_request(request)
        return request

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
        DJANGO_PUBLIC_URL="https://campushub.example",
    )
    def test_oauth_redirect_uses_production_callback_and_pkce(self):
        request = self.make_request()

        authorize_url = auth.begin_google_oauth(request)
        query = parse_qs(urlparse(authorize_url).query)
        verifier = request.session["google_pkce_verifier"]
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")

        self.assertEqual(query["provider"], ["google"])
        self.assertEqual(query["redirect_to"], ["https://campushub.example/auth/callback"])
        self.assertEqual(query["code_challenge"], [expected_challenge])
        self.assertEqual(query["code_challenge_method"], ["s256"])
        self.assertTrue(0 < len(verifier) <= 128)

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
    )
    def test_code_exchange_verifies_google_identity_and_consumes_verifier(self):
        request = self.make_request()
        request.session["google_pkce_verifier"] = "one-time-verifier"
        request.session["google_started_at"] = int(time.time())
        post_response = SimpleNamespace(status_code=200, json=lambda: {"access_token": "short-lived-token"})
        user_response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "email": "Student@Example.edu",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
                "app_metadata": {"provider": "google"},
                "user_metadata": {"full_name": "Campus Student"},
                "identities": [{"provider": "google"}],
            },
        )
        http_client = MagicMock()
        http_client.post.return_value = post_response
        http_client.get.return_value = user_response

        with patch("portal.auth.httpx.Client") as client_factory:
            client_factory.return_value.__enter__.return_value = http_client
            profile = auth.exchange_google_code(request, "authorization-code")

        self.assertEqual(profile, {"email": "student@example.edu", "name": "Campus Student"})
        self.assertNotIn("google_pkce_verifier", request.session)
        self.assertNotIn("google_started_at", request.session)
        self.assertEqual(http_client.post.call_args.kwargs["json"]["code_verifier"], "one-time-verifier")
        self.assertEqual(
            http_client.get.call_args.kwargs["headers"]["Authorization"],
            "Bearer short-lived-token",
        )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
    )
    def test_rejects_expired_oauth_verifier(self):
        request = self.make_request()
        request.session["google_pkce_verifier"] = "expired-verifier"
        request.session["google_started_at"] = int(time.time()) - 601

        with self.assertRaises(auth.SupabaseAuthError):
            auth.exchange_google_code(request, "authorization-code")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_google_profile_passes_database_ready_state_to_template(self):
        request = RequestFactory().get("/auth/profile/")
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.session["google_pending_profile"] = {
            "email": "new-student@example.edu",
            "name": "New Student",
        }

        with patch("portal.views.render") as render:
            from portal.views import google_profile

            google_profile(request)

        self.assertTrue(render.call_args.args[2]["database_configured"])

    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    @patch("portal.views.auth.begin_email_signup")
    @patch("portal.views.auth.sign_in_with_email_password", return_value=None)
    def test_legacy_password_login_requires_email_verification(
        self, sign_in, begin_email_signup
    ):
        password_hash = bcrypt.hashpw(b"student-password", bcrypt.gensalt(rounds=4)).decode()
        user = SimpleNamespace(
            id="user-id",
            name="Student",
            email="student@example.edu",
            password_hash=password_hash,
            role="student",
            branch_id=None,
            semester=None,
        )
        with patch("portal.auth.find_user_by_email", return_value=user):
            response = self.client.post(
                "/login/",
                {"email": user.email, "password": "student-password"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We sent a verification link to your email.")
        self.assertNotIn("campushub_user", self.client.session)
        begin_email_signup.assert_called_once()
        self.assertTrue(begin_email_signup.call_args.args[3]["campushub_signup"])


class EmailVerificationTests(SimpleTestCase):
    def make_post_request(self, path, data):
        request = RequestFactory().post(path, data)
        SessionMiddleware(lambda current_request: None).process_request(request)
        return request

    @patch("portal.views.User.objects.create")
    @patch("portal.views.auth.get_verified_email_identity")
    def test_confirmation_rejects_invalid_or_unverified_links(
        self, verify_identity, create_user
    ):
        verify_identity.side_effect = auth.SupabaseAuthError(
            "This email address has not been verified."
        )
        request = self.make_post_request(
            "/auth/email/complete/", {"access_token": "unverified-token"}
        )

        from portal.views import complete_email_confirmation

        response = complete_email_confirmation(request)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(json.loads(response.content)["error"])
        create_user.assert_not_called()

    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    @patch("portal.views.auth.set_user_session")
    @patch("portal.views.bcrypt.hashpw", return_value=b"unusable-hash")
    @patch("portal.views.transaction.atomic", return_value=nullcontext())
    @patch("portal.views.User.objects.create")
    @patch("portal.views.auth.find_user_by_email", return_value=None)
    @patch("portal.views.auth.get_verified_email_identity")
    def test_verified_email_creates_student_account_and_session(
        self,
        verify_identity,
        find_user,
        create_user,
        atomic,
        hash_password,
        set_session,
    ):
        user = SimpleNamespace(id=uuid.uuid4(), email="new@example.edu")
        create_user.return_value = user
        verify_identity.return_value = {
            "email": "new@example.edu",
            "email_confirmed_at": "2026-10-14T00:00:00Z",
            "user_metadata": {
                "campushub_signup": True,
                "campushub_name": "New Student",
                "campushub_branch_id": None,
                "campushub_semester": None,
            },
        }
        request = self.make_post_request(
            "/auth/email/complete/", {"access_token": "verified-token"}
        )

        from portal.views import complete_email_confirmation

        response = complete_email_confirmation(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], "/branchhub/")
        self.assertEqual(create_user.call_args.kwargs["email"], "new@example.edu")
        self.assertEqual(create_user.call_args.kwargs["role"], "student")
        set_session.assert_called_once_with(request, user)

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
        DJANGO_PUBLIC_URL="https://campushub.example",
        ALLOWED_HOSTS=["testserver"],
    )
    def test_email_signup_uses_the_public_confirmation_callback_and_requires_confirmation(
        self,
    ):
        request = RequestFactory().post("/register/")
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "user": {
                    "id": "auth-user-id",
                    "email": "student@example.edu",
                    "email_confirmed_at": None,
                    "identities": [{"provider": "email"}],
                }
            },
        )
        client = MagicMock()
        client.post.return_value = response

        with patch("portal.auth.httpx.Client") as client_factory:
            client_factory.return_value.__enter__.return_value = client
            auth.begin_email_signup(
                request,
                "student@example.edu",
                "student-password",
                {"campushub_signup": True},
            )

        self.assertEqual(
            client.post.call_args.args[0],
            "https://campus-project.supabase.co/auth/v1/signup",
        )
        self.assertEqual(
            client.post.call_args.kwargs["params"]["redirect_to"],
            "https://campushub.example/auth/email/confirm/",
        )
        self.assertEqual(
            client.post.call_args.kwargs["json"]["data"]["campushub_signup"],
            True,
        )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
    )
    def test_email_signup_fails_closed_when_confirmation_is_disabled(self):
        request = RequestFactory().post("/register/")
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "user": {"id": "auth-user-id", "email_confirmed_at": None},
                "session": {"access_token": "unverified-session"},
            },
        )
        client = MagicMock()
        client.post.return_value = response

        with patch("portal.auth.httpx.Client") as client_factory:
            client_factory.return_value.__enter__.return_value = client
            with self.assertRaises(auth.SupabaseAuthError):
                auth.begin_email_signup(
                    request,
                    "student@example.edu",
                    "student-password",
                    {"campushub_signup": True},
                )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
    )
    def test_email_password_signin_rejects_unconfirmed_email(self):
        response = SimpleNamespace(
            status_code=400,
            json=lambda: {
                "code": "email_not_confirmed",
                "msg": "Email not confirmed",
            },
        )
        client = MagicMock()
        client.post.return_value = response

        with patch("portal.auth.httpx.Client") as client_factory:
            client_factory.return_value.__enter__.return_value = client
            with self.assertRaisesRegex(auth.SupabaseAuthError, "verify your email"):
                auth.sign_in_with_email_password(
                    "student@example.edu", "student-password"
                )
        client.get.assert_not_called()

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_ANON_KEY="public-anon-key",
    )
    def test_email_password_signin_checks_confirmed_identity(self):
        token_response = SimpleNamespace(
            status_code=200,
            json=lambda: {"access_token": "verified-access-token"},
        )
        identity_response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "email": "student@example.edu",
                "email_confirmed_at": "2026-10-14T00:00:00Z",
            },
        )
        client = MagicMock()
        client.post.return_value = token_response
        client.get.return_value = identity_response

        with patch("portal.auth.httpx.Client") as client_factory:
            client_factory.return_value.__enter__.return_value = client
            identity = auth.sign_in_with_email_password(
                "student@example.edu", "student-password"
            )

        self.assertEqual(identity["email"], "student@example.edu")
        self.assertEqual(
            client.get.call_args.args[0],
            "https://campus-project.supabase.co/auth/v1/user",
        )
        self.assertEqual(
            client.get.call_args.kwargs["headers"]["Authorization"],
            "Bearer verified-access-token",
        )


class FeaturePermissionTests(SimpleTestCase):
    def set_logged_in_session(self, role="student"):
        user_id = str(uuid.uuid4())
        session = self.client.session
        session["campushub_user"] = {
            "id": user_id,
            "name": "Test Student",
            "email": "student@example.invalid",
            "role": role,
            "branch_id": None,
            "semester": None,
        }
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return user_id

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_bookshare_and_skillswap_require_a_signed_in_user(self):
        self.assertRedirects(
            self.client.get("/bookshare/"),
            "/login/",
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            self.client.get("/skillswap/"),
            "/login/",
            fetch_redirect_response=False,
        )

    @override_settings(ALLOWED_HOSTS=["testserver"], SUPABASE_DATABASE_CONFIGURED=False)
    def test_login_required_notice_is_in_english(self):
        response = self.client.get("/skillswap/", follow=True)

        self.assertContains(
            response,
            "Please log in to your CampuZHub account first.",
            status_code=503,
        )

    def test_malformed_account_id_clears_the_signed_in_session(self):
        session = self.client.session
        session["campushub_user"] = {
            "id": "not-a-uuid",
            "name": "Test Student",
            "role": "student",
        }
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        response = self.client.get("/profile/")

        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        self.assertNotIn("campushub_user", self.client.session)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    @patch("portal.features.User.objects.filter")
    def test_forged_admin_role_in_cookie_does_not_grant_staff_access(self, user_query):
        user_id = self.set_logged_in_session(role="super_admin")
        user_query.return_value.first.return_value = SimpleNamespace(
            id=uuid.UUID(user_id),
            role="student",
        )

        response = self.client.get("/admin/")

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    @override_settings(SUPABASE_DATABASE_CONFIGURED=True, ALLOWED_HOSTS=["testserver"])
    @patch("portal.views.auth.begin_email_signup")
    @patch("portal.views.auth.find_user_by_email", return_value=None)
    @patch("portal.views.User.objects.create")
    def test_registration_sends_verification_without_creating_an_account(
        self, create_user, find_user, begin_email_signup
    ):
        request = RequestFactory().post(
            "/register/",
            {
                "name": "New Student",
                "email": "new@example.edu",
                "password": "valid-password",
                "branch": "",
                "semester": "",
            },
        )
        SessionMiddleware(lambda current_request: None).process_request(request)
        with patch("portal.views.render") as render, patch(
            "portal.views.logger.exception"
        ):
            from portal.views import register

            response = register(request)

        self.assertEqual(response, render.return_value)
        self.assertTrue(render.call_args.args[2]["confirmation_sent"])
        self.assertEqual(render.call_args.args[2]["confirmation_email"], "new@example.edu")
        begin_email_signup.assert_called_once()
        self.assertTrue(begin_email_signup.call_args.args[3]["campushub_signup"])
        create_user.assert_not_called()


class BookShareWorkflowTests(SimpleTestCase):
    def make_authenticated_post(self, path, user_id):
        request = RequestFactory().post(path)
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.session["campushub_user"] = {"id": str(user_id)}
        request._messages = FallbackStorage(request)
        return request

    def make_book(self, *, owner_id, action="borrow", available_until=None, status="available"):
        return SimpleNamespace(
            id=uuid.uuid4(),
            owner_id=owner_id,
            action=action,
            available_until=available_until,
            status=status,
            save=MagicMock(),
        )

    def test_book_listing_rejects_past_availability_dates(self):
        form = BookListingForm(
            {
                "title": "Calculus",
                "author": "",
                "subject": "Mathematics",
                "branch": "",
                "action": "borrow",
                "location": "",
                "available_until": (timezone.localdate() - timedelta(days=1)).isoformat(),
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Choose today or a future date.", form.errors["available_until"])
        self.assertEqual(
            form.fields["available_until"].widget.attrs["min"],
            timezone.localdate().isoformat(),
        )
        long_title_form = BookListingForm(
            {
                "title": "B" * 161,
                "author": "",
                "subject": "",
                "branch": "",
                "action": "borrow",
                "location": "",
                "available_until": "",
            }
        )
        self.assertFalse(long_title_form.is_valid())
        self.assertIn("title", long_title_form.errors)

    @patch("portal.features.transaction.atomic", return_value=nullcontext())
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.BookRequest.objects.select_for_update")
    @patch("portal.features.BookRequest.objects.create")
    def test_request_after_previous_decline_reopens_existing_unique_request(
        self,
        create_request,
        request_query,
        user_query,
        atomic,
    ):
        from portal.features import request_book

        requester = SimpleNamespace(id=uuid.uuid4())
        owner = uuid.uuid4()
        book = self.make_book(owner_id=owner)
        previous_request = SimpleNamespace(
            status="rejected",
            created_at=None,
            save=MagicMock(),
        )
        user_query.return_value.first.return_value = requester
        request_query.return_value.filter.return_value.first.return_value = previous_request
        request = self.make_authenticated_post("/bookshare/request/", requester.id)

        with patch("portal.features.get_object_or_404", return_value=book):
            response = request_book(request, book.id)

        self.assertEqual(response["Location"], "/bookshare/")
        self.assertEqual(previous_request.status, "pending")
        self.assertIsNotNone(previous_request.created_at)
        previous_request.save.assert_called_once_with(update_fields=["status", "created_at"])
        create_request.assert_not_called()
        self.assertEqual(book.status, "requested")
        book.save.assert_called_once_with(update_fields=["status"])

    @patch("portal.features.transaction.atomic", return_value=nullcontext())
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.BookRequest.objects.create")
    def test_expired_book_cannot_be_requested(
        self,
        create_request,
        user_query,
        atomic,
    ):
        from portal.features import request_book

        requester = SimpleNamespace(id=uuid.uuid4())
        book = self.make_book(
            owner_id=uuid.uuid4(),
            available_until=timezone.localdate() - timedelta(days=1),
        )
        user_query.return_value.first.return_value = requester
        request = self.make_authenticated_post("/bookshare/request/", requester.id)

        with patch("portal.features.get_object_or_404", return_value=book):
            request_book(request, book.id)

        create_request.assert_not_called()
        book.save.assert_not_called()

    @patch("portal.features.transaction.atomic", return_value=nullcontext())
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.BookRequest.objects.select_for_update")
    def test_completed_donation_closes_listing_instead_of_relisting_it(
        self,
        request_query,
        user_query,
        atomic,
    ):
        from portal.features import update_book_request

        owner = SimpleNamespace(id=uuid.uuid4())
        request_id = uuid.uuid4()
        book = self.make_book(owner_id=owner.id, action="donate", status="lent")
        book_request = SimpleNamespace(
            id=request_id,
            book_id=book.id,
            requester_id=uuid.uuid4(),
            status="accepted",
            save=MagicMock(),
        )
        user_query.return_value.first.return_value = owner
        request_query.return_value.get.return_value = book_request
        request = self.make_authenticated_post(
            f"/bookshare/requests/{request_id}/",
            owner.id,
        )
        request.POST = request.POST.copy()
        request.POST["action"] = "complete"

        with (
            patch(
                "portal.features.get_object_or_404",
                side_effect=[SimpleNamespace(book_id=book.id), book_request],
            ),
            patch("portal.features.Book") as book_model,
        ):
            book_model.objects.select_for_update.return_value.get.return_value = book
            response = update_book_request(request, request_id)

        self.assertEqual(response["Location"], "/bookshare/")
        self.assertEqual(book_request.status, "completed")
        self.assertEqual(book.status, "closed")
        book.save.assert_called_once_with(update_fields=["status"])

    @patch("portal.features.transaction.atomic", return_value=nullcontext())
    @patch("portal.features.User.objects.filter")
    @patch("portal.features.Book.objects.select_for_update")
    @patch("portal.features.BookRequest.objects.select_for_update")
    def test_completed_borrow_makes_book_available_again(
        self,
        request_query,
        book_query,
        user_query,
        atomic,
    ):
        from portal.features import update_book_request

        owner = SimpleNamespace(id=uuid.uuid4())
        request_id = uuid.uuid4()
        book = self.make_book(owner_id=owner.id, action="borrow", status="lent")
        book_request = SimpleNamespace(
            id=request_id,
            book_id=book.id,
            requester_id=uuid.uuid4(),
            status="accepted",
            save=MagicMock(),
        )
        user_query.return_value.first.return_value = owner
        request_query.return_value.get.return_value = book_request
        book_query.return_value.get.return_value = book
        request = self.make_authenticated_post(
            f"/bookshare/requests/{request_id}/",
            owner.id,
        )
        request.POST = request.POST.copy()
        request.POST["action"] = "complete"

        with patch(
            "portal.features.get_object_or_404",
            side_effect=[SimpleNamespace(book_id=book.id), book_request],
        ):
            response = update_book_request(request, request_id)

        self.assertEqual(response["Location"], "/bookshare/")
        self.assertEqual(book_request.status, "completed")
        self.assertEqual(book.status, "available")
        book.save.assert_called_once_with(update_fields=["status"])

    @patch("portal.features.BookRequest.objects.filter")
    @patch("portal.features.Branch.objects.all")
    @patch("portal.features.Book.objects.select_related")
    @patch("portal.features.User.objects.filter")
    def test_bookshare_directory_renders_searchable_listing_actions(
        self,
        user_query,
        book_query,
        branch_query,
        request_query,
    ):
        user = SimpleNamespace(
            id=uuid.uuid4(),
            role="student",
            name="Test Student",
            branch_id=None,
        )
        book = SimpleNamespace(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            owner=SimpleNamespace(id=uuid.uuid4(), name="Peer Student"),
            branch=None,
            title="Calculus, Volume I",
            author="A. Author",
            subject="Mathematics",
            action="borrow",
            get_action_display=lambda: "Borrow",
            location="Library",
            available_until=None,
            status="available",
        )
        listings = MagicMock()
        listings.exclude.return_value = listings
        listings.filter.return_value = listings
        listings.count.return_value = 1
        listings.__getitem__.return_value = [book]
        user_query.return_value.first.return_value = user
        book_query.return_value = listings
        branch_query.return_value = []
        request_query.return_value.select_related.return_value = []

        session = self.client.session
        session["campushub_user"] = {"id": str(user.id)}
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        branch_field = BookListingForm.base_fields["branch"]
        original_branch_queryset = branch_field.queryset
        branch_field.queryset = original_branch_queryset.none()
        try:
            response = self.client.get("/bookshare/?q=Calculus")
        finally:
            branch_field.queryset = original_branch_queryset

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good books find")
        self.assertContains(response, "Calculus, Volume I")
        self.assertContains(response, "Request to borrow")
        self.assertContains(response, 'id="book-query"')
        self.assertContains(response, "Requests for your books")


class StorageTests(SimpleTestCase):
    @override_settings(
        SUPABASE_URL="",
        SUPABASE_SERVICE_ROLE_KEY="",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_file_upload_fails_explicitly_without_storage_configuration(self):
        upload = SimpleUploadedFile(
            "lecture.pdf",
            b"%PDF-1.7 test",
            content_type="application/pdf",
        )

        with self.assertRaisesRegex(StorageUploadError, "uploads are not configured"):
            upload_note_file(upload)

    def test_file_upload_rejects_unsupported_mime_types(self):
        upload = SimpleUploadedFile(
            "malware.exe",
            b"not a document",
            content_type="application/octet-stream",
        )

        with self.assertRaisesRegex(StorageUploadError, "PDF, PNG, and JPG"):
            upload_note_file(upload)

    def test_file_upload_rejects_mime_and_extension_spoofing(self):
        upload = SimpleUploadedFile(
            "lecture.pdf",
            b"not actually a PDF",
            content_type="application/pdf",
        )

        with override_settings(
            SUPABASE_URL="https://campus-project.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="test-service-key",
            SUPABASE_STORAGE_BUCKET="campushub-files",
        ):
            with self.assertRaisesRegex(StorageUploadError, "actual format"):
                upload_note_file(upload)

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_valid_pdf_upload_uses_supabase_storage_post_api(self):
        upload = SimpleUploadedFile(
            "lecture.pdf",
            b"%PDF-1.7 test",
            content_type="application/pdf",
        )
        response = MagicMock()

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            url, filename = upload_note_file(upload)

        self.assertEqual(filename, "lecture.pdf")
        self.assertTrue(url.startswith("notes/"))
        client.post.assert_called_once()
        self.assertTrue(client.post.call_args.args[0].startswith(
            "https://campus-project.supabase.co/storage/v1/object/campushub-files/notes/"
        ))
        self.assertEqual(client.post.call_args.kwargs["content"], b"%PDF-1.7 test")
        self.assertEqual(client.post.call_args.kwargs["headers"]["x-upsert"], "false")
        response.raise_for_status.assert_called_once()

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_notice_attachment_upload_uses_announcements_storage_path(self):
        upload = SimpleUploadedFile(
            "campus-update.pdf",
            b"%PDF-1.7 notice",
            content_type="application/pdf",
        )
        response = MagicMock()

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            url, filename = upload_announcement_file(upload)

        self.assertEqual(filename, "campus-update.pdf")
        self.assertTrue(url.startswith("announcements/"))
        self.assertIn("/storage/v1/object/campushub-files/announcements/", client.post.call_args.args[0])

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_project_zip_upload_uses_project_storage_path(self):
        upload = SimpleUploadedFile(
            "campus-project.zip",
            b"PK\x03\x04project archive",
            content_type="application/zip",
        )
        response = MagicMock()

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            url, filename = upload_project_file(upload)

        self.assertEqual(filename, "campus-project.zip")
        self.assertTrue(url.startswith("projects/"))
        self.assertEqual(client.post.call_args.kwargs["content"], b"PK\x03\x04project archive")
        response.raise_for_status.assert_called_once()

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
        SUPABASE_UPLOAD_BUCKET="campushub-python-files",
    )
    def test_upload_uses_private_bucket_and_persists_bucket_qualified_reference(self):
        upload = SimpleUploadedFile(
            "lecture.pdf",
            b"%PDF-1.7 test",
            content_type="application/pdf",
        )
        response = MagicMock()

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            file_reference, _ = upload_note_file(upload)

        self.assertTrue(file_reference.startswith("storage://campushub-python-files/notes/"))
        self.assertIn(
            "/storage/v1/object/campushub-python-files/notes/",
            client.post.call_args.args[0],
        )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_private_storage_file_links_use_short_lived_signed_urls(self):
        response = MagicMock()
        response.json.return_value = {
            "signedURL": "/object/sign/campushub-files/notes/lecture.pdf?token=temporary"
        }

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            url = signed_storage_url("notes/lecture.pdf")

        self.assertEqual(
            url,
            "https://campus-project.supabase.co/storage/v1/object/sign/"
            "campushub-files/notes/lecture.pdf?token=temporary",
        )
        self.assertEqual(
            client.post.call_args.args[0],
            "https://campus-project.supabase.co/storage/v1/object/sign/"
            "campushub-files/notes/lecture.pdf",
        )
        self.assertEqual(
            client.post.call_args.kwargs["json"],
            {"expiresIn": 60 * 60},
        )
        response.raise_for_status.assert_called_once()

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co/",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
        SUPABASE_UPLOAD_BUCKET="campushub-python-files",
    )
    def test_bucket_qualified_private_reference_signs_from_its_bucket(self):
        response = MagicMock()
        response.json.return_value = {
            "signedURL": "/object/sign/campushub-python-files/notes/lecture.pdf?token=temporary"
        }

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            signed_storage_url("storage://campushub-python-files/notes/lecture.pdf")

        self.assertEqual(
            client.post.call_args.args[0],
            "https://campus-project.supabase.co/storage/v1/object/sign/"
            "campushub-python-files/notes/lecture.pdf",
        )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
        SUPABASE_UPLOAD_BUCKET="campushub-python-files",
    )
    def test_bucket_qualified_reference_rejects_unconfigured_bucket(self):
        with self.assertRaisesRegex(StorageUploadError, "configured storage bucket"):
            signed_storage_url("storage://other-bucket/notes/lecture.pdf")

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_private_storage_converts_legacy_public_url_to_object_path(self):
        response = MagicMock()
        response.json.return_value = {
            "signedURL": "/object/sign/campushub-files/notes/lecture.pdf?token=temporary"
        }

        with patch("portal.storage.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.post.return_value = response
            signed_storage_url(
                "https://campus-project.supabase.co/storage/v1/object/public/"
                "campushub-files/notes/lecture.pdf"
            )

        self.assertTrue(
            client.post.call_args.args[0].endswith("/notes/lecture.pdf")
        )

    @override_settings(
        SUPABASE_URL="https://campus-project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-key",
        SUPABASE_STORAGE_BUCKET="campushub-files",
    )
    def test_private_storage_rejects_file_references_from_other_hosts(self):
        with self.assertRaisesRegex(StorageUploadError, "does not belong"):
            signed_storage_url("https://other-project.supabase.co/notes/lecture.pdf")

    def test_project_upload_rejects_invalid_zip_signature(self):
        upload = SimpleUploadedFile(
            "campus-project.zip",
            b"not really a zip file",
            content_type="application/zip",
        )

        with self.assertRaisesRegex(StorageUploadError, "actual format"):
            upload_project_file(upload)

    def test_project_upload_field_accepts_zip_pdf_and_images(self):
        field = ProjectForm().fields["attachment"]

        self.assertFalse(field.required)
        self.assertEqual(
            field.widget.attrs["accept"],
            ".zip,.pdf,.png,.jpg,.jpeg,application/zip,application/pdf,image/png,image/jpeg",
        )
        self.assertIn("max 10 MB", field.help_text)

    @patch("portal.features.SkillFeedback.objects.filter")
    @patch("portal.features.SkillRequest.objects.filter")
    @patch("portal.features.Branch.objects.all")
    @patch("portal.features.Skill.objects.filter")
    @patch("portal.features.Skill.objects.select_related")
    @patch("portal.features.User.objects.filter")
    def test_skillswap_filters_directory_and_renders_exchange_actions(
        self,
        user_query,
        skill_select_related,
        skill_filter,
        branch_query,
        requests_query,
        feedback_query,
    ):
        user = SimpleNamespace(id=uuid.uuid4(), role="student", name="Test Student")
        user_query.return_value.first.return_value = user

        branch = SimpleNamespace(id=uuid.uuid4(), code="CSE", name="Computer Science")
        branch_query.return_value = [branch]

        listing = SimpleNamespace(
            id=uuid.uuid4(),
            type="teach",
            level="beginner",
            skill_name="Python",
            user=SimpleNamespace(name="Peer Student", branch=None),
            rating_count=2,
            average_rating=4.5,
        )
        listings = MagicMock()
        listings.annotate.return_value = listings
        listings.exclude.return_value = listings
        listings.filter.side_effect = lambda *args, **kwargs: listings
        listings.count.return_value = 1
        listings.__iter__.return_value = iter([listing])
        listings.__getitem__.side_effect = lambda key: [listing][key]
        skill_select_related.return_value = listings
        skill_filter.return_value = [SimpleNamespace(id=uuid.uuid4(), type="teach", skill_name="JavaScript", level="beginner")]

        requests_query.return_value.select_related.return_value = []

        feedback_filter = MagicMock()
        feedback_filter.select_related.return_value = []
        feedback_filter.values_list.return_value = []
        feedback_query.return_value = feedback_filter

        session = self.client.session
        session["campushub_user"] = {"id": str(user.id)}
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        response = self.client.get("/skillswap/?q=Python&type=teach&level=beginner&branch=" + str(branch.id))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teach what you know.")
        self.assertContains(response, "Find a match")
        self.assertContains(response, "Send learning request")
        self.assertContains(response, "4.5 / 5")
        self.assertContains(response, "2 ratings")
        self.assertNotContains(response, "★")
        self.assertContains(response, 'id="skill-branch"')
        self.assertContains(response, "Your next connection starts with one request.")


class CampusToolTests(SimpleTestCase):
    def test_every_registered_tool_page_renders(self):
        slugs = (
            "percentage", "cgpa", "units", "python", "sql", "linux", "subnet",
            "ohms-law", "power", "logic-gates", "mechanical-units", "area-volume",
            "mlt-dilution",
        )

        for slug in slugs:
            with self.subTest(slug=slug):
                response = self.client.get(f"/tools/{slug}/")
                self.assertEqual(response.status_code, 200)

    def test_python_practice_is_available_without_executing_user_code(self):
        response = self.client.get("/tools/python/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not execute arbitrary code")
        self.assertContains(response, "x = 3")

    def test_python_practice_checks_answers_without_running_code(self):
        response = self.client.post(
            "/tools/python/",
            {"exercise": "1", "answer": "0, 1, 2"},
        )

        self.assertContains(response, "range(3)")
        self.assertContains(response, "Correct.")

    def test_percentage_and_subnet_tools_calculate_valid_results(self):
        percentage = self.client.post("/tools/percentage/", {"a": "25", "b": "100"})
        subnet = self.client.post(
            "/tools/subnet/",
            {"address": "192.168.1.10", "prefix": "24"},
        )

        self.assertContains(percentage, "25%")
        self.assertContains(subnet, "192.168.1.0")
        self.assertContains(subnet, "192.168.1.255")
        self.assertContains(subnet, "254 usable / 256 total")

    def test_remaining_calculators_return_expected_results(self):
        cases = (
            ("/tools/cgpa/", {"grades": "8,9"}, "8.5"),
            (
                "/tools/units/",
                {
                    "category": "length",
                    "value": "1",
                    "from_unit": "Metres (m)",
                    "to_unit": "Kilometres (km)",
                },
                "0.001 Kilometres (km)",
            ),
            ("/tools/ohms-law/", {"voltage": "12", "current": "2"}, "R = 6 Ω · P = 24 W"),
            ("/tools/power/", {"first": "12", "second": "2"}, "24 W"),
            ("/tools/logic-gates/", {"a": "on", "b": "on"}, "AND"),
            ("/tools/area-volume/", {"shape": "circle", "first": "1"}, "3.142 square units"),
            (
                "/tools/mechanical-units/",
                {
                    "category": "pressure",
                    "value": "1",
                    "from_unit": "Megapascal (MPa)",
                    "to_unit": "Pascal (Pa)",
                },
                "1000000 Pascal (Pa)",
            ),
            (
                "/tools/mlt-dilution/",
                {"c1": "10", "v1": "2", "c2": "5", "v2": ""},
                "Final volume: 4",
            ),
        )
        for url, data, expected in cases:
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected)

    def test_tool_validation_rejects_zero_denominators_and_unphysical_temperature(self):
        percentage = self.client.post("/tools/percentage/", {"a": "25", "b": "0"})
        temperature = self.client.post(
            "/tools/units/",
            {
                "category": "temperature",
                "value": "-300",
                "from_unit": "Celsius (°C)",
                "to_unit": "Kelvin (K)",
            },
        )

        self.assertContains(percentage, "B cannot be zero.")
        self.assertContains(temperature, "absolute zero")
        self.assertNotContains(temperature, "-26.85 K")

    def test_unknown_tool_slugs_return_not_found(self):
        response = self.client.get("/tools/not-a-real-tool/")

        self.assertEqual(response.status_code, 404)

    def test_each_branch_tool_route_renders(self):
        for slug in sorted(BRANCH_TOOL_SLUGS):
            with self.subTest(slug=slug):
                response = self.client.get(f"/branch-tools/{slug}/")
                self.assertEqual(response.status_code, 200)

    def test_engineering_and_civil_calculators_return_expected_results(self):
        cases = (
            (
                "stress-strain",
                {"force": "100", "area": "10", "length": "100", "extension": "0.1"},
                "Young&#x27;s modulus: 10.0000 GPa",
            ),
            (
                "gear-ratio",
                {"driver_teeth": "20", "driven_teeth": "40", "input_speed": "1200"},
                "Ideal output speed: 600.00 rpm",
            ),
            (
                "heat-transfer",
                {"mass": "2", "specific_heat": "4", "temperature_change": "-5"},
                "Sensible heat transfer: -40.0000 kJ",
            ),
            (
                "concrete-volume",
                {"length": "2", "width": "3", "depth": "0.2", "allowance": "5"},
                "With allowance: 1.2600 m³",
            ),
            (
                "survey-level",
                {"benchmark_rl": "100", "backsight": "1.5", "staff_reading": "2"},
                "Reduced level: 99.5000 m",
            ),
            ("quantity-estimator", {"quantity": "5", "unit_rate": "120"}, "₹600.00"),
            ("slope-grade", {"rise": "3", "run": "4"}, "Grade: 75.0000%"),
        )
        for slug, data, expected in cases:
            with self.subTest(slug=slug):
                response = self.client.post(f"/branch-tools/{slug}/", data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected)

    def test_electrical_and_electronics_calculators_return_expected_results(self):
        cases = (
            (
                "resistor-network",
                {"values": "100, 200", "voltage": "12"},
                "Series: Req 300.0000 Ω",
            ),
            (
                "ac-power",
                {"voltage": "230", "current": "2", "power_factor": "0.8"},
                "Real power: 368.0000 W",
            ),
            (
                "transformer-ratio",
                {"primary_voltage": "230", "primary_turns": "100", "secondary_turns": "50"},
                "Ideal secondary voltage: 115.0000 V",
            ),
            (
                "resistor-colour-code",
                {"band1": "red", "band2": "violet", "multiplier": "orange", "tolerance": "gold"},
                "Nominal resistance: 27,000 Ω",
            ),
            (
                "led-resistor",
                {"supply_voltage": "5", "forward_voltage": "2", "current_ma": "20"},
                "Calculated resistance: 150.00 Ω",
            ),
            (
                "rc-time-constant",
                {"resistance": "10000", "capacitance_uf": "10"},
                "Time constant τ: 100.0000 ms",
            ),
            ("number-base", {"value": "255"}, "Hexadecimal: FF"),
        )
        for slug, data, expected in cases:
            with self.subTest(slug=slug):
                response = self.client.post(f"/branch-tools/{slug}/", data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected)

    def test_branch_practice_tools_explain_answers_and_advance(self):
        response = self.client.post(
            "/branch-tools/dsa-practice/",
            {"question": "0", "answer": "1"},
        )

        self.assertContains(response, "Correct.")
        self.assertContains(response, "What is the average lookup complexity")

    def test_branch_practice_handles_malformed_question_indices(self):
        for question_index in ("invalid", "99"):
            with self.subTest(question_index=question_index):
                response = self.client.post(
                    "/branch-tools/dsa-practice/",
                    {"question": question_index, "answer": "1"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Which structure follows FIFO order?")

    def test_git_helper_only_displays_commands_and_web_playground_is_sandboxed(self):
        helper = self.client.post("/branch-tools/git-helper/", {"task": "inspect"})
        playground = self.client.get("/branch-tools/web-playground/")

        self.assertContains(helper, "git status")
        self.assertContains(helper, "Commands are shown for learning only")
        self.assertContains(playground, 'sandbox="allow-scripts"')
        self.assertContains(playground, "Content Security Policy")
        self.assertContains(playground, "/static/python/branch-web-playground.js?v=1")

    def test_calculator_validation_rejects_invalid_inputs(self):
        ac_power = self.client.post(
            "/branch-tools/ac-power/",
            {"voltage": "230", "current": "2", "power_factor": "1.2"},
        )
        circuit = self.client.post(
            "/branch-tools/resistor-network/",
            {"values": "100,0", "voltage": "12"},
        )
        extreme_circuit = self.client.post(
            "/branch-tools/resistor-network/",
            {"values": "1e99999999", "voltage": "12"},
        )
        concrete = self.client.post(
            "/branch-tools/concrete-volume/",
            {"length": "2", "width": "3", "depth": "0.2", "allowance": "101"},
        )

        self.assertContains(ac_power, "Ensure this value is less than or equal to 1.")
        self.assertContains(circuit, "Enter 1–12 resistor values")
        self.assertContains(extreme_circuit, "Enter 1–12 resistor values")
        self.assertContains(concrete, "Ensure this value is less than or equal to 100.")


class CompilerTests(SimpleTestCase):
    def test_compiler_page_restores_the_editor_without_changing_its_shell(self):
        response = self.client.get("/compiler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<body class="code-lab-page">')
        self.assertContains(response, '<img class="brand-wordmark" src="/static/python/campuzhub-wordmark.png" alt="CampuZHub">')
        self.assertContains(response, "Run Python interactively in your browser")
        self.assertContains(response, "Run code")
        self.assertContains(response, "compiler.js")

    def test_execute_api_rejects_invalid_language_and_oversized_code(self):
        unsupported = self.client.post(
            "/compiler/execute/",
            data='{"language":"python","code":"print(1)","stdin":""}',
            content_type="application/json",
        )
        oversized = self.client.post(
            "/compiler/execute/",
            data=json.dumps(
                {"language": "c", "code": "x" * 50_001, "stdin": ""}
            ),
            content_type="application/json",
        )

        self.assertEqual(unsupported.status_code, 400)
        self.assertIn("supported programming language", unsupported.json()["message"])
        self.assertEqual(oversized.status_code, 413)

    def test_execute_api_sends_only_supported_cloud_language_to_onecompiler(self):
        response_context = MagicMock()
        response = response_context.__enter__.return_value
        response.iter_bytes.return_value = [
            b'{"stdout":"Hello, CampuZHub!\\\\n","stderr":"","exception":null,"executionTime":1.25}'
        ]
        response.status_code = 200

        with patch("portal.compiler_views.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.stream.return_value = response_context
            result = self.client.post(
                "/compiler/execute/",
                data=json.dumps(
                    {"language": "c", "code": "int main(void) { return 0; }", "stdin": "CampuZHub"}
                ),
                content_type="application/json",
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["stdout"], "Hello, CampuZHub!\\n")
        upstream_payload = client.stream.call_args.kwargs["json"]
        self.assertEqual(upstream_payload["mode"], "c_cpp")
        self.assertEqual(upstream_payload["properties"]["stdin"], "CampuZHub")
        self.assertEqual(
            upstream_payload["properties"]["files"][0]["name"],
            "Main.c",
        )

    @patch(
        "portal.compiler_views.httpx.Client",
        side_effect=httpx.TimeoutException("timeout"),
    )
    def test_execute_api_reports_compiler_timeout(self, client_factory):
        response = self.client.post(
            "/compiler/execute/",
            data=json.dumps({"language": "c", "code": "int main(){return 0;}", "stdin": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 504)
        self.assertIn("too long", response.json()["message"])
