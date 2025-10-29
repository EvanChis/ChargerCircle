# config/views.py

# Import render, redirect from django.shortcuts because 'home_view' needs them.
from django.shortcuts import render, redirect

"""
Author:
This function handles the main home page ('/') of the website.
It checks if the user is already logged in. If they are, it
sends them straight to their dashboard. If they are not logged
in, it shows them the public landing page with options to
sign up or log in.
"""
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

