import subprocess

# Start Celery worker
worker = subprocess.Popen(['celery', '-A', 'health_care_backend', 'worker', '-l', 'info', '--pool=solo'])

# Start Celery beat
beat = subprocess.Popen(['celery', '-A', 'health_care_backend', 'beat', '-l', 'info', '--scheduler', 'django_celery_beat.schedulers:DatabaseScheduler'])

# Wait for both to finish (this will keep the script running)
worker.wait()
beat.wait()
