from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase, override_settings

from campushub.settings import postgres_settings


class PortalPageTests(SimpleTestCase):
    @patch("portal.views.Announcement.objects.select_related")
    @patch("portal.views.Branch.objects.all")
    @override_settings(SUPABASE_DATABASE_CONFIGURED=True)
    def test_home_renders_existing_design_and_branch_data(self, branches_query, announcements_query):
        branches_query.return_value = [
            type("BranchRow", (), {"id": "branch-1", "name": "Computer Science / IT", "code": "CSE", "icon": ""})()
        ]
        announcements_query.return_value.all.return_value = []

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CampusHub")
        self.assertContains(response, "Computer Science / IT")
        self.assertContains(response, "/static/styles/global.css")

    @override_settings(SUPABASE_DATABASE_CONFIGURED=False)
    def test_home_explains_database_is_not_configured(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Branches will appear here once the existing Supabase database is connected.")

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
