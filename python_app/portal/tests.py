import base64
import hashlib
import json
import time
import uuid
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

import bcrypt
import httpx
from django import forms
from django.db import IntegrityError, OperationalError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from portal import auth
from portal.forms import AnnouncementForm, BookListingForm, NoteForm, ProjectForm
from portal.idea_catalog import IDEAS
from portal.storage import (
    StorageUploadError,
    upload_announcement_file,
    upload_note_file,
    upload_project_file,
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
        self.assertContains(response, "CampusHub")
        self.assertContains(response, "YOUR CAMPUS, IN MOTION")
        self.assertContains(response, "Learn something.")
        self.assertContains(response, "QUICK START / PYTHON")
        self.assertContains(response, "Computer Science / IT")
        self.assertContains(response, "/static/styles/global.css")
        self.assertContains(response, "/static/python/python.css?v=29")

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
        self.assertContains(response, '<span class="brand-mark">CH</span>')
        self.assertContains(response, "CampusHub • Open-source student ecosystem • Built for campus use")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_home_explains_database_is_not_configured(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect to CampusHub to see your branch communities.")

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
    def test_branchhub_ignores_another_branch_filter_for_students(
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
            ["Algorithms"],
        )
        self.assertEqual(response.context["branch_filter"], str(own_branch_id))

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
    def test_subject_detail_denies_students_from_other_branches(
        self, user_query, get_subject, notes_filter
    ):
        user = SimpleNamespace(
            id=uuid.uuid4(),
            role="student",
            branch_id=uuid.uuid4(),
        )
        subject = SimpleNamespace(
            id=uuid.uuid4(),
            branch_id=uuid.uuid4(),
        )
        self.set_logged_in_user(user.id)
        user_query.return_value.first.return_value = user
        get_subject.return_value = subject

        response = self.client.get(f"/branchhub/subjects/{subject.id}/")

        self.assertRedirects(response, "/branchhub/", fetch_redirect_response=False)
        notes_filter.assert_not_called()

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
    def test_password_hash_is_compatible_with_bcrypt_storage(self):
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

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/branchhub/")


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
            "Please log in to your CampusHub account first.",
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
    @patch("portal.views.transaction.atomic", return_value=nullcontext())
    @patch("portal.views.User.objects.create")
    @patch("portal.views.auth.find_user_by_email", return_value=None)
    def test_public_registration_always_creates_student_role(
        self, find_user, create_user, atomic
    ):
        user = SimpleNamespace(
            id=uuid.uuid4(),
            name="New Student",
            email="new@example.edu",
            role="student",
            branch_id=None,
            semester=None,
        )
        create_user.return_value = user

        response = self.client.post(
            "/register/",
            {
                "name": "New Student",
                "email": "new@example.edu",
                "password": "valid-password",
                "role": "super_admin",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/branchhub/")
        self.assertEqual(create_user.call_args.kwargs["role"], "student")
        self.assertIsNotNone(create_user.call_args.kwargs["created_at"])

    @override_settings(SUPABASE_DATABASE_CONFIGURED=True, ALLOWED_HOSTS=["testserver"])
    @patch("portal.views.auth.find_user_by_email", return_value=None)
    @patch("portal.views.User.objects.create", side_effect=IntegrityError("required column failed"))
    @patch("portal.views.transaction.atomic", return_value=nullcontext())
    def test_registration_does_not_report_unrelated_database_error_as_duplicate(
        self, atomic, create_user, find_user
    ):
        request = RequestFactory().post(
            "/register/",
            {
                "name": "New Student",
                "email": "new@example.edu",
                "password": "valid-password",
            },
        )
        SessionMiddleware(lambda current_request: None).process_request(request)
        with patch("portal.views.render") as render, patch(
            "portal.views.logger.exception"
        ):
            from portal.views import register

            register(request)

        form = render.call_args.args[2]["form"]
        self.assertTrue(
            any("We could not create your account." in error for error in form.non_field_errors())
        )
        self.assertNotIn(
            "An account with this email address already exists.",
            form.errors.get("email", []),
        )


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
        self.assertIn("/storage/v1/object/public/campushub-files/notes/", url)
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
        self.assertIn("/storage/v1/object/public/campushub-files/announcements/", url)
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
        self.assertIn("/storage/v1/object/public/campushub-files/projects/", url)
        self.assertEqual(client.post.call_args.kwargs["content"], b"PK\x03\x04project archive")
        response.raise_for_status.assert_called_once()

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


class CompilerTests(SimpleTestCase):
    def test_compiler_page_restores_the_editor_without_changing_its_shell(self):
        response = self.client.get("/compiler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<body class="code-lab-page">')
        self.assertContains(response, '<span class="brand-mark">CH</span>')
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
            b'{"stdout":"Hello, CampusHub!\\\\n","stderr":"","exception":null,"executionTime":1.25}'
        ]
        response.status_code = 200

        with patch("portal.compiler_views.httpx.Client") as client_factory:
            client = client_factory.return_value.__enter__.return_value
            client.stream.return_value = response_context
            result = self.client.post(
                "/compiler/execute/",
                data=json.dumps(
                    {"language": "c", "code": "int main(void) { return 0; }", "stdin": "CampusHub"}
                ),
                content_type="application/json",
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["stdout"], "Hello, CampusHub!\\n")
        upstream_payload = client.stream.call_args.kwargs["json"]
        self.assertEqual(upstream_payload["mode"], "c_cpp")
        self.assertEqual(upstream_payload["properties"]["stdin"], "CampusHub")
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
