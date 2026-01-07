# forms.py
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import Room, Booking, BookingRule
from .models import Room, Booking, BookingRule, Announcement
from django.contrib.auth import get_user_model
User = get_user_model()


class RoomForm(forms.ModelForm):
    """Form for creating and editing rooms"""
    
    class Meta:
        model = Room
        fields = [
            'name',
            'room_number',
            'room_type',
            'capacity',
            'description',
            'equipment',
            'image',
            'is_available',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter room name'
            }),
            'room_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., A-101 (duplicates allowed)'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Maximum occupancy'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of the room'
            }),
            'equipment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Available equipment (comma-separated)'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity and capacity < 1:
            raise forms.ValidationError('Capacity must be at least 1.')
        return capacity

    def clean_room_number(self):
        """Allow duplicate room numbers for both new and existing rooms"""
        room_number = self.cleaned_data.get('room_number')
        if room_number:
            # Just clean whitespace but don't enforce uniqueness
            room_number = room_number.strip()
            # Explicitly allow duplicates - no validation against existing room numbers
            return room_number
        return room_number

    def clean_image(self):
        """Validate image file"""
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (10MB limit)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Image file size should be less than 10MB.')
            
            # Check file type
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError('Please upload a valid image file (JPG, PNG, GIF, etc.).')
        
        return image

    def clean(self):
        """Override clean method to explicitly allow duplicate room numbers with images"""
        cleaned_data = super().clean()
        
        # Explicitly allow duplicate room numbers regardless of other fields
        # This overrides any potential uniqueness validation
        room_number = cleaned_data.get('room_number')
        if room_number:
            # No validation against existing room numbers - duplicates are explicitly allowed
            pass
        
        return cleaned_data


class RoomSearchForm(forms.Form):
    """Form for searching and filtering rooms"""
    
    ROOM_TYPE_CHOICES = [
        ('', 'All Types'),
        ('conference', 'Conference Room'),
        ('meeting', 'Meeting Room'),
        ('classroom', 'Classroom'),
        ('lab', 'Laboratory'),
        ('auditorium', 'Auditorium'),
        ('office', 'Office'),
        ('other', 'Other'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search rooms by name, number, or description...'
        })
    )
    
    room_type = forms.ChoiceField(
        choices=ROOM_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    min_capacity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min capacity',
            'min': '1'
        })
    )
    
    max_capacity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max capacity',
            'min': '1'
        })
    )
    
    availability_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    
    available_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        min_capacity = cleaned_data.get('min_capacity')
        max_capacity = cleaned_data.get('max_capacity')
        availability_date = cleaned_data.get('availability_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate capacity range
        if min_capacity and max_capacity and min_capacity > max_capacity:
            raise forms.ValidationError('Minimum capacity cannot be greater than maximum capacity.')
        
        # Validate time range
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Start time must be before end time.')
        
        # If checking availability, all date/time fields are required
        if any([availability_date, start_time, end_time]):
            if not all([availability_date, start_time, end_time]):
                raise forms.ValidationError('Date, start time, and end time are all required for availability checking.')
        
        return cleaned_data


class BookingForm(forms.ModelForm):
    """Form for creating and editing bookings"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    
    class Meta:
        model = Booking
        fields = ['room', 'purpose', 'attendees', 'start_date', 'start_time', 'end_time']
        widgets = {
            'room': forms.Select(attrs={
                'class': 'form-control'
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the meeting purpose'
            }),
            'attendees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Number of attendees'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show available rooms
        self.fields['room'].queryset = Room.objects.filter(is_available=True)
        
        # Set default values
        if not self.instance.pk:  # Only for new bookings
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['start_time'].initial = time(9, 0)  # 9:00 AM
            self.fields['end_time'].initial = time(10, 0)   # 10:00 AM

    def clean_attendees(self):
        attendees = self.cleaned_data.get('attendees')
        room = self.cleaned_data.get('room')
        
        if attendees and room and attendees > room.capacity:
            raise forms.ValidationError(
                f'Number of attendees ({attendees}) exceeds room capacity ({room.capacity}).'
            )
        
        return attendees

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        room = cleaned_data.get('room')
        
        if not all([start_date, start_time, end_time]):
            return cleaned_data
        
        # Validate time range
        if start_time >= end_time:
            raise forms.ValidationError('Start time must be before end time.')
        
        # Create datetime objects
        start_datetime = timezone.make_aware(datetime.combine(start_date, start_time))
        end_datetime = timezone.make_aware(datetime.combine(start_date, end_time))
        
        # Check if booking is in the past
        if start_datetime <= timezone.now():
            raise forms.ValidationError('Booking cannot be in the past.')
        
        # Check if booking is too far in the future (e.g., 6 months)
        if start_datetime > timezone.now() + timedelta(days=180):
            raise forms.ValidationError('Booking cannot be more than 6 months in advance.')
        
        # Check for conflicts (exclude current booking if editing)
        if room:
            conflicts = Booking.objects.filter(
                room=room,
                start_time__lt=end_datetime,
                end_time__gt=start_datetime,
                    status__in=['confirmed']
            )
            
            # Exclude current booking if editing
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            
            if conflicts.exists():
                # Get details of conflicting booking for better error message
                conflict = conflicts.first()
                conflict_start = conflict.start_time.strftime('%I:%M %p')
                conflict_end = conflict.end_time.strftime('%I:%M %p')
                conflict_user = conflict.user.get_full_name() or conflict.user.username
                
                raise forms.ValidationError(
                    f'This time slot conflicts with an existing booking by {conflict_user} '
                    f'from {conflict_start} to {conflict_end}. Please choose a different time.'
                )
        
        # Store combined datetime for use in views
        cleaned_data['start_datetime'] = start_datetime
        cleaned_data['end_datetime'] = end_datetime
        
        return cleaned_data


class BookingSearchForm(forms.Form):
    """Form for searching bookings"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by room name or purpose...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('Start date must be before end date.')
        
        return cleaned_data


class QuickBookingForm(forms.Form):
    """Simplified form for quick bookings"""
    
    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_available=True),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    
    duration = forms.ChoiceField(
        choices=[
            (30, '30 minutes'),
            (60, '1 hour'),
            (90, '1.5 hours'),
            (120, '2 hours'),
            (180, '3 hours'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    purpose = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Meeting purpose'
        })
    )
    
    attendees = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': 'Number of attendees'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        self.fields['date'].initial = timezone.now().date()
        self.fields['start_time'].initial = time(9, 0)
        self.fields['duration'].initial = 60

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        duration = cleaned_data.get('duration')
        room = cleaned_data.get('room')
        attendees = cleaned_data.get('attendees')
        
        if not all([date, start_time, duration]):
            return cleaned_data
        
        # Calculate end time
        start_datetime = timezone.make_aware(datetime.combine(date, start_time))
        end_datetime = start_datetime + timedelta(minutes=int(duration))
        
        # Validate booking time
        if start_datetime <= timezone.now():
            raise forms.ValidationError('Booking cannot be in the past.')
        
        # Check room capacity
        if room and attendees and attendees > room.capacity:
            raise forms.ValidationError(
                f'Number of attendees ({attendees}) exceeds room capacity ({room.capacity}).'
            )
        
        # Check for conflicts
        if room:
            conflicts = Booking.objects.filter(
                room=room,
                start_time__lt=end_datetime,
                end_time__gt=start_datetime,
                status__in=['pending', 'confirmed']
            )
            
            if conflicts.exists():
                raise forms.ValidationError('This time slot conflicts with an existing booking.')
        
        # Store calculated values
        cleaned_data['start_datetime'] = start_datetime
        cleaned_data['end_datetime'] = end_datetime
        
        return cleaned_data


class BookingRuleForm(forms.ModelForm):
    """Form for creating and editing booking rules"""
    
    class Meta:
        model = BookingRule
        fields = [
            'name',
            'max_duration_hours',
            'daily_booking_limit',
            'weekly_booking_limit',
            'max_advance_days',
            'min_advance_hours',
            'min_cancel_hours',
            'min_modify_hours',
            'booking_start_time',
            'booking_end_time',
            'is_active',
        ]

    
class AdminBookingForm(forms.ModelForm):
    """Form for admin to create/edit bookings"""
    class Meta:
        model = Booking
        fields = ['user', 'room', 'start_time', 'end_time', 'purpose', 'status']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter booking purpose'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active users
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('first_name')
        # Only show available rooms
        self.fields['room'].queryset = Room.objects.filter(is_available=True).order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        room = cleaned_data.get('room')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("End time must be after start time.")
            
            # Check for conflicts (exclude current booking if editing)
            conflicts = Booking.objects.filter(
                room=room,
                    status__in=['confirmed'],
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            
            if conflicts.exists():
                raise forms.ValidationError("This time slot conflicts with an existing booking.")
        
        return cleaned_data


class AnnouncementForm(forms.ModelForm):
    """Form for creating/editing announcements"""
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'announcement_type', 'priority', 'is_active', 'show_until']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter announcement title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter announcement content'}),
            'announcement_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def clean_show_until(self):
        show_until = self.cleaned_data.get('show_until')
        if show_until:
            from django.utils import timezone
            if show_until <= timezone.now():
                raise forms.ValidationError("Show until date must be in the future.")
        return show_until

class BulkRoomActionForm(forms.Form):
    """Form for bulk room actions"""
    ACTION_CHOICES = [
        ('make_available', 'Make Available'),
        ('make_unavailable', 'Make Unavailable'),
        ('delete', 'Delete'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    room_ids = forms.ModelMultipleChoiceField(
        queryset=Room.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

class BookingFilterForm(forms.Form):
    """Form for filtering bookings in admin"""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name'),
        required=False,
        empty_label="All Users",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.all().order_by('name'),
        required=False,
        empty_label="All Rooms",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Booking.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class UserSearchForm(forms.Form):
    """Form for searching users"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name, email, or student ID'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All'), ('active', 'Active'), ('inactive', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )