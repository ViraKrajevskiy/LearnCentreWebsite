from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = 'WebSite'

    def ready(self):
        import WebSite.signals  # noqa: F401