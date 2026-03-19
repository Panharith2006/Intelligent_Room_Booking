from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for handling Google OAuth sign-ups and logins
    Open for ALL Google accounts - no email domain restrictions
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow signup for ANY Google account - no domain restrictions
        """
        return True  # Always allow Google account registration
    
    def pre_social_login(self, request, sociallogin):
        """
        Called after a user successfully authenticates via a social provider,
        but before the login is processed.
        Open for all Google email domains.
        """
        user = sociallogin.user
        
        if sociallogin.is_existing:
            # User already exists, proceed with login
            messages.success(request, f'Welcome back, {user.first_name}! You have been signed in with Google.')
            return
        
        # Check if a user with this email already exists
        if user.email:
            try:
                existing_user = User.objects.get(email=user.email)
                # Connect the social account to existing user
                sociallogin.connect(request, existing_user)
                messages.info(request, f'Successfully connected your Google account to your existing account.')
                return
            except User.DoesNotExist:
                # No existing user with this email, will create new user
                pass
    
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        Enhanced to allow better profile editing later.
        """
        user = sociallogin.user
        
        # Get user data from Google
        extra_data = sociallogin.account.extra_data
        
        # Set user fields from Google data with better handling
        if not user.first_name and extra_data.get('given_name'):
            user.first_name = extra_data.get('given_name', '').strip().title()
        
        if not user.last_name and extra_data.get('family_name'):
            user.last_name = extra_data.get('family_name', '').strip().title()
            
        # If no separate first/last name, try to split the full name
        if not user.first_name and not user.last_name and extra_data.get('name'):
            full_name = extra_data.get('name', '').strip()
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0].title() if name_parts else ''
            user.last_name = name_parts[1].title() if len(name_parts) > 1 else ''
        
        # Generate student ID if not exists - make it clear it's from Google
        if not hasattr(user, 'student_id') or not user.student_id:
            user.student_id = "" # Leave empty so user can add their real student ID later
        
        # Set default values for required fields that can be edited later
        if not hasattr(user, 'phone_number') or not user.phone_number:
            user.phone_number = ""  # Leave empty so user can add their real number
        
        if not hasattr(user, 'faculty') or not user.faculty:
            user.faculty = ""  # Leave empty so user can select their faculty
        
        if not hasattr(user, 'department') or not user.department:
            user.department = ""  # Leave empty so user can add their department

        if hasattr(user, 'booking_approval_status'):
            user.booking_approval_status = 'pending'
        
        # Save the user
        user.save()
        
        # Add user to User group
        try:
            user_group, created = Group.objects.get_or_create(name='User')
            user.groups.add(user_group)
            logger.info(f"Added Google user {user.email} to User group")
        except Exception as e:
            logger.error(f"Failed to add user to group: {e}")
        
        # Enhanced welcome message encouraging profile completion
        welcome_msg = f'Welcome {user.first_name}! Your Google account has been successfully registered. '
        welcome_msg += 'You can now access all features and your room bookings will automatically sync with your Google Calendar!'
        messages.success(request, welcome_msg)
        
        return user
    
    def get_login_redirect_url(self, request):
        """
        Return the URL to redirect to after successful login.
        """
        user = request.user
        
        # Check user role and redirect accordingly
        if user.groups.filter(name='Admin').exists():
            return '/accounts/admin-dashboard/'
        else:
            return '/accounts/user-dashboard/'
    
    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Handle authentication errors
        """
        logger.error(f"Google authentication error: {error}, Exception: {exception}")
        messages.error(request, 'Failed to authenticate with Google. Please try again or use regular login.')
        return redirect('accounts:login')
