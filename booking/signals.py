"""
Django signals for booking app
Handles automatic Google Calendar integration
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking
from .google_calendar import (
    create_calendar_event_for_booking,
    update_calendar_event_for_booking,
    delete_calendar_event_for_booking
)
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def handle_booking_save(sender, instance, created, **kwargs):
    """
    Handle booking creation and updates
    Automatically create/update Google Calendar events
    """
    try:
        if created:
            # New booking created - create calendar event
            logger.info(f"New booking created: {instance.id} for user {instance.user.email}")
            
            # Only create calendar event for confirmed bookings
            if instance.status == 'confirmed':
                success = create_calendar_event_for_booking(instance)
                if success:
                    logger.info(f"Successfully created calendar event for booking {instance.id}")
                else:
                    logger.warning(f"Failed to create calendar event for booking {instance.id}")
                    
        else:
            # Existing booking updated
            logger.info(f"Booking updated: {instance.id}")
            
            # If booking was cancelled, delete calendar event
            if instance.status in ['cancelled', 'no_show']:
                success = delete_calendar_event_for_booking(instance)
                if success:
                    logger.info(f"Successfully deleted calendar event for cancelled booking {instance.id}")
                    
            # If booking details changed and it's still confirmed, update calendar event
            elif instance.status == 'confirmed' and instance.google_event_id:
                success = update_calendar_event_for_booking(instance)
                if success:
                    logger.info(f"Successfully updated calendar event for booking {instance.id}")
                    
            # If booking was just confirmed and doesn't have a calendar event yet
            elif instance.status == 'confirmed' and not instance.google_event_id:
                success = create_calendar_event_for_booking(instance)
                if success:
                    logger.info(f"Successfully created calendar event for newly confirmed booking {instance.id}")
                    
    except Exception as e:
        logger.error(f"Error in booking signal handler: {e}")

@receiver(post_delete, sender=Booking)
def handle_booking_delete(sender, instance, **kwargs):
    """
    Handle booking deletion
    Delete associated Google Calendar events
    """
    try:
        logger.info(f"Booking deleted: {instance.id}")
        
        if instance.google_event_id:
            success = delete_calendar_event_for_booking(instance)
            if success:
                logger.info(f"Successfully deleted calendar event for deleted booking {instance.id}")
            else:
                logger.warning(f"Failed to delete calendar event for deleted booking {instance.id}")
                
    except Exception as e:
        logger.error(f"Error in booking deletion signal: {e}")

# Signal to track booking changes for calendar updates
@receiver(pre_save, sender=Booking)
def track_booking_changes(sender, instance, **kwargs):
    """
    Track changes to booking for calendar sync
    Store the previous state to determine what changed
    """
    if instance.pk:
        try:
            instance._previous_state = Booking.objects.get(pk=instance.pk)
        except Booking.DoesNotExist:
            instance._previous_state = None
    else:
        instance._previous_state = None