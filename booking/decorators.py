# booking/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden

def admin_required(view_func):
    """Decorator to require admin privileges"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        
        # Allow access if user is admin, staff, or superuser
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access denied. Admin privileges required.')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def staff_required(view_func):
    """Decorator to require staff privileges (admin or staff)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')

        if not (request.user.is_admin or request.user.is_staff):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access denied. Staff privileges required.')

        return view_func(request, *args, **kwargs)
    return wrapper
