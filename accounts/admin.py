from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'student_id', 'faculty', 'department', 'phone_number', 'is_superuser', 'is_active')
    list_filter = ('is_superuser', 'is_active', 'faculty')
    
    # Disable bulk actions but keep individual actions
    actions = []  
    
    fieldsets = (
    (None, {'fields': ('email', 'password')}),
    ('Personal Info', {'fields': ('first_name', 'last_name', 'student_id', 'phone_number', 'faculty', 'department')}),
    ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'student_id', 'phone_number', 'faculty', 'department', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'student_id', 'phone_number', 'faculty', 'department')
    ordering = ('-created_at',)

admin.site.register(User, CustomUserAdmin)