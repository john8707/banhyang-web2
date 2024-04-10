"""
Django settings for banhyang project.

Generated by 'django-admin startproject' using Django 3.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
    
from django.core.management.utils import get_random_secret_key

SECRET_KEY = SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', get_random_secret_key())
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.ngrok-free.app").split(",")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'banhyang.core',
    'django.contrib.humanize',
    'banhyang.practice'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'banhyang.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'config/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'banhyang.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases


"""
if get_secret("DATABASE") == "sqlite3":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
            'default': {
                        'ENGINE': 'django.db.backends.postgresql',
                        'HOST': 'banhyang-db.cqhloq4etla7.ap-northeast-2.rds.amazonaws.com',
                        'PORT': '5432',
                        'NAME': 'deploy',
                        'USER': 'banhyang34',
                        'PASSWORD': get_secret("DATABASE"),
                    }
            }
"""

import sys
import oracledb
oracledb.version = "2.1.1"
sys.modules["cx_Oracle"] = oracledb

USE_TEST_DB = os.getenv("USE_TEST_DB", False)
if USE_TEST_DB is True:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:

    DATABASES = {
        'default' :{
            'ENGINE' : 'django.db.backends.oracle',
            'NAME' : os.getenv("ORACLE_DNS", None),
            'USER' : 'ADMIN',
            'PASSWORD' : os.getenv("ORACLE_PW", None),
        }
    }

"""
For planetscale
DB_PARAMS = dj_database_url.parse(os.environ.get("DJANGO_DATABASE_URL").replace('\'', ''))
DATABASES['migrate'] = DB_PARAMS
DB_PARAMS["ENGINE"] = "banhyang.custom_db_backends.vitess"

For koyeb database server
'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'banhyang-web',
    'USER': 'koyeb-adm',
    'PASSWORD': os.getenv("POSTGRESQL_PW", None),
    'HOST': 'ep-plain-field-a1abb1n0.ap-southeast-1.pg.koyeb.app',
    'OPTIONS': {'sslmode': 'require'},
},
"""


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    'banhyang/core/static',
    'banhyang/practice/static'
    
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(ROOT_DIR, '.static_root')
