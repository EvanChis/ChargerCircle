# Python 3
# Scripts enabled in Windows

# To git Started:
# Clone from GitHub

# Windows:
# Open repo in VS Code
# Start the Terminal

# In the terminal, type the following command and press Enter:
.\bootstrap.bat
# If you see: "We noticed... Do you...?"
# CLICK YES

# Always be sure terminal is:
# (.venv) <Path> not just <Path>
# If it's not do:
.\.venv\Scripts\activate

# Create your admin user for django admin priveleges:
python manage.py createsuperuser

# Now you're all set up!

# In dev, mostly need:
# Runs the server
python manage.py runserver
# Stops the server
ctrl + c

# If changes are made to database models (`models.py`), create and apply migrations:
# Creates migration files
python manage.py makemigrations
# Applies migrations to database
python manage.py migrate

# Git Started:
# Get Upstash URL and Neon URL from Discord
# Put ^ in the .env where it says to


# macOS or Linux:
# Untested on macOS or Linux
# bootstrap.sh is for macOS or Linux
# everything else should be pretty much the same
# DM if this is an issue
