import sys
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def run_seed_callback(sender, **kwargs):
    try:
        from core.services.db_service import seed_database_safely
        seed_database_safely()
    except Exception:
        pass

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        post_migrate.connect(run_seed_callback, sender=self)
