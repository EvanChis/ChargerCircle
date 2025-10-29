# config/settings.py

# Import os because it's needed to read environment variables (like 'SECRET_KEY', 'DEBUG').
import os
# Import Path from pathlib because it helps the project find its own location ('BASE_DIR').
from pathlib import Path
# Import dj_database_url from dj_database_url because it reads the database connection info.
import dj_database_url
# Import load_dotenv from dotenv because it loads the secret keys from the .env file.
from dotenv import load_dotenv

"""
Author:
This is the main configuration file for the entire Django project.
It's like the central control panel that tells the application
what features to turn on, what apps to use, how to connect to
the database, and where to find files.
RT: This file is critical for real-time features, as it defines
the 'ASGI_APPLICATION' and 'CHANNEL_LAYERS' settings which
enable WebSockets.
"""

# Builds paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Loads environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - not for production
SECRET_KEY = os.getenv('SECRET_KEY', 'a-default-secret-key-for-development')
DEBUG = os.getenv('DEBUG', '1') == '1'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

"""
Author:
This list tells Django which "apps" or "features" are
turned on for this project. This includes Django's built-in
apps (like 'admin', 'auth'), third-party apps we added
('daphne', 'storages'), and our own custom apps ('accounts',
'rooms', 'messaging').
RT: The 'daphne' app is listed here, which is the server
that handles real-time WebSocket connections.
"""
# Application definition
INSTALLED_APPS = [
    'daphne', # RT: The real-time server
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'storages',
    # Local apps
    'accounts',
    'rooms',
    'messaging',
    'core',
]

"""
Author:
Middleware are layers of security and functionality that
process every request and response. This list includes
things for security (like 'CsrfViewMiddleware') and for
handling user sessions and authentication ('SessionMiddleware',
'AuthenticationMiddleware').
"""
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

"""
Author:
This setting tells Django where to find the HTML template
files that create the web pages. It also lists "context
processors," which are helpers that make certain data
(like the logged-in user or the notification count)
available to all templates.
RT: The 'pending_invites_count' processor provides real-time
notification data to the header.
"""
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'messaging.context_processors.pending_invites_count', # RT: For live notification badge
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

"""
Author:
This setting tells Django to use the 'asgi.py' file as the
main entry point, which allows the server to handle both
regular HTTP requests and real-time WebSocket traffic.
RT: This is the primary setting that enables all real-time
functionality.
"""
ASGI_APPLICATION = 'config.asgi.application'


"""
Author:
This setting tells the application how to connect to the
database. It's set up to read a 'DATABASE_URL' from the
.env file, which makes it easy to switch between a local
test database (SQLite) and the production database (PostgreSQL).
"""
# Database
DATABASES = {
    'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

"""
Author:
This setting configures the "live-messaging" system
(Channels) that allows the application to send real-time
notifications and chat messages between different users.
It uses Redis (via the 'REDIS_URL') as the "message broker"
to pass these messages.
RT: This is the complete configuration for the real-time
messaging backend.
"""
# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')],
        },
    },
}

"""
Author:
This setting tells Django to use our custom 'User' model
(defined in 'accounts/models.py') for handling all user
accounts, instead of Django's default built-in one. This
is what allows us to use email as the login.
"""
# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

"""
Author:
These settings tell Django where to find, collect, and
serve the "static" files. These are files like CSS,
JavaScript, and basic images that don't change.
'whitenoise' is used to serve these files efficiently.
"""
# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

"""
Author: Evan
These settings define where to store "media" files, which
are files uploaded by users (like their profile pictures).
The 'if' statement checks if we are in production
(using 'AWS_STORAGE_BUCKET_NAME') and tells the app to
save files to an S3 bucket instead of the local server.
"""
# Media files (User Uploads)
if 'AWS_STORAGE_BUCKET_NAME' in os.environ:
    # Production Media Storage (S3)
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3StaticStorage"},
    }
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Local Development Media Storage
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings for production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

