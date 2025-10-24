# Python 3
# Scripts enabled in Windows

# To git Started:
# Clone from GitHub

# Windows
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
# DM if there are any issues


# In dev, mostly need:
# Runs the server
python manage.py runserver
# Stops the server
ctrl + c
# If desired:
deactivate

# If changes are made to database models (`models.py`), create and apply migrations:
# Creates migration files
python manage.py makemigrations
# Applies migrations to database
python manage.py migrate

# USING / TESTING FOR NOW
# Get Upstash URL from Discord
# Put ^ in the .env where it says to
# This ^ is a deployment URL. Else, have to download Redis and run it
# With the Server Running
# Go to http://127.0.0.1:localhost/admin
# localhost is whatever number it says in terminal
# Minimal admin set up:
# Click Courses > Add > Name: Hang Out Slug: hang-out Description: This is a universal tag!!! > Save and Add Another
# Name: CS 102 Slug: cs-102 Description: whatever > Save
# Click your user (the superuser you made)
# Give them an age
# give them Hang Out and CS 102 (click both (they will be highlighted) > save)
# Go to your profile http://127.0.0.1:localhost > Profile
# Upload 1 picture > You should see 1 picture + CS 102 on your profile and new button in top right with your new picture
# You can click the new button to return to your profile at any time
# http://127.0.0.1:localhost > Logout > Sign Up > New User > Open diff browser > Login to both accounts
# > Test with two users simultaneously


# Feel free to dm if there are any issues running the app, or working on it locally


# macOS or Linux
# Untested on macOS or Linux
# bootstrap.sh is for macOS or Linux
# everything else should be pretty much the same
# DM if this is an issue
