import os
import django 
from celery import Celery

# Set default settings for Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_care_backend.settings")

# Ensure Django is fully loaded
django.setup()

# Initialize Celery
app = Celery("health_care_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True

# Autodiscover tasks
app.autodiscover_tasks()

# Celery Debugging
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
