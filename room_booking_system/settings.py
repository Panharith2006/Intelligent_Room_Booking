from pathlib import Path
from decouple import config

# Optional PyMySQL shim: only install if the package is available.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    import warnings
    warnings.warn('pymysql not installed; MySQLdb shim not applied. Install pymysql if using MySQL.', UserWarning)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts.apps.AccountsConfig',  # Your accounts app
    'booking',  # Your booking app
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'corsheaders', # for CORS handlling with chatbot
    # Chatbot app temporarily disabled to avoid import errors when the package
    # is not present in the environment. Re-enable when the `chatbot` package
    # is available and installed.
    # 'chatbot.apps.ChatbotConfig',  # AI Chatbot with Semantic Kernel (Django-integrated)
    
]

# Enable chatbot app only if importable to avoid startup errors when it's not installed
try:
    import importlib
    if importlib.util.find_spec('chatbot') is not None:
        INSTALLED_APPS.append('chatbot.apps.ChatbotConfig')
except Exception:
    pass

SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Development CORS settings - allow frontend to call chat endpoints
CORS_ALLOW_ALL_ORIGINS = True

# Allow configuring CSRF trusted origins via environment (comma-separated)
# Example in .env: CSRF_TRUSTED_ORIGINS=https://abcd1234.ngrok.io
_csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf_origins.split(',') if x.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

ROOT_URLCONF = 'room_booking_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Use templates/ directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'booking.context_processors.room_types',  # Add booking context
                'booking.context_processors.active_announcements',  # Add announcements globally
            ],
        },
    },
]

WSGI_APPLICATION = 'room_booking_system.wsgi.application'

# Database configuration - supports both SQLite and MySQL
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE:
    # SQLite configuration for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # MySQL database configuration (from .env)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='room_booking'),
            'USER': config('DB_USER', default='Rith'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3307'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Phnom_Penh'  # Cambodia timezone
USE_I18N = True
USE_TZ = True


# Deepseek (hosted LLM) configuration - set these in your environment
from decouple import config as _config
DEEPSEEK_API_KEY = _config('DEEPSEEK_API_KEY', default='')
DEEPSEEK_BASE_URL = _config('DEEPSEEK_BASE_URL', default='https://api.deepseek.com/v1')

# Groq (free, fast LLM) configuration - FREE TIER AVAILABLE
GROQ_API_KEY = _config('GROQ_API_KEY', default='')
GROQ_MODEL = _config('GROQ_MODEL', default='llama-3.1-8b-instant')

# Hugging Face (free alternative LLM) configuration - DEPRECATED (API shut down Dec 2025)
HF_API_KEY = _config('HF_API_KEY', default='')
HF_MODEL = _config('HF_MODEL', default='microsoft/DialoGPT-medium')

# Static and Media files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'templates' / 'SignIn-RegisterPage',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default PK field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model (FIXED - only one declaration)
AUTH_USER_MODEL = 'accounts.User'


# Auth redirect settings for Allauth
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/setting/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'


# Email backend (from .env, fallback to console for dev)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default=None)
EMAIL_PORT = config('EMAIL_PORT', default=None, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=None)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Room Booking System <noreply@rupp.edu.kh>')
EMAIL_SUBJECT_PREFIX = config('EMAIL_SUBJECT_PREFIX', default='[Room Booking] ')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@rupp.edu.kh')



AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Google provider settings for django-allauth
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar',  # Full calendar access
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',  # Changed to offline to get refresh tokens
            'prompt': 'consent',  # Force consent screen to get refresh token
        },
        'OAUTH_PKCE_ENABLED': True,
        # Allow any Google account (no domain restrictions)
        'VERIFIED_EMAIL': True,
        'VERSION': 'v2',  # Use Google OAuth v2
    }
}

# AllAuth settings (updated for latest version)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Change to 'mandatory' for production
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',  # 5 attempts per 5 minutes
}

# Social account settings - Open for all Google accounts
SOCIALACCOUNT_AUTO_SIGNUP = True  # Automatically create accounts for new Google users
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Skip email verification for Google accounts
SOCIALACCOUNT_QUERY_EMAIL = True  # Always ask for email permission
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow login via GET request
SOCIALACCOUNT_STORE_TOKENS = True  # Store access tokens for Google Calendar integration
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'

# Allow any email domain for Google OAuth (no restrictions)
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # Auto-connect to existing accounts with same email

# Additional settings to help with redirect URI
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'  # Use http for local development

# Custom adapter for handling Google signup
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'

# ✅ PUBLIC ACCESS SETTINGS - Allow anyone to sign in with Google
# These settings ensure your app works for ALL Google users once OAuth is published
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # Auto-connect accounts with same email
ACCOUNT_EMAIL_VERIFICATION = 'none'  # No email verification required for public access
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # No email verification for Google users

# ✅ Production-ready settings for Google OAuth
# When you deploy, these settings allow unlimited public access
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow login via GET requests
ACCOUNT_LOGOUT_ON_GET = True  # Allow logout via GET requests


# ===================================
# Telegram Bot Settings
# ===================================
# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default=None)

# List of admin Telegram chat IDs (comma-separated in .env)
TELEGRAM_ADMIN_CHAT_IDS = [
    chat_id.strip() for chat_id in 
    config('TELEGRAM_ADMIN_CHAT_IDS', default='').split(',')
    if chat_id.strip()
]

