
# your_project/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', "health_care_backend.settings")

app = Celery('health_care_backend',broker=settings.CELERY_BROKER_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True

# Autodiscover tasks
app.autodiscover_tasks()

# Celery Debugging
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
