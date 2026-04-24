def format_support_message(name, email, subject, message):
    """Format a support message for Telegram notification."""
    return (
        f"\U0001F6A8 *User Issue Reported* \U0001F6A8\n"
        f"*From:* {name} ({email})\n"
        f"*Subject:* {subject}\n"
        f"*Message:* {message}"
    )

def send_support_message_to_telegram(name, email, subject, message):
    """Send a support message to all admin Telegram chat IDs."""
    if not ADMIN_CHAT_IDS:
        logger.warning("No ADMIN_CHAT_IDS configured for Telegram support alerts.")
        return
    alert_msg = format_support_message(name, email, subject, message)
    logger.info(f"[DEBUG] ADMIN_CHAT_IDS in send_support_message_to_telegram: {ADMIN_CHAT_IDS}")
    logger.info(f"[DEBUG] Alert message: {alert_msg}")
    for chat_id in ADMIN_CHAT_IDS:
        logger.info(f"[DEBUG] Sending Telegram alert to chat_id: {chat_id}")
        send_telegram_message(chat_id, alert_msg, parse_mode='Markdown')
import requests
import logging
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Booking
from accounts.models import User

logger = logging.getLogger(__name__)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
ADMIN_CHAT_IDS = getattr(settings, 'TELEGRAM_ADMIN_CHAT_IDS', [])  # List of admin chat IDs

def send_telegram_message(chat_id, message, parse_mode='Markdown'):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Telegram message sent successfully to {chat_id}")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False

def format_booking_notification(booking, action="created"):
    user = booking.user
    room = booking.room
    
    # Emoji based on action with bright colors
    emoji_map = {
        'confirmed': '✅', 
        'cancelled': '🔴', 
    }
    
    action_text = {
        'created': 'New Booking',
        'confirmed': 'Booking Confirmed',
        'cancelled': 'Booking Cancelled',
        'updated': 'Booking Updated'
    }
    
    emoji = emoji_map.get(action, '📋')
    title = action_text.get(action, 'Booking Notification')
    
    # Calculate duration
    duration_hours = int((booking.end_time - booking.start_time).total_seconds() / 3600)
    duration_mins = int(((booking.end_time - booking.start_time).total_seconds() % 3600) / 60)
    if duration_mins > 0:
        duration_text = f"{duration_hours}h {duration_mins}m"
    else:
        duration_text = f"{duration_hours}h"
    
    message = f"""{emoji} *{title}*

👤 *User*: {user.get_full_name() or user.username}
📧 *Email*: {user.email}

🏢 *Room*: {room.name} ({room.room_number})
👥 *Capacity*: {room.capacity} people
🙋 *Participants*: {booking.attendees} people
🏷️ *Type*: {room.room_type.title()}

📅 *Date*: {booking.start_time.strftime('%A, %B %d, %Y')}
⏰ *Time*: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}
⏱️ *Duration*: {duration_text}
🎯 *Purpose*: _{booking.purpose or 'Not specified'}_
📝 *Additional Notes*: _{booking.additional_notes or 'None'}_

🆔 *Booking ID*: #{booking.id}
━━━━━━━━━━━━━━
{emoji} *Status*: {booking.status.upper()}"""

    return message

@receiver(post_save, sender=Booking)
def booking_created_notification(sender, instance, created, **kwargs):
    if not ADMIN_CHAT_IDS:
        return
    
    if created:
        # New booking created
        message = format_booking_notification(instance, "created")
        for chat_id in ADMIN_CHAT_IDS:
            send_telegram_message(chat_id, message)
    
    else:
        # Booking was updated - check if status changed
        try:
            # Check if status changed to cancelled or confirmed
            if hasattr(instance, '_previous_status'):
                old_status = instance._previous_status
                new_status = instance.status
                
                # Notify on status changes to confirmed or cancelled
                if old_status != new_status and new_status in ['confirmed', 'cancelled']:
                    action = new_status
                    message = format_booking_notification(instance, action)
                    for chat_id in ADMIN_CHAT_IDS:
                        send_telegram_message(chat_id, message)
                        
        except Exception as e:
            logger.error(f"Error checking booking status change: {e}")

@receiver(pre_save, sender=Booking)
def track_booking_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except Booking.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

def alert_to_admins(message):
    if not ADMIN_CHAT_IDS:
        return

    for chat_id in ADMIN_CHAT_IDS:
        send_telegram_message(chat_id, message)






