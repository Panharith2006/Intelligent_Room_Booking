from django.utils import timezone
from datetime import timedelta
from .models import Booking, BookingRule

class BookingRuleEnforcer:
    
    def __init__(self):
        self.rules = BookingRule.objects.first()
    
    def validate_booking_duration(self, start_time, end_time):
        """Validate booking duration against rules"""
        if not self.rules:
            return True, ""
        
        duration = end_time - start_time
        max_duration = timedelta(hours=self.rules.max_duration_hours)
        
        if duration > max_duration:
            return False, f"Booking duration cannot exceed {self.rules.max_duration_hours} hours."
        
        return True, ""
    
    def validate_advance_booking(self, booking_datetime):
        """Validate advance booking rules"""
        if not self.rules:
            return True, ""
        
        advance_time = booking_datetime - timezone.now()
        if advance_time.days > self.rules.max_advance_days:
            return False, f"Bookings can only be made {self.rules.max_advance_days} days in advance."
        
        return True, ""
    
    def validate_user_limits(self, user, booking_datetime):
        """Validate user booking limits"""
        if not self.rules:
            return True, ""
        
        errors = self.rules.check_user_can_book(user, booking_datetime)
        if errors:
            return False, "; ".join(errors)
        
        return True, ""
    
    def can_modify_booking(self, booking):
        """Check if booking can be modified"""
        if not self.rules or not self.rules.min_modify_hours:
            return True, ""
        
        time_until_booking = booking.start_time - timezone.now()
        if time_until_booking.total_seconds() < self.rules.min_modify_hours * 3600:
            return False, f"Bookings can only be modified {self.rules.min_modify_hours} hours in advance."
        
        return True, ""
    
    def get_user_booking_stats(self, user, date=None):
        """Get user's booking statistics"""
        if not date:
            date = timezone.now().date()
        
        # Daily bookings
        daily_bookings = Booking.objects.filter(
            user=user,
            start_time__date=date,
            status__in=['pending', 'confirmed']
        ).count()
        
        # Weekly bookings
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_bookings = Booking.objects.filter(
            user=user,
            start_time__date__range=[week_start, week_end],
            status__in=['pending', 'confirmed']
        ).count()
        
        return {
            'daily_bookings': daily_bookings,
            'daily_limit': self.rules.daily_booking_limit if self.rules else 0,
            'weekly_bookings': weekly_bookings,
            'weekly_limit': self.rules.weekly_booking_limit if self.rules else 0,
        }