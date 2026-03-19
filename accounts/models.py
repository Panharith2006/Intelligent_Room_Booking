from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, student_id, phone_number, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, student_id=student_id, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, student_id=None, phone_number=None, password=None, **extra_fields):
        """Create and return a superuser. Accepts optional `student_id` and `phone_number`
        so `manage.py createsuperuser` works interactively without requiring extra prompts.
        """
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('booking_approval_status', 'approved')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Provide safe defaults when interactive prompt doesn't supply these fields.
        # `student_id` and `phone_number` are allowed to be blank/null in the model.
        if student_id in (None, ''):
            student_id = None
        if phone_number in (None, ''):
            phone_number = '000-000-0000'

        return self.create_user(email, student_id, phone_number, password, **extra_fields)


class User(AbstractUser):
    username = None

    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pending Review'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
    ]

    email = models.EmailField(
        'Email Address',
        unique=True,
        help_text='Required. Must be a valid email address.'
    )

    student_id = models.CharField(
        'Lecturer ID',
        max_length=20,
        unique=True,
        blank=True,   # Allow blank for admin accounts and Google users
        null=True,    # Allow null temporarily for migration
        help_text='6-20 character lecturer identification.'
    )

    position = models.CharField(
        'Position',
        max_length=100,
        blank=True,
        help_text='Academic position (e.g., Lecturer, Assistant Professor).'
    )

    phone_number = models.CharField(
        'Phone Number',
        max_length=20, 
        help_text='Format: +999999999 or 999-999-9999',
        blank=True
    )

    is_admin = models.BooleanField(
        'Admin status',
        default=False,
        help_text='Designates administrative privileges (different from staff status).'
    )

    faculty = models.CharField(
        'Faculty',
        max_length=100,  # Increased length for custom faculty names
        blank=True,
        help_text='Faculty or school name.'
    )

    department = models.CharField(
        'Department',
        max_length=100,  # Increased for longer department names
        blank=True
    )

    profile_picture = models.ImageField(
        'Profile Picture',
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        default=None,
        help_text='Upload a profile image.'
    )

    is_staff = models.BooleanField(
        'Staff status',
        default=False,
        help_text='Designates whether the user can log into this admin site.'
    )

    booking_approval_status = models.CharField(
        'Booking Approval Status',
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
        help_text='Controls whether lecturer can make room bookings.'
    )

    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Updated At', auto_now=True)

    late_cancellation_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of late cancellations (less than policy notice period).'
    )

    cancellation_warning_count = models.PositiveIntegerField(
        default=0,
        help_text='Total warning notices issued for late cancellations.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        db_table = 'accounts_user'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def get_student_display_id(self):
        """Return lecturer ID"""
        if self.student_id:
            return f"{self.student_id}"
        return ""

    def get_lecturer_display_id(self):
        """Return lecturer ID for templates that use the newer terminology."""
        return self.get_student_display_id()
    
    def get_phone_display(self):
        """Return phone number or default"""
        return self.phone_number or "000-000-0000"

    def is_google_user(self):
        """Check if this user signed up via Google OAuth"""
        return hasattr(self, 'socialaccount_set') and self.socialaccount_set.filter(provider='google').exists()

    def is_profile_complete(self):
        """Check if lecturer profile is complete for booking approval."""
        required_fields = [self.first_name, self.last_name, self.email]
        profile_fields = [
            self.phone_number,
            self.faculty,
            self.department,
            self.position,
            self.profile_picture,
        ]

        # All required fields must be filled
        if not all(required_fields):
            return False

        # For Google users, student_id starting with GOOGLE is acceptable
        if self.is_google_user() and self.student_id and self.student_id.startswith('GOOGLE'):
            return all(profile_fields)
        else:
            # For regular users, lecturer ID should not be auto-generated
            if not self.student_id or self.student_id.startswith(('USR', 'GOOGLE')):
                return False
            return all(profile_fields)

    def get_profile_completion_percentage(self):
        """Get profile completion percentage"""
        total_fields = 9  # first_name, last_name, email, lecturer_id, phone, faculty, department, position, photo
        filled_fields = 0

        # Required fields
        if self.first_name:
            filled_fields += 1
        if self.last_name:
            filled_fields += 1
        if self.email:
            filled_fields += 1

        # Optional but important fields
        if self.student_id and not self.student_id.startswith(('USR', 'GOOGLE')):
            filled_fields += 1
        elif self.student_id and self.student_id.startswith('GOOGLE') and self.is_google_user():
            filled_fields += 0.5

        if self.phone_number:
            filled_fields += 1
        if self.faculty:
            filled_fields += 1
        if self.department:
            filled_fields += 1

        if self.position:
            filled_fields += 1

        if self.profile_picture:
            filled_fields += 1

        return int((filled_fields / total_fields) * 100)

    def is_regular_user(self):
        """Check if user is a regular user (not admin)"""
        return not self.is_admin and not self.is_staff

    def is_admin_user(self):
        """Check if user is admin"""
        return self.is_admin or self.is_superuser

    def can_book_rooms(self):
        """Return True if lecturer account is approved for booking."""
        return self.booking_approval_status == self.APPROVAL_APPROVED
