"""
WSGI config for banhyang project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banhyang.config.settings')

application = get_wsgi_application()
from django.core.management import call_command
call_command('migrate')


if os.getenv("MIGRATE", False) is True:
    call_command('dumpdata', 'practice','--exclude', 'contenttypes','--natural-foreign', '-o', 'db.json')
    call_command('loaddata', 'db.json', '--database=migrate')

from django.contrib.auth import get_user_model
User = get_user_model()  # get the currently active user model,
if os.getenv("DJANGO_SUPERUSER_USERNAME", None) and os.getenv("DJANGO_SUPERUSER_PASSWORD", None):
    User.objects.filter(username= os.getenv("DJANGO_SUPERUSER_USERNAME")).exists() or \
        call_command('createsuperuser', interactive=False)
