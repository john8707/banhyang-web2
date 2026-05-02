import os
from celery import Celery

# Django의 settings 모듈을 Celery의 기본 설정으로 지정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banhyang.config.settings')

# 'banhyang'이라는 이름으로 Celery 애플리케이션을 생성합니다.
app = Celery('banhyang')

# Django settings.py에서 'CELERY_'로 시작하는 설정을 가져옵니다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 설치된 모든 Django 앱에서 tasks.py를 자동으로 찾습니다.
app.autodiscover_tasks()