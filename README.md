# This app is in a state of development
# Known Issues: Are known
# Currently in the final MVP phase
# Some things are broken right now because of some changes that are being made
# Once this final phase is done - hopefully in the next couple days
# It should be smooth sailing and better commentation will follow
# Then prep for deployment

# To git Started:
# Clone from GitHub

# Windows Set Up
# Open the repo in VS Code
# Start the Terminal

# In the terminal, type the following command and press Enter:
.\bootstrap.bat
# If you see: "We noticed... Do you...?" => CLICK YES

# Create your admin user so you can log in:
python manage.py createsuperuser

# Now you're all set up!
# DM if there are any issues


# In development
# Always be sure your terminal is:
(.venv) <Path> not just <Path>
# If it's not do:
.\.venv\Scripts\activate

# In dev, you'll likely just need:
# Runs the server
python manage.py runserver
# Stops the server
ctrl + c

# If you make changes to the database models (`models.py`), you need to create and apply migrations:
# Creates the migration files
python manage.py makemigrations
# Applies the migrations to the database
python manage.py migrate

# USING / TESTING FOR NOW
# Get the Upstash URL from Discord
# Put it in the .env where it says to
# Unknown if we actually need to ^^ but never not had it and haven't had time to be sure
# With the Server Running
# Go to http://127.0.0.1:localhost/admin
# localhost is whatever the number is there in your terminal not actually localhost
# Minimum local backend set up in admin:
# Click Courses > Add > Name: Hang Out Slug: hang-out Description: This is a universal tag!!! > Save and Add Another
# Name: CS 102 Slug: cs-102 Description: whatever > Save
# Click your user (the superuser you made)
# Give them an age
# give them Hang Out and CS 102 (click both (they will be highlighted) > save)
# Go to your profile http://127.0.0.1:localhost > Profile
# Upload 1 picture > You should see 1 picture + CS 102 on your profile and new button in top right with your new picture
# You can click the new button to return to your profile at any time
# http://127.0.0.1:localhost > Logout > Sign Up > New User > Open diff browser > Login to both accounts > Test with two users simultaneously


# Feel free to dm if there are any issues running the site, or working on it locally


# macOS or Linux
# Untested on macOS or Linux
# bootstrap.sh is for macOS or Linux
# everything else should be pretty much the same
# DM if this is an issue
