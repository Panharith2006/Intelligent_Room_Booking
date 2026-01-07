# ===== booking/context_processors.py =====
from django.utils import timezone
from django.db.models import Q

def room_types(request):
    """Add room types to template context"""
    from .models import Room
    return {
        'ROOM_TYPES': Room.ROOM_TYPES,
    }

def active_announcements(request):
    """Add active announcements to template context for all pages"""
    try:
        from .models import Announcement
        
        # Only show announcements to authenticated users
        if request.user.is_authenticated and not request.user.is_superuser:
            announcements = Announcement.objects.filter(
                is_active=True
            ).filter(
                Q(show_until__isnull=True) | Q(show_until__gte=timezone.now())
            ).order_by('-priority', '-created_at')[:3]  # Limit to 3 most important
            
            return {'global_announcements': announcements}
    except:
        pass
    
    return {'global_announcements': []}