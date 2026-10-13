from types import SimpleNamespace

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .tool_views import TOOL_TITLES

CANONICAL_DOMAIN = "campushub-python.vercel.app"


class PublicSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return [
            "home",
            "branches",
            "compiler",
            "project_ideas",
            *[("tool_detail", slug) for slug in TOOL_TITLES],
        ]

    def location(self, item):
        if isinstance(item, tuple):
            return reverse(item[0], kwargs={"slug": item[1]})
        return reverse(item)

    def get_urls(self, page=1, site=None, protocol=None):
        return super().get_urls(
            page=page,
            site=SimpleNamespace(domain=CANONICAL_DOMAIN),
            protocol="https",
        )
