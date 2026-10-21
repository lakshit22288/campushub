from django.urls import path

from . import admin_views
from . import branch_tool_views
from . import compiler_views
from . import features
from . import planner_views
from . import tool_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("branches/", views.branch_list, name="branches"),
    path("search/", features.global_search, name="search"),
    path("tools/<slug:slug>/", tool_views.tool_detail, name="tool_detail"),
    path("branch-tools/<slug:slug>/", branch_tool_views.branch_tool_detail, name="branch_tool_detail"),
    path("login/", views.login, name="login"),
    path("password/reset/", views.password_reset_request, name="password_reset_request"),
    path("register/", views.register, name="register"),
    path("auth/google/", views.google_sign_in, name="google_sign_in"),
    path("auth/email/confirm/", views.email_confirmation, name="email_confirmation"),
    path("auth/email/complete/", views.complete_email_confirmation, name="email_confirmation_complete"),
    path("auth/password/reset/", views.password_reset_confirm, name="password_reset_confirm"),
    path("auth/callback", views.google_callback, name="google_callback"),
    path("auth/profile/", views.google_profile, name="google_profile"),
    path("logout/", views.logout, name="logout"),
    path("branchhub/", features.branchhub, name="branchhub"),
    path("branchhub/subjects/<uuid:subject_id>/", features.subject_detail, name="subject_detail"),
    path("bookshare/", features.bookshare, name="bookshare"),
    path("bookshare/<uuid:book_id>/request/", features.request_book, name="request_book"),
    path("bookshare/requests/<uuid:request_id>/", features.update_book_request, name="update_book_request"),
    path("skillswap/", features.skillswap, name="skillswap"),
    path("skillswap/<uuid:skill_id>/request/", features.request_skill, name="request_skill"),
    path("skillswap/requests/<uuid:request_id>/", features.update_skill_request, name="update_skill_request"),
    path("skillswap/requests/<uuid:request_id>/feedback/", features.submit_skill_feedback, name="submit_skill_feedback"),
    path("help/", features.help_requests, name="help_requests"),
    path("campus/", planner_views.campus_board, name="campus_board"),
    path("planner/", planner_views.planner, name="planner"),
    path("help/<uuid:request_id>/resolve/", features.close_help_request, name="close_help_request"),
    path("profile/", features.profile, name="profile"),
    path("compiler/", compiler_views.compiler_page, name="compiler"),
    path("compiler/execute/", compiler_views.execute_code, name="compiler_execute"),
    path("project-ideas/", features.project_ideas, name="project_ideas"),
    path("admin/", admin_views.admin_dashboard, name="admin"),
]
