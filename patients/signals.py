from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

@receiver(post_migrate)
def create_periodic_task(sender, **kwargs):
    if sender.name == "patients":
        if not PeriodicTask.objects.filter(name="Send appointment reminders").exists():
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=1, period=IntervalSchedule.DAYS
            )
            PeriodicTask.objects.create(
                interval=schedule,
                name="Send appointment reminders",
                task="patients.tasks.send_scheduled_reminders",
                args=json.dumps([]),
            )
