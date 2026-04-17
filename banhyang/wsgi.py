"""
WSGI config for banhyang project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.contrib.auth import get_user_model
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banhyang.config.settings')

application = get_wsgi_application()
call_command('migrate')

MIGRATE = os.getenv('MIGRATE', False)
if MIGRATE is True:
    call_command('migrate', '--database=migrate')
    call_command('dumpdata', 'practice','--exclude', 'practice.User', '--exclude', 'contenttypes', '--natural-foreign', '-o', 'db.json')
    call_command('loaddata', 'db.json', '--database=migrate')


User = get_user_model()  # get the currently active user model,
if os.getenv("DJANGO_SUPERUSER_USERNAME", None) and os.getenv("DJANGO_SUPERUSER_PASSWORD", None):
    DJANGO_SUPERUSER_NAME = os.getenv("DJANGO_SUPERUSER_NAME", 'admin')
    DJANGO_SUPERUSER_STUDENT_ID = os.getenv("DJANGO_SUPERUSER_STUDENT_ID", '0')
    DJANGO_SUPERUSER_PHONE_NUMBER = os.getenv("DJANGO_SUPERUSER_PHONE_NUMBER", '0')
    User.objects.filter(username=os.getenv("DJANGO_SUPERUSER_USERNAME")).exists() or \
        call_command('createsuperuser',
                     '--name', DJANGO_SUPERUSER_NAME,
                     '--student_id', DJANGO_SUPERUSER_STUDENT_ID,
                     '--phone_number', DJANGO_SUPERUSER_PHONE_NUMBER,
                     '--is_confirmed', True, interactive=False)


from banhyang.practice.views import sched
sched.start()
