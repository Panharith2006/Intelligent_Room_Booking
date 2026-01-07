from django.urls import include, path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    # User page URLs
    path('about-us/', views.about_us_view, name='about_us'),
    path('service/', views.service_view, name='service'),
    path('booking/', views.booking_view, name='booking'),

    path('create-booking/', views.create_booking, name='create_booking'),
    path('booked/', views.booked_view, name='booked'),
    path('setting/', views.setting_view, name='setting'),
    path('profile-setting/', views.profile_setting_view, name='profile_setting'),
    path('profile/', views.user_profile_view, name='user_profile'),

    # Additional URLs
    path('update-profile/', views.profile_setting_view, name='update_profile'),
    path('booking-detail/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('admin/booking-detail/<int:booking_id>/', views.admin_booking_detail_view, name='admin_booking_detail'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('deactivate-user/', views.deactivate_user_view, name='deactivate_user'),
    
    # Room Booking Calendar (FullCalendar)
    path('room-schedule/', views.room_schedule_view, name='room_schedule'),
    path('api/room-bookings/', views.api_room_bookings, name='api_room_bookings'),

    # AJAX endpoints for frontend integration
    path('ajax/check-availability/', views.check_availability_ajax, name='check_availability_ajax'),
    path('ajax/get-rooms/', views.get_rooms_ajax, name='get_rooms_ajax'),
    path('ajax/room-list/', views.ajax_room_list, name='ajax_room_list'),
    path('ajax/get-buildings/', views.get_buildings_ajax, name='get_buildings_ajax'),
    path('ajax/get-room-details/', views.get_room_details_ajax, name='get_room_details_ajax'),

    # AJAX Endpoints for Admin Functions
    path('admin/ajax/users/<int:user_id>/toggle-status/', views.ajax_toggle_user_status, name='ajax_toggle_user_status'),
    path('admin/ajax/rooms/<int:room_id>/delete/', views.ajax_delete_room, name='ajax_delete_room'),
    path('admin/ajax/rooms/<int:room_id>/toggle-availability/', views.ajax_toggle_room_availability, name='admin_toggle_room_availability'),
    path('admin/ajax/bulk-action/', views.ajax_bulk_action, name='ajax_bulk_action'),

    # Login and Logout URLs
    path('login/', views.custom_login_view, name='login'),
    path('logout/', views.custom_logout_view, name='logout'),

    # Registration URL
    path('register/', views.register, name='register'),

    # Dashboard URLs
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/settings/', views.admin_setting_view, name='admin_settings'),
    path('dashboard/', views.user_dashboard_view, name='dashboard'),
    path('user-dashboard/', views.user_dashboard_view, name='user_dashboard'),
    
    # Admin management URLs (added for dashboard actions)
    path('admin/manage-rooms/', views.manage_rooms_view, name='manage_rooms'),
    path('admin/room-management/', views.admin_room_management_view, name='admin_room_management'),
    path('admin/view-rooms/', views.admin_view_rooms_view, name='admin_view_rooms'),
    path('admin/all-bookings/', views.all_bookings_view, name='all_bookings'),
    path('admin/manage-users/', views.manage_users_view, name='manage_users'),
    path('admin/add-room/', views.add_room_view, name='admin_add_room'),
    path('admin/room/<int:room_id>/', views.admin_room_detail_view, name='admin_room_detail'),
    path('admin/room/<int:room_id>/edit/', views.admin_edit_room_view, name='admin_edit_room'),
    path('admin/ajax/rooms/<int:room_id>/toggle-availability/', views.ajax_toggle_room_availability, name='ajax_toggle_room_availability'),
    path('admin/ajax/rooms/bulk-action/', views.ajax_bulk_action, name='admin_bulk_room_action'),
    path('admin/ajax/rooms/<int:room_id>/delete/', views.ajax_delete_room, name='admin_ajax_delete_room'),

    # google account login
    path('accounts/', include('allauth.urls')),
]
