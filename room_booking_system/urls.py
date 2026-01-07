from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_login(request):
    """Redirect root URL to login"""
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('booking/', include('booking.urls')),  # Booking app integration
    path('', redirect_to_login), 
    path('chatbot/', include('chatbot.urls')),  # AI Chatbot (Deepseek-backed)
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path('accounts/', include('allauth.urls')),
    # path('social-auth/', include('social_django.urls', namespace='social')),
]