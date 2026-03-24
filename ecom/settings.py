from decouple import config, Csv
"""
Django settings for ecom project - Enhanced for World-Class eccommence
"""

from pathlib import Path
import os
from datetime import timedelta
from decimal import Decimal


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ============= SECURITY SETTINGS =============

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-td*y)-^=vivnwbr_!=+fyy88!%^=3eetw#%13sd92e6r43w$in')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,.localhost').split(',')

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ============= APPLICATION DEFINITION =============

SHARED_APPS = [
    'django_tenants',  # MUST be first
    'tenants',         # Tenant management
    
    # Django core (public schema)
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    
    # Users (authentication in public, profiles in tenant)
    'users',
]

TENANT_APPS = [
    # Django apps for each tenant
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # ← ADD THIS LINE

    
    # Your business logic (isolated per tenant)
    'eccommence',  # Products, Vendors, Customers
    'payment',     # Orders, Transactions
    'cart', 
    'store_admin',          
        # Order management (if separate)
    
    # Future apps
    # 'analytics',
    # 'notifications',
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# ============= MIDDLEWARE =============

# Middleware
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'ecom.middleware.ForceTenantURLConfMiddleware',  # ← ADD THIS LINE

    'ecom.middleware.DebugTenantMiddleware',  # Our debug middleware

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ecom.middleware.TenantSubscriptionMiddleware',  # ADD THIS
    'ecom.middleware.TenantLimitMiddleware',  # ADD THIS
]

ROOT_URLCONF = 'ecom.urls'


# ============= TEMPLATES =============

# Context Processors
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                
                # Custom context processors
                'cart.context_processors.cart',
                'eccommence.context_processors.all_categories',
                'ecom.context_processors.site_settings',  # ADD THIS
                'ecom.context_processors.tenant_context',  # ADD THIS
            ],
        },
    },
]

WSGI_APPLICATION = 'ecom.wsgi.application'


# ============= DATABASE =============

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME', default='ecommerce_db'),
        'USER': config('DB_USER', default='ecommerce_user'),
        'PASSWORD': config('DB_PASSWORD', default='@Developer22'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)


# ============= MULTI-TENANCY CONFIGURATION =============

TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_NAME = 'public'
PUBLIC_SCHEMA_URLCONF = 'ecom.public_urls'
TENANT_URLCONF = 'ecom.tenant_urls'


# ============= PASSWORD VALIDATION =============

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ============= AUTHENTICATION =============

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/users/login/'

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'ecom_sessionid'


# ============= INTERNATIONALIZATION =============

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'  # Changed to Uganda timezone
USE_I18N = True
USE_TZ = True


# ============= STATIC & MEDIA FILES =============

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# For production (use with WhiteNoise or similar)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'


# ============= EMAIL CONFIGURATION =============

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'mwesigedeveloper@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'pcsr mpvj xczg ubuj')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Homies <mwesigedeveloper@gmail.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email settings
EMAIL_TIMEOUT = 10
EMAIL_USE_LOCALTIME = False

# Password reset
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours
PASSWORD_RESET_SUBJECT = 'Homies - Reset Your Password'


# ============= SITE CONFIGURATION =============

SITE_ID = 1
SITE_NAME = 'Homies'
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:8000')


# ============= CART CONFIGURATION =============

CART_SESSION_ID = 'cart'


# ============= PAYMENT GATEWAY CONFIGURATION =============

# Flutterwave
FLUTTERWAVE_PUBLIC_KEY = os.environ.get('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_SECRET_KEY = os.environ.get('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_ENCRYPTION_KEY = os.environ.get('FLUTTERWAVE_ENCRYPTION_KEY', '')
FLUTTERWAVE_WEBHOOK_SECRET = os.environ.get('FLUTTERWAVE_WEBHOOK_SECRET', '')

# Paystack
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
PAYSTACK_WEBHOOK_SECRET = os.environ.get('PAYSTACK_WEBHOOK_SECRET', '')

# Stripe
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# M-Pesa (Safaricom)
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_INITIATOR_NAME = os.environ.get('MPESA_INITIATOR_NAME', '')
MPESA_SECURITY_CREDENTIAL = os.environ.get('MPESA_SECURITY_CREDENTIAL', '')

# Payment settings
PAYMENT_CURRENCY = 'UGX'
PAYMENT_CURRENCY_SYMBOL = 'UGX'


# ============= FILE UPLOAD SETTINGS =============

# Max upload size: 5MB for images, 10MB for documents
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx']


# ============= LOGGING =============

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'payment': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# ============= CACHING (Optional but Recommended) =============

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ecom',
        'TIMEOUT': 300,  # 5 minutes default
    }
} if os.environ.get('USE_REDIS', 'False') == 'True' else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# ============= CELERY CONFIGURATION (For Background Tasks) =============

if os.environ.get('USE_CELERY', 'False') == 'True':
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes


# ============= REST FRAMEWORK (If using API) =============

# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': [
#         'rest_framework.authentication.SessionAuthentication',
#         'rest_framework.authentication.TokenAuthentication',
#     ],
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticatedOrReadOnly',
#     ],
#     'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
#     'PAGE_SIZE': 20,
#     'DEFAULT_FILTER_BACKENDS': [
#         'django_filters.rest_framework.DjangoFilterBackend',
#         'rest_framework.filters.SearchFilter',
#         'rest_framework.filters.OrderingFilter',
#     ],
# }


# ============= CRISPY FORMS (If using) =============

# CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
# CRISPY_TEMPLATE_PACK = "bootstrap5"


# ============= CORS HEADERS (If using API) =============

# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",  # React/Vue frontend
#     "http://127.0.0.1:3000",
# ]
# CORS_ALLOW_CREDENTIALS = True


# ============= BUSINESS SETTINGS =============

# Tax rate (18% VAT for Uganda)('0.18')
TAX_RATE = Decimal('0.0')

# Default shipping cost (in UGX)
DEFAULT_SHIPPING_COST = Decimal('5000.00')

# Platform commission rate (percentage)
PLATFORM_COMMISSION_RATE = Decimal('10.00')

# Low stock threshold
LOW_STOCK_THRESHOLD = 10

# Order auto-cancel after (days)
ORDER_AUTO_CANCEL_DAYS = 7

# Order auto-complete after delivery (days)
ORDER_AUTO_COMPLETE_DAYS = 7


# ============= ADMIN CUSTOMIZATION =============

ADMIN_SITE_HEADER = 'Homies Admin'
ADMIN_SITE_TITLE = 'Homies Admin Portal'
ADMIN_INDEX_TITLE = 'Welcome to Homies Admin'


# ============= MISCELLANEOUS =============

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Message tags for Bootstrap
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# Pagination
PAGINATE_BY = 20

# Phone number format
PHONE_NUMBER_REGION = 'UG'  # Uganda


# ============= DEVELOPMENT SETTINGS =============

if DEBUG:
    # Show emails in console during development
    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
    # Django Debug Toolbar (optional)
    # INSTALLED_APPS += ['debug_toolbar']
    # MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    # INTERNAL_IPS = ['127.0.0.1']
    
    # Disable HTTPS redirects in development
    SECURE_SSL_REDIRECT = False

    # Force correct domain in password reset emails
if DEBUG:
    SITE_ID = 1