# eduagent_project/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv # Add this import
from datetime import timedelta # Import timedelta for token settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Add this section to load .env ---
# Assuming your .env file is in the root 'eduagent_backend' directory
dotenv_path = BASE_DIR.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)
# --- End of .env loading section ---

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here' # Keep the generated key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # Keep True for development

ALLOWED_HOSTS = [] # Keep empty for now, configure for deployment later


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party apps
    'rest_framework',
    'corsheaders',

    'rest_framework_simplejwt',
    'dj_rest_auth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'dj_rest_auth.registration',

    # Your apps
    'api.apps.ApiConfig', # Add your 'api' app
    'authentication.apps.AuthenticationConfig',
]

# <<< AUTH: Required by django.contrib.sites
SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Add CORS middleware (place high)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'eduagent_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eduagent_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3', # Simple database for development
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Django REST Framework Settings ---
REST_FRAMEWORK = {
    # Configure default permission classes if needed later
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     'rest_framework.permissions.AllowAny', # Or IsAuthenticated, etc.
    # ],
    # Configure default authentication classes if needed later
    # 'DEFAULT_AUTHENTICATION_CLASSES': [
    #     # e.g., 'rest_framework.authentication.TokenAuthentication',
    # ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
     'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # Add BrowsableAPIRenderer only if DEBUG is True for easy testing
        'rest_framework.renderers.BrowsableAPIRenderer' if DEBUG else '',
    ],
    
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser' # Needed for file uploads
    ]
}
# --- End DRF Settings ---


# --- CORS Settings ---
# Define allowed origins for your frontend (adjust for production)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Example React default
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Example Vite default
    "http://127.0.0.1:5173",
]
# Or allow all origins for easy development (less secure)
# CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'authorization', # <<< Ensure this is present
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Allow credentials if needed (e.g., for cookies/sessions with frontend)
# CORS_ALLOW_CREDENTIALS = True
# --- End CORS Settings ---

# --- Allauth Settings ---
# <<< AUTH: Basic Allauth configuration
ACCOUNT_EMAIL_VERIFICATION = 'none' # Options: 'mandatory', 'optional', 'none'. Use 'none' for testing.
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_SIGNUP_FIELDS = {'username', 'email', 'password'}
# --- End Allauth Settings ---

# --- dj-rest-auth Settings ---
# <<< AUTH: Configure dj-rest-auth to use JWT
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_HTTPONLY': False,  # Set to False to allow frontend JS to access the token
    # <<< AUTH: Point USER_DETAILS_SERIALIZER to the one in your new 'authentication' app
    'USER_DETAILS_SERIALIZER': 'authentication.serializers.CurrentUserSerializer',
    'LOGIN_SERIALIZER': 'dj_rest_auth.serializers.LoginSerializer', # Default is usually fine
    'REGISTER_SERIALIZER': 'dj_rest_auth.registration.serializers.RegisterSerializer', # Default is usually fine
    'TOKEN_MODEL': None, # Disable DRF's default Token model since we use JWT
    # Add other dj-rest-auth settings if needed (e.g., password reset serializers)
}
# --- End dj-rest-auth Settings ---

# --- Simple JWT Settings ---
# <<< AUTH: Configure JWT token behavior
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # e.g., 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),    # e.g., 1 week
    'ROTATE_REFRESH_TOKENS': True, # Issue new refresh token when old one is used
    'BLACKLIST_AFTER_ROTATION': True, # Blacklist old refresh token after rotation
    'UPDATE_LAST_LOGIN': True, # Update user's last_login field on token refresh

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Use the project's SECRET_KEY
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',), # Default: Bearer <token>
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    # Settings for sliding tokens (optional alternative to refresh tokens)
    # 'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    # 'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    # 'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}
# --- End Simple JWT Settings ---


# --- Custom Application Settings ---
# Base directory for storing ChromaDB vector stores
CHROMA_DB_ROOT_DIR = BASE_DIR / 'chroma_db'

# Ensure the root directory exists (create if it doesn't)
os.makedirs(CHROMA_DB_ROOT_DIR, exist_ok=True)

# Embedding model configuration (used by utils.py)
EMBEDDING_MODEL = 'nomic-embed-text'

# Retriever configuration (used by utils.py)
RETRIEVER_SEARCH_TYPE = 'mmr'
RETRIEVER_K = 3

# Maximum upload size for knowledge base files in Megabytes (used by views.py)
MAX_UPLOAD_SIZE_MB = 200 # <-- Increased limit (adjust value as needed)

# Optional: Setting to control if KB directory should be cleared on upload
# CLEAR_KB_ON_UPLOAD = False # Set to True if you always want a fresh KB