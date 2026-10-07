from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("branches/", views.branch_list, name="branches"),
    path("branchhub/", views.feature_status, {"feature": "BranchHub"}, name="branchhub"),
    path("bookshare/", views.feature_status, {"feature": "BookShare"}, name="bookshare"),
    path("skillswap/", views.feature_status, {"feature": "SkillSwap"}, name="skillswap"),
    path("compiler/", views.feature_status, {"feature": "Code Lab"}, name="compiler"),
    path("project-ideas/", views.feature_status, {"feature": "Project ideas"}, name="project_ideas"),
]
