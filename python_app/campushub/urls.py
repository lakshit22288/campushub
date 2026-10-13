from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from portal.sitemaps import PublicSitemap

sitemaps = {"public": PublicSitemap()}
ROBOTS_TXT = """\
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /auth/
Disallow: /bookshare/
Disallow: /help/
Disallow: /login/
Disallow: /logout/
Disallow: /profile/
Disallow: /register/
Disallow: /search/
Disallow: /skillswap/
Disallow: /health/
Disallow: /compiler/execute/
Sitemap: https://campushub-python.vercel.app/sitemap.xml
"""


def robots_txt(request):
    return HttpResponse(ROBOTS_TXT, content_type="text/plain")

urlpatterns = [
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django_sitemap"),
    path("", include("portal.urls")),
]
