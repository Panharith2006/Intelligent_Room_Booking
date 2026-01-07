# admin.py - Fixed version
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Room, Booking, BookingRule, Announcement

# @admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser"""
    
    # Remove 'is_admin' and replace with appropriate fields
    list_display = (
        'username', 
        'email', 
        'get_full_name', 
        'user_type',  
        'is_approved', 
        'is_active', 
        'date_joined'
    )
    
    list_filter = (
        'user_type',  
        'is_approved', 
        'is_active', 
        'is_superuser',
        'date_joined'
    )
    
    search_fields = ('username', 'email', 'first_name', 'last_name', 'student_id')
    
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    # Customize the fieldsets to include new fields
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': (
                'user_type', 
                'student_id', 
                'phone_number', 
                'department',
                'is_approved',
                'max_concurrent_bookings'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': (
                'user_type', 
                'student_id', 
                'phone_number', 
                'department',
                'is_approved'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Admin configuration for Room"""
    
    def room_image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:48px; width:auto; border-radius:6px; object-fit:cover;" />', obj.image.url)
        return format_html('<span style="color:#888;">No image</span>')
    room_image_thumb.short_description = 'Image'

    list_display = (
        'room_image_thumb',
        'name',
        'room_number',
        'room_type',
        'capacity',
        'availability_status',
        'is_available',
        'is_bookable_status'
    )

    list_filter = (
        'room_type',
        'availability_status',
        'is_available',
        'created_at'
    )

    search_fields = ('name', 'room_number', 'description')

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'room_number', 'room_type', 'capacity', 'image')
        }),
        ('Details', {
            'fields': ('description', 'equipment')
        }),
        ('Status', {
            'fields': ('availability_status', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_bookable_status(self, obj):
        """Display bookable status with color coding"""
        if obj.is_bookable():
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Bookable</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Not Bookable</span>'
            )
    is_bookable_status.short_description = 'Bookable'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Admin configuration for Booking"""
    
    list_display = (
        'room', 
        'user', 
        'start_time', 
        'end_time', 
        'status',
        'duration_display',
        'is_active_status'
    )
    
    list_filter = (
        'status', 
        'room__room_type',
        'start_time',
        'created_at'
    )
    
    search_fields = (
        'user__username', 
        'user__first_name', 
        'user__last_name',
        'room__name', 
        'room__room_number',
        'purpose'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'duration_hours')
    
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Booking Details', {
            'fields': ('user', 'room', 'start_time', 'end_time')
        }),
        ('Purpose & Notes', {
            'fields': ('purpose', 'additional_notes')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Information', {
            'fields': ('duration_hours', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        """Display booking duration in hours"""
        return f"{obj.duration_hours:.1f}h"
    duration_display.short_description = 'Duration'
    
    def is_active_status(self, obj):
        """Display if booking is currently active"""
        if obj.is_available():
            return format_html(
                '<span style="color: green; font-weight: bold;">● Active</span>'
            )
        else:
            return format_html(
                '<span style="color: gray;">○ Inactive</span>'
            )
    is_active_status.short_description = 'Active'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'room')

@admin.register(BookingRule)
class BookingRuleAdmin(admin.ModelAdmin):
    """Admin configuration for BookingRule"""
    
    list_display = (
        'name', 
        'max_duration_hours',
        "daily_booking_limit",
        "weekly_booking_limit",
        'max_advance_days',
        'is_active'
    )
    
    list_filter = ('is_active', 'created_at')
    
    search_fields = ('name',)
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Rule Name', {
            'fields': ('name', 'is_active')
        }),
        ('Booking Limits', {
            'fields': (
                'max_duration_hours',
                'daily_booking_limit', 
                'weekly_booking_limit',
            )
        }),
        ('Time Constraints', {
            'fields': (
                'max_advancee_days',
                'min_advance_hours',
                'booking_start_time',
                'booking_end_time'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Admin configuration for Announcement"""
    
    list_display = (
        'title', 
        'announcement_type', 
        'priority',
        'is_active',
        'is_visible_status',
        'created_by',
        'created_at'
    )
    
    list_filter = (
        'announcement_type', 
        'priority', 
        'is_active',
        'created_at'
    )
    
    search_fields = ('title', 'content')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Announcement Content', {
            'fields': ('title', 'content')
        }),
        ('Classification', {
            'fields': ('announcement_type', 'priority')
        }),
        ('Visibility', {
            'fields': ('is_active', 'show_until')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_visible_status(self, obj):
        """Display visibility status"""
        if obj.is_visible():
            return format_html(
                '<span style="color: green; font-weight: bold;">👁 Visible</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">🚫 Hidden</span>'
            )
    is_visible_status.short_description = 'Visible'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by field"""
        if not change: 
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Admin site customization
admin.site.site_header = 'Room Booking Administration'
admin.site.site_title = 'Room Booking Admin'
admin.site.index_title = 'Welcome to Room Booking Administration'