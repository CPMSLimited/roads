# roads/settings/production.py
from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "cpmsferma.com",
    "www.cpmsferma.com",
    "165.232.36.205",
    "localhost",
    "127.0.0.1",
]

# Behind a reverse proxy (e.g., Nginx)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Enforce HTTPS/HSTS in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Static files via WhiteNoise in production
INSTALLED_APPS = INSTALLED_APPS + []
MIDDLEWARE = MIDDLEWARE.copy()
# insert WhiteNoise after SecurityMiddleware if not already there in base
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# CORS/CSRF for your domains + optional dev origins if you test from laptop against prod
CORS_ALLOWED_ORIGINS = [
    "https://cpmsferma.com",
    "https://www.cpmsferma.com",
    # Uncomment during testing if you call prod API from local frontend:
    # "http://localhost:5173",
    # "http://127.0.0.1:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "https://cpmsferma.com",
    "https://www.cpmsferma.com",
]
