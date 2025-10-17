# config/views.py

from django.shortcuts import render, redirect

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')
