import sys

from django.apps import AppConfig

from backend import settings


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        if 'runserver' not in sys.argv:
            return
        if settings.SCHEDULER_AUTOSTART:
            from . import scheduler
            scheduler.start()
