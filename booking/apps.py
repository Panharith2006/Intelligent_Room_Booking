from django.apps import AppConfig


class BookingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booking'
    
    def ready(self):
        """Import signals when the app is ready"""
        import booking.signals
        import booking.telegram_notifications  # Import Telegram notifications
