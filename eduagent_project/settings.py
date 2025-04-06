# eduagent_project/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv # Add this import

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

    # Third-party apps
    'rest_framework',
    'corsheaders',

    # Your apps
    'api.apps.ApiConfig', # Add your 'api' app
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Add CORS middleware (place high)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
    # ... (keep default validators) ...
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

# Allow credentials if needed (e.g., for cookies/sessions with frontend)
# CORS_ALLOW_CREDENTIALS = True
# --- End CORS Settings ---

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