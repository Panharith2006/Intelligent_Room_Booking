from django.urls import include, path
from . import views, admin_views, api_views

app_name = 'booking'

urlpatterns = [
    # ============================================
    # AI Chatbot API Endpoints (for Semantic Kernel)
    # ============================================
    path('api/rooms/', api_views.api_list_rooms, name='api_list_rooms'),
    path('api/rooms/availability/', api_views.api_check_availability, name='api_check_availability'),
    path('api/rooms/search/', api_views.api_search_rooms, name='api_search_rooms'),
    path('api/bookings/', api_views.api_list_user_bookings, name='api_list_user_bookings'),
    path('api/bookings/create/', api_views.api_create_booking, name='api_create_booking'),
    path('api/bookings/cancel/', api_views.api_cancel_booking, name='api_cancel_booking'),
    path('api/rules/', api_views.api_get_booking_rules, name='api_get_booking_rules'),
    
    # Room management URLs
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),
    path('rooms/create/', views.room_create, name='room_create'),
    path('rooms/<int:room_id>/edit/', views.room_edit, name='room_edit'),
    path('rooms/<int:room_id>/toggle-status/', views.room_toggle_status, name='room_toggle_status'),
    path('rooms/<int:room_id>/delete/', views.room_delete, name='room_delete'),

    # Admin URLs - using admin_views
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/rooms/', admin_views.admin_room_list, name='admin_room_list'),
    path('admin/rooms/create/', admin_views.admin_room_create, name='admin_room_create'),
    path('admin/rooms/<int:room_id>/edit/', admin_views.admin_room_edit, name='admin_room_edit'),
    path('admin/rooms/<int:room_id>/delete/', admin_views.admin_room_delete, name='admin_room_delete'),
    path('admin/rooms/<int:room_id>/toggle-availability/', admin_views.admin_room_toggle_availability, name='admin_room_toggle_availability'),
    path('admin/rooms/bulk-action/', admin_views.admin_room_bulk_action, name='admin_room_bulk_action'),
    
    # Admin booking management
    path('admin/bookings/', admin_views.admin_booking_list, name='admin_booking_list'),
    path('admin/bookings/create/', admin_views.admin_booking_create, name='admin_booking_create'),
    path('admin/bookings/<int:booking_id>/edit/', admin_views.admin_booking_edit, name='admin_booking_edit'),
    path('admin/bookings/<int:booking_id>/delete/', admin_views.admin_booking_delete, name='admin_booking_delete'),
    path('admin/bookings/<int:booking_id>/update-status/', admin_views.admin_booking_update_status, name='admin_booking_update_status'),
    
    # Admin system configuration
    path('admin/booking-rules/', admin_views.admin_booking_rules, name='admin_booking_rules'),
    path('admin/announcements/', admin_views.admin_announcements, name='admin_announcements'),
    path('admin/announcements/create/', admin_views.admin_announcement_create, name='admin_announcement_create'),
    path('admin/announcements/<int:announcement_id>/edit/', admin_views.admin_announcement_edit, name='admin_announcement_edit'),
    path('admin/announcements/<int:announcement_id>/delete/', admin_views.admin_announcement_delete, name='admin_announcement_delete'),
    path('admin/announcements/<int:announcement_id>/toggle-active/', admin_views.admin_announcement_toggle_active, name='admin_announcement_toggle_active'),
    
    # Admin user management
    path('admin/users/', admin_views.admin_user_management, name='admin_user_management'),
    path('admin/users/<int:user_id>/toggle-status/', admin_views.admin_user_toggle_status, name='admin_user_toggle_status'),
    
    # Admin AJAX endpoints
    path('admin/api/room-availability/', admin_views.admin_get_room_availability, name='admin_get_room_availability'),
    path('admin/api/booking-stats/', admin_views.admin_booking_stats, name='admin_booking_stats'),
    
    # Admin schedule
    path('admin/schedule/', admin_views.admin_schedule_view, name='admin_schedule'),
    path('admin/schedule/events/', admin_views.admin_schedule_events, name='admin_schedule_events'),
    path('admin/bookings/<int:booking_id>/quick-edit/', admin_views.admin_booking_quick_edit, name='admin_booking_quick_edit'),

    # User dashboard
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    
    # User booking URLs
    path('create/', views.create_booking, name='create_booking'),
    path('my-bookings/', views.user_bookings, name='user_bookings'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('bookings/<int:booking_id>/modify/', views.modify_booking, name='modify_booking'),
    path('quick-book/<int:room_id>/', views.quick_book, name='quick_book'),
    path('calendar/', views.booking_calendar, name='booking_calendar'),

    # AJAX endpoints
    path('api/check-availability/', views.check_room_availability, name='check_room_availability'),
    path('api/rooms-availability/', views.rooms_api_availability, name='rooms_api_availability'),
    path('api/check-room-availability-ajax/', views.check_room_availability_ajax, name='check_room_availability_ajax'),
    path('check-availability/', views.check_availability, name='check_availability'),

    # Booking schedule URLs
    path('schedule/', views.booking_schedule_by_day, name='booking_schedule_by_day'),
    path('schedule/room/<int:room_id>/', views.booking_schedule_by_room, name='booking_schedule_by_room'),
]