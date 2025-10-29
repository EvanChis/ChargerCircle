# config/wsgi.py

# Import os because it's needed to set the 'DJANGO_SETTINGS_MODULE' environment variable.
import os
# Import get_wsgi_application from django.core.wsgi because 'application' needs it.
from django.core.wsgi import get_wsgi_application

"""
Author:
This file is the entry-point for the web server when it's running
in WSGI mode (the standard way Django handles normal, non-real-time
web requests). It tells the server where to find the main
application settings and how to run the Django app.
"""
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
