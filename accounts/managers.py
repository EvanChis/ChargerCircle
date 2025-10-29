# accounts/managers.py

# Import BaseUserManager from django.contrib.auth.base_user because 'CustomUserManager' is based on it.
from django.contrib.auth.base_user import BaseUserManager

"""
Author: Evan
This class provides the core logic for how user accounts are
created. It overrides Django's default behavior to use an
email address as the main login identifier instead of a username.
It contains two main functions: one for creating a regular
user ('create_user') and one for creating an administrator
('create_superuser').
"""
class CustomUserManager(BaseUserManager):
    
    # Custom user model manager where email is the unique identifier for authentication instead of usernames
    
    def create_user(self, email, password, **extra_fields):
        
        # Creates and saves a User with the given email and password.
        
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        
        # Creates and saves a SuperUser with the given email and password.
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

