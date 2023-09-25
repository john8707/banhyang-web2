release: python manage.py migrate
web: gunicorn --bind 0:8000 banhyang.wsgi:application --log-file -