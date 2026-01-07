import logging
from datetime import datetime, timedelta
from django.conf import settings
from allauth.socialaccount.models import SocialToken
import requests
import json

logger = logging.getLogger(__name__)

class GoogleCalendarIntegration:
    """Handles Google Calendar API integration"""
    
    def __init__(self, user):
        self.user = user
        self.calendar_api_url = "https://www.googleapis.com/calendar/v3"
    
    def get_access_token(self):
        """Get Google access token for the user"""
        try:
            # Get the most recent Google token for this user
            social_token = SocialToken.objects.filter(
                account__user=self.user,
                account__provider='google'
            ).first()
            
            if social_token:
                # Check if token is still valid or refresh if needed
                if self.is_token_valid(social_token.token):
                    return social_token.token
                else:
                    # Try to refresh the token
                    refreshed_token = self.refresh_access_token(social_token)
                    if refreshed_token:
                        return refreshed_token
            
            logger.warning(f"No valid Google token found for user {self.user.email}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting access token for {self.user.email}: {e}")
            return None
    
    def is_token_valid(self, token):
        """Check if the access token is still valid"""
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{self.calendar_api_url}/calendars/primary",
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def refresh_access_token(self, social_token):
        """Refresh the access token using refresh token"""
        try:
            if not social_token.token_secret:  # refresh_token
                logger.warning(f"No refresh token available for user {self.user.email}")
                return None
            
            logger.info(f"Token refresh needed for user {self.user.email}")
            return None
            
        except Exception as e:
            logger.error(f"Error refreshing token for {self.user.email}: {e}")
            return None
    
    def create_calendar_event(self, booking):
        """Create a calendar event for a room booking"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.warning(f"Cannot create calendar event - no access token for {self.user.email}")
                return False
            
            # Prepare event data
            event_data = {
                'summary': f'Room Booking: {booking.room.name}',
                'description': self.build_event_description(booking),
                'location': f'{booking.room.name} ({booking.room.room_number})',
                'start': {
                    'dateTime': booking.start_time.isoformat(),
                    'timeZone': 'Asia/Phnom_Penh',  # Cambodia timezone
                },
                'end': {
                    'dateTime': booking.end_time.isoformat(),
                    'timeZone': 'Asia/Phnom_Penh',
                },
                'attendees': [
                    {'email': self.user.email, 'displayName': self.user.get_full_name()}
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 minutes before
                    ],
                },
                'colorId': '2',  # Green color for room bookings
            }
            
            # Make API request to create event
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(
                f"{self.calendar_api_url}/calendars/primary/events",
                headers=headers,
                data=json.dumps(event_data),
                timeout=15
            )
            
            if response.status_code == 200:
                event_data = response.json()
                event_id = event_data.get('id')
                event_link = event_data.get('htmlLink')
                
                # Store the event ID in the booking for future reference
                booking.google_event_id = event_id
                booking.google_event_link = event_link
                booking.calendar_last_synced = datetime.now()
                booking.save()
                
                logger.info(f"Successfully created calendar event for booking {booking.id}")
                return True
                
            else:
                logger.error(f"Failed to create calendar event: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating calendar event for booking {booking.id}: {e}")
            return False
    
    def update_calendar_event(self, booking):
        """Update an existing calendar event"""
        try:
            if not hasattr(booking, 'google_event_id') or not booking.google_event_id:
                logger.warning(f"No calendar event ID found for booking {booking.id}")
                return False
            
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # Prepare updated event data
            event_data = {
                'summary': f'Room Booking: {booking.room.name}',
                'description': self.build_event_description(booking),
                'location': f'{booking.room.name} ({booking.room.room_number})',
                'start': {
                    'dateTime': booking.start_time.isoformat(),
                    'timeZone': 'Asia/Phnom_Penh',
                },
                'end': {
                    'dateTime': booking.end_time.isoformat(),
                    'timeZone': 'Asia/Phnom_Penh',
                },
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            
            response = requests.put(
                f"{self.calendar_api_url}/calendars/primary/events/{booking.google_event_id}",
                headers=headers,
                data=json.dumps(event_data),
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated calendar event for booking {booking.id}")
                return True
            else:
                logger.error(f"Failed to update calendar event: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating calendar event for booking {booking.id}: {e}")
            return False
    
    def delete_calendar_event(self, booking):
        """Delete a calendar event when booking is cancelled"""
        try:
            if not hasattr(booking, 'google_event_id') or not booking.google_event_id:
                return True  # No event to delete
            
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.delete(
                f"{self.calendar_api_url}/calendars/primary/events/{booking.google_event_id}",
                headers=headers,
                timeout=15
            )
            
            if response.status_code in [200, 204, 410]:  # 410 = already deleted
                logger.info(f"Successfully deleted calendar event for booking {booking.id}")
                booking.google_event_id = None
                booking.google_event_link = None
                booking.save()
                return True
            else:
                logger.error(f"Failed to delete calendar event: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting calendar event for booking {booking.id}: {e}")
            return False
    
    def build_event_description(self, booking):
        """Build a detailed description for the calendar event"""
        description = f"""
🏢 Room Booking Details

📍 Room: {booking.room.name} ({booking.room.room_number})
👥 Capacity: {booking.room.capacity} people
🎯 Purpose: {booking.purpose}
👤 Attendees: {booking.attendees}

📝 Additional Notes:
{booking.additional_notes or 'No additional notes'}

🏫 RUPP Room Booking System
Booking ID: {booking.id}
Status: {booking.status.title()}
        """.strip()
        
        return description

# Utility functions for easy access
def create_calendar_event_for_booking(booking):
    """Create a calendar event for a booking if user has Google account connected"""
    try:
        # Check if user has Google account connected
        if not hasattr(booking.user, 'socialaccount_set'):
            return False
        
        google_account = booking.user.socialaccount_set.filter(provider='google').first()
        if not google_account:
            return False
        
        # Create calendar integration instance and create event
        calendar_integration = GoogleCalendarIntegration(booking.user)
        return calendar_integration.create_calendar_event(booking)
        
    except Exception as e:
        logger.error(f"Error in create_calendar_event_for_booking: {e}")
        return False

def update_calendar_event_for_booking(booking):
    """Update calendar event when booking is modified"""
    try:
        if not hasattr(booking.user, 'socialaccount_set'):
            return False
        
        google_account = booking.user.socialaccount_set.filter(provider='google').first()
        if not google_account:
            return False
        
        calendar_integration = GoogleCalendarIntegration(booking.user)
        return calendar_integration.update_calendar_event(booking)
        
    except Exception as e:
        logger.error(f"Error in update_calendar_event_for_booking: {e}")
        return False

def delete_calendar_event_for_booking(booking):
    """Delete calendar event when booking is cancelled"""
    try:
        if not hasattr(booking.user, 'socialaccount_set'):
            return True
        
        google_account = booking.user.socialaccount_set.filter(provider='google').first()
        if not google_account:
            return True
        
        calendar_integration = GoogleCalendarIntegration(booking.user)
        return calendar_integration.delete_calendar_event(booking)
        
    except Exception as e:
        logger.error(f"Error in delete_calendar_event_for_booking: {e}")
        return False