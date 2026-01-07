"""
Setup Google OAuth Application

To use Google OAuth in your Room Booking System, you need to:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select existing project
3. Enable Google+ API and Google Identity API
4. Go to Credentials section
5. Create OAuth 2.0 Client ID
6. Set Authorized redirect URIs to:
   - http://localhost:8000/accounts/google/login/callback/
   - http://127.0.0.1:8000/accounts/google/login/callback/
   - Your production domain callback URL
7. Copy the Client ID and Client Secret

Then run this command to add them to your Django admin:
python manage.py setup_google_oauth --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

Or add them manually in Django admin:
1. Go to /admin/
2. Navigate to "Social Applications" 
3. Add new Social Application:
   - Provider: Google
   - Name: Google
   - Client id: [Your Google Client ID]
   - Secret key: [Your Google Client Secret]
   - Sites: Select your site (usually localhost:8000)
"""

from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Setup Google OAuth application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=str,
            help='Google OAuth Client ID',
        )
        parser.add_argument(
            '--client-secret',
            type=str,
            help='Google OAuth Client Secret',
        )

    def handle(self, *args, **options):
        if not options['client_id'] or not options['client_secret']:
            self.stdout.write(
                self.style.WARNING(__doc__)
            )
            return

        # Get or create the Google social app
        google_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': options['client_id'],
                'secret': options['client_secret'],
            }
        )

        if not created:
            # Update existing app
            google_app.client_id = options['client_id']
            google_app.secret = options['client_secret']
            google_app.save()

        # Add current site to the app
        current_site = Site.objects.get_current()
        google_app.sites.add(current_site)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully {"created" if created else "updated"} Google OAuth application!\n'
                f'Client ID: {options["client_id"]}\n'
                f'Site: {current_site.domain}\n'
                f'Callback URL: http://{current_site.domain}/accounts/google/login/callback/'
            )
        )
