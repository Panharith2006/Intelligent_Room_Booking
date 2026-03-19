from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from PIL import Image, UnidentifiedImageError

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form that matches your HTML frontend"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name',
            'id': 'firstName'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name',
            'id': 'lastName'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'id': 'email'
        })
    )
    
    student_id = forms.CharField(
        max_length=20,
        required=False,  # Make optional for flexibility
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Lecturer ID (optional)',
            'id': 'studentId'
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number (optional)',
            'id': 'phoneNumber'
        })
    )
    
    faculty = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Faculty (optional)',
            'id': 'faculty'
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department (optional)',
            'id': 'department'
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        })
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'id': 'confirmPassword'
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'student_id', 'phone_number', 'faculty', 'department')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if student_id and User.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("This lecturer ID is already registered.")
        return student_id
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.student_id = self.cleaned_data.get('student_id', '')  # Leave blank if not provided
        user.phone_number = self.cleaned_data.get('phone_number') or "000-000-0000"
        user.faculty = self.cleaned_data.get('faculty', '')
        user.department = self.cleaned_data.get('department', '')
        
        if commit:
            user.save()
        return user

class CustomLoginForm(forms.Form):
    """Custom login form that matches your HTML frontend"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'id': 'username',  
            'name': 'username' 
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        })
    )
# this code is for the password change form
class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with your styling"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password',
            'id': 'currentPassword'
        })
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'id': 'newPassword'
        })
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'id': 'confirmPassword'
        })
    )

class UserUpdateForm(forms.ModelForm):
    """Form for updating user profile - Works for both regular users and Google OAuth users"""
    
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'id': 'profilePicture',
            'accept': 'image/jpeg,image/png,image/webp',
            'style': 'display:none;'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'student_id', 'phone_number', 'faculty', 'department', 'email', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
                'id': 'firstName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
                'id': 'lastName'
            }),
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lecturer ID',
                'id': 'studentId'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address',
                'id': 'id_email',
                'readonly': 'readonly',
                'style': 'background:#f5f5f5; cursor:not-allowed;',
                'title': 'Email cannot be changed for security reasons'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number (e.g., +855-12-345-678)',
                'id': 'phoneNumber'
            }),
            'faculty': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Faculty',
                'id': 'faculty'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Department',
                'id': 'department'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields more user-friendly for Google users
        if self.instance and hasattr(self.instance, 'socialaccount_set') and self.instance.socialaccount_set.exists():
            # This is a Google user - customize form
            self.fields['student_id'].help_text = 'Optional - You can add your lecturer ID or leave blank'
            self.fields['phone_number'].help_text = 'Optional - Add your phone number for better communication'
            self.fields['faculty'].help_text = 'Optional - Select your faculty if applicable'
            self.fields['department'].help_text = 'Optional - Enter your department or program'
            
            # Make student_id not required for Google users if it's auto-generated
            if self.instance.student_id and self.instance.student_id.startswith('GOOGLE'):
                self.fields['student_id'].required = False
                self.fields['student_id'].widget.attrs['placeholder'] = 'Lecturer ID (optional for Google users)'
        
        

    def clean_email(self):
        """Email cannot be changed for security reasons"""
        return self.instance.email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        
        # Handle empty or None student_id
        if not student_id:
            # If no student_id provided, keep the existing one 
            if self.instance.student_id:
                return self.instance.student_id
            else:
                # Leave empty so user can add their real lecturer ID later
                return ""

            # Normalize lecturer ID - remove spaces and convert to uppercase
        student_id = student_id.replace(' ', '').upper()
        
        # Only check for duplicates if changed and not empty
        if student_id != self.instance.student_id:
            qs = User.objects.filter(student_id=student_id).exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This lecturer ID is already registered.")
                
        # Validate format only if not auto-generated ID
        if not student_id.startswith(('GOOGLE', 'USR')):
            import re
            if not re.match(r'^[A-Z0-9]{6,20}$', student_id):
                raise forms.ValidationError("Lecturer ID must be 6-20 characters (letters and numbers only)")
        
        return student_id

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            phone = phone.strip()
            # More flexible phone validation
            cleaned_phone = ''.join(filter(str.isdigit, phone.replace('+', '')))
            if len(cleaned_phone) < 9:
                raise forms.ValidationError("Phone number must be at least 9 digits long.")
            if len(cleaned_phone) > 15:
                raise forms.ValidationError("Phone number is too long.")
        return phone

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            return first_name.strip().title()  # Capitalize properly
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            return last_name.strip().title()  # Capitalize properly
        return last_name

    def clean_faculty(self):
        faculty = self.cleaned_data.get('faculty')
        if faculty:
            return faculty.strip()  # Preserve user input as-is
        return faculty or ''  # Return empty string instead of None

    def clean_department(self):
        department = self.cleaned_data.get('department')
        if department:
            return department.strip()  # Preserve user input as-is
        return department or ''  # Return empty string instead of None

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if not picture:
            return picture

        allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
        content_type = getattr(picture, 'content_type', None)
        if content_type and content_type not in allowed_types:
            raise forms.ValidationError('Profile photo must be JPG, PNG, or WEBP format.')

        max_size_bytes = 2 * 1024 * 1024  # 2MB
        if picture.size > max_size_bytes:
            raise forms.ValidationError('Profile photo must be 2MB or smaller.')

        try:
            image = Image.open(picture)
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError('Uploaded file is not a valid image.')
        finally:
            try:
                picture.seek(0)
            except Exception:
                pass

        return picture

    def save(self, commit=True):
        user = super().save(commit=False)
        clear_requested = str(self.data.get('clear_profile_picture', '0')).lower() in {'1', 'true', 'on', 'yes'}
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Updating profile for user: {user.email}")
        
        # Update all fields from cleaned data
        for field in ['first_name', 'last_name', 'student_id', 'phone_number', 'faculty', 'department']:
            value = self.cleaned_data.get(field)
            old_value = getattr(user, field, None)
            if value is not None:  # Allow empty strings but not None
                setattr(user, field, value)
                if old_value != value:
                    logger.info(f"Changed {field}: '{old_value}' -> '{value}'")
            else:
                # Ensure empty strings for faculty and department instead of None
                if field in ['faculty', 'department']:
                    setattr(user, field, '')
                    logger.info(f"Set {field} to empty string")

        
        # Email is read-only, do not update
        # Handle profile picture
        profile_picture = self.cleaned_data.get('profile_picture')
        if clear_requested:
            user.profile_picture = None
        elif profile_picture:
            logger.info(f"Updating profile picture: {profile_picture}")
            user.profile_picture = profile_picture
        elif self.fields['profile_picture'].required is False and not profile_picture and self.instance.profile_picture:
            # If no new image uploaded, keep the old one
            user.profile_picture = self.instance.profile_picture
            
        if commit:
            try:
                user.save()
                logger.info(f"Successfully saved user: {user.email}")
            except Exception as e:
                logger.error(f"Failed to save user {user.email}: {str(e)}")
                raise
        return user