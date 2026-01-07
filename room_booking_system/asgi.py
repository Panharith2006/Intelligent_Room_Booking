"""
ASGI config for room_booking_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')

application = get_asgi_application()

"""
Serve static and media files in development when using ASGI (uvicorn).

WhiteNoise is a WSGI middleware. To use it with an ASGI server we wrap
the WSGI application with WhiteNoise and then convert it to ASGI using
``asgiref.wsgi.WsgiToAsgi``. This provides a simple static/media serving
solution during development when running with uvicorn.
"""
try:
	from django.conf import settings
	from django.core.wsgi import get_wsgi_application
	from asgiref.wsgi import WsgiToAsgi
	from whitenoise import WhiteNoise

	# Build WSGI app and wrap with WhiteNoise
	wsgi_app = get_wsgi_application()

	static_root = getattr(settings, 'STATIC_ROOT', None)
	if not static_root:
		static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
		static_root = static_dirs[0] if static_dirs else None

	if static_root:
		wsgi_app = WhiteNoise(wsgi_app, root=str(static_root))

		# Serve media files too
		media_root = getattr(settings, 'MEDIA_ROOT', None)
		if media_root:
			wsgi_app.add_files(str(media_root), prefix=getattr(settings, 'MEDIA_URL', '/media/').lstrip('/'))

	# Convert WSGI app (with WhiteNoise) to ASGI
	application = WsgiToAsgi(wsgi_app)
except Exception:
	# If something goes wrong, keep the original ASGI application
	pass
