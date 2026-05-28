import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import logging

# Load environment variables
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key-for-local-dev-only')
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if os.environ.get('RENDER'):
    ALLOWED_HOSTS.append('.onrender.com')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',

    # Local apps
    'core',
    'wallets',
    'contracts',
    'transactions',
    'reports',
    'ai',
    'solana',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
import sys
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=not DEBUG
        )
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
WHITENOISE_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')

if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ] + (['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# Etherscan Config
ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')

# Gemini Config
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Ethereum RPC Config (Alchemy / Infura / QuickNode)
ETH_RPC_URL = os.environ.get('ETH_RPC_URL', '')

# --- PRODUCTION SECURITY ---
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    X_FRAME_OPTIONS = 'SAMEORIGIN'

# --- STRUCTURED LOGGING ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'ai': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'wallets': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'contracts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'transactions': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'reports': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'solana': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# --- STARTUP VALIDATION ---
_startup_logger = logging.getLogger('core')

if not ETHERSCAN_API_KEY:
    _startup_logger.warning('ETHERSCAN_API_KEY is not set. Ethereum analysis endpoints will fail.')

if not ETH_RPC_URL:
    _startup_logger.warning('ETH_RPC_URL is not set. On-chain address detection (wallet vs contract) will be unavailable.')
else:
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL, request_kwargs={'timeout': 10}))
        if w3.is_connected():
            _startup_logger.info('Connected to Ethereum RPC successfully')
        else:
            _startup_logger.warning('Failed to connect to Ethereum RPC. Check ETH_RPC_URL connectivity.')
    except Exception as e:
        _startup_logger.warning('Error connecting to Ethereum RPC: %s', e)

_gemini_key = os.environ.get('GEMINI_API_KEY', '')
if not _gemini_key or _gemini_key.startswith('your_'):
    _startup_logger.warning('GEMINI_API_KEY is missing or placeholder. AI reasoning will return fallback responses.')

if 'django-insecure-' in SECRET_KEY:
    _startup_logger.warning('SECRET_KEY uses insecure default. Set a strong SECRET_KEY for production.')
