# A very basic settings file that allows Sphinx to build
# the docs (this is becuase autodoc is used).
import os
import sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))

SITE_ID = 303
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {"default": {
    "NAME": ":memory:",
    "ENGINE": "django.db.backends.sqlite3",
    "USER": '',
    "PASSWORD": '',
    "PORT": '',
}}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'scaffold',
)

SECRET_KEY = "NULL"

SCAFFOLD_EXTENDING_APP_NAME = "scaffold"
SCAFFOLD_EXTENDING_MODEL_PATH = "scaffold.models.BaseSection"
