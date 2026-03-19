from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def hours_until(datetime_obj):
    """Calculate hours until the given datetime from now"""
    if not datetime_obj:
        return 0
    
    current_time = timezone.now()
    time_diff = datetime_obj - current_time
    hours = time_diff.total_seconds() / 3600
    return max(0, hours)  # Return 0 if time has passed

@register.filter
def can_cancel_booking(booking):
    """Check if booking can still be cancelled before it starts."""
    if booking.status not in ['pending', 'confirmed']:
        return False

    return hours_until(booking.start_time) > 0

@register.filter
def time_until_readable(datetime_obj):
    """Return human-readable time until booking"""
    if not datetime_obj:
        return "Unknown"
    
    current_time = timezone.now()
    time_diff = datetime_obj - current_time
    
    if time_diff.total_seconds() <= 0:
        return "Started"
    
    days = time_diff.days
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
