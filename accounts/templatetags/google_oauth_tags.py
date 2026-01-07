"""
Custom template tags for handling Google OAuth integration safely.
"""
from django import template
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.templatetags.socialaccount import provider_login_url
from allauth.socialaccount.providers.google.provider import GoogleProvider
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def safe_google_login_url(context):
    """
    Safely get Google login URL only if Google OAuth is properly configured.
    Returns empty string if Google SocialApp is not configured.
    """
    try:
        # Check if Google SocialApp exists
        SocialApp.objects.get(provider=GoogleProvider.id)
        # If it exists, return the actual login URL
        return provider_login_url(context, GoogleProvider.id)
    except SocialApp.DoesNotExist:
        # Return empty string if Google OAuth is not configured
        return ""


@register.simple_tag
def google_oauth_configured():
    """
    Check if Google OAuth is properly configured.
    Returns True if Google SocialApp exists, False otherwise.
    """
    try:
        SocialApp.objects.get(provider=GoogleProvider.id)
        return True
    except SocialApp.DoesNotExist:
        return False


@register.simple_tag(takes_context=True)
def safe_google_signup_url(context):
    """
    Safely get Google signup URL only if Google OAuth is properly configured.
    For registration, we can use the same login URL as allauth handles both.
    The 'process' parameter helps allauth understand the context.
    """
    try:
        # Check if Google SocialApp exists
        SocialApp.objects.get(provider=GoogleProvider.id)
        # If it exists, return the actual login URL (which handles signup too)
        # Add process=signup to help allauth understand the context
        login_url = provider_login_url(context, GoogleProvider.id)
        if login_url and '?' in login_url:
            return f"{login_url}&process=signup"
        elif login_url:
            return f"{login_url}?process=signup"
        return login_url
    except SocialApp.DoesNotExist:
        # Return empty string if Google OAuth is not configured
        return ""


@register.simple_tag(takes_context=True) 
def safe_google_login_url_with_process(context, process="login"):
    """
    Safely get Google login/signup URL with explicit process parameter.
    """
    try:
        # Check if Google SocialApp exists
        SocialApp.objects.get(provider=GoogleProvider.id)
        # If it exists, return the actual login URL
        login_url = provider_login_url(context, GoogleProvider.id)
        if login_url and '?' in login_url:
            return f"{login_url}&process={process}"
        elif login_url:
            return f"{login_url}?process={process}"
        return login_url
    except SocialApp.DoesNotExist:
        # Return empty string if Google OAuth is not configured
        return ""
