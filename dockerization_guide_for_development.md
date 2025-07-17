# Complete Guide to Dockerizing EventHub Django Application for Development

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Understanding the Current Application](#understanding-the-current-application)
3. [Docker Configuration Files](#docker-configuration-files)
4. [Environment Configuration](#environment-configuration)
5. [Application Configuration Updates](#application-configuration-updates)
6. [Step-by-Step Implementation](#step-by-step-implementation)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Prerequisites

Before starting, ensure you have the following installed:

- **Docker Desktop** (latest version)
- **Docker Compose** (comes with Docker Desktop)
- **Git** (for version control)
- **Code editor** (VS Code, PyCharm, etc.)
- **Basic understanding of**:
  - Django framework
  - Command line interface
  - Environment variables
  - Database concepts

### Verify Installation
```shell script
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Verify Docker is running
docker ps
```


---

## Understanding the Current Application

### Application Structure Analysis
Your EventHub application currently has:
- **Django 5.2.3** web framework
- **Django REST Framework** for API endpoints
- **Custom authentication** system
- **Media file handling** for event images
- **SQLite database** (we'll migrate to PostgreSQL)
- **Environment variable support** with python-dotenv

### Key Dependencies
From `requirements.txt`:
- `Django==5.2.3`
- `djangorestframework==3.16.0`
- `psycopg2-binary==2.9.10` (PostgreSQL adapter)
- `Pillow==11.2.1` (image processing)
- `python-dotenv==1.1.0` (environment variables)

---

## Docker Configuration Files

### 1. Create Development Dockerfile

Create a new file called `Dockerfile.dev` in your project root:

```dockerfile
# Use Python 3.12 to match your current environment
FROM python:3.12-slim

# Set metadata
LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="EventHub Django Application - Development"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # PostgreSQL client and development headers
    postgresql-client \
    libpq-dev \
    # Build tools for Python packages
    build-essential \
    # Git for version control (useful in development)
    git \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first (Docker layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create media directory for file uploads
RUN mkdir -p /app/media && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command for development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```


### 2. Create Docker Compose for Development

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  # Database service
  db:
    image: postgres:15-alpine
    container_name: eventhub_db_dev
    environment:
      POSTGRES_DB: ${DB_NAME:-eventhub_dev}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_HOST_AUTH_METHOD: trust
    volumes:
      # Persistent database storage
      - postgres_data:/var/lib/postgresql/data
      # Custom initialization scripts (optional)
      - ./docker/init-db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - eventhub_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -d ${DB_NAME:-eventhub_dev}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis service for caching and sessions (optional but recommended)
  redis:
    image: redis:7-alpine
    container_name: eventhub_redis_dev
    ports:
      - "6379:6379"
    networks:
      - eventhub_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Web application service
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: eventhub_web_dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      # Mount source code for live reloading
      - .:/app
      # Persistent media storage
      - media_files:/app/media
      # Cache Python packages (optional optimization)
      - pip_cache:/root/.cache/pip
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DEBUG=True
      - DJANGO_SETTINGS_MODULE=eventhub.settings
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - eventhub_network
    restart: unless-stopped
    stdin_open: true
    tty: true

  # Database administration tool (optional)
  adminer:
    image: adminer:latest
    container_name: eventhub_adminer_dev
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: db
    depends_on:
      - db
    networks:
      - eventhub_network
    restart: unless-stopped

# Named volumes for persistent data
volumes:
  postgres_data:
    driver: local
  media_files:
    driver: local
  pip_cache:
    driver: local

# Custom network for service communication
networks:
  eventhub_network:
    driver: bridge
```


### 3. Update .dockerignore

```.dockerignore (dockerignore)
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Django
db.sqlite3
db.sqlite3-journal
*.log
local_settings.py

# Development files
.env
.vscode/
.idea/
*.swp
*.swo

# Git
.git/
.gitignore

# Documentation
README.md
*.md
docs/

# Media files (will be handled by volumes)
media/

# Static files (will be collected in container)
staticfiles/

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# OS
.DS_Store
Thumbs.db

# Node.js (if using frontend build tools)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
```


---

## Environment Configuration

### 1. Create Development Environment File

```
# Django Configuration
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production-2024
DJANGO_SETTINGS_MODULE=eventhub.settings
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,web

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=eventhub_dev
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis Configuration (optional)
REDIS_URL=redis://redis:6379/0

# Email Configuration (for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Media and Static Files
MEDIA_URL=/media/
STATIC_URL=/static/

# API Configuration
API_TITLE=EventHub API
API_VERSION=1.0.0
API_DESCRIPTION=Event management platform API

# Security (Development only)
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```


### 2. Update .env.example

```
# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=eventhub.settings
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=eventhub
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Media and Static Files
MEDIA_URL=/media/
STATIC_URL=/static/

# API Configuration
API_TITLE=EventHub API
API_VERSION=1.0.0
API_DESCRIPTION=Event management platform API

# Security
CSRF_TRUSTED_ORIGINS=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:3000
```


---

## Application Configuration Updates

### 1. Update Django Settings

```python
"""
Django settings for eventhub project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-3%qen2pop0$1qsb-afpj_7==ds5cl!#++&eg-eh+p29uuopr9u')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_spectacular",
    "events",
    "accounts",
]

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": os.getenv('API_TITLE', 'EventHub API'),
    "DESCRIPTION": os.getenv('API_DESCRIPTION', 'A platform for creating and managing events'),
    "VERSION": os.getenv('API_VERSION', '1.0.0'),
    "SERVE_INCLUDE_SCHEMA": False,
}

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "eventhub.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "eventhub.wsgi.application"

# Database Configuration
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
        "OPTIONS": {
            "charset": "utf8mb4",
        } if os.getenv("DB_ENGINE") == "django.db.backends.mysql" else {},
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv('STATIC_URL', '/static/')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files (Uploaded files)
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "accounts.CustomUser"

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '1025'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Security Settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# CORS Settings (if using django-cors-headers)
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000').split(',')

# Cache Configuration (Redis)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
} if 'redis' in REDIS_URL else {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'eventhub.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'eventhub': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```


### 2. Create Docker Helper Scripts

Create a `docker/` directory and add helper scripts:

```sql
-- Create necessary PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```


```shell script
#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "Database is ready!"

# Run Django management commands
echo "Running Django management commands..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
END

# Start the Django development server
echo "Starting Django development server..."
exec "$@"
```


Make the script executable:
```shell script
chmod +x docker/entrypoint.sh
```


---

## Step-by-Step Implementation

### Step 1: Prepare Your Environment

1. **Create environment file**:
```shell script
cp .env.example .env.dev
```


2. **Edit the environment file** with your preferred settings

3. **Create required directories**:
```shell script
mkdir -p docker/init-db
mkdir -p media
mkdir -p staticfiles
```


### Step 2: Build and Start Services

1. **Build the Docker images**:
```shell script
docker-compose -f docker-compose.dev.yml build
```


2. **Start the services**:
```shell script
docker-compose -f docker-compose.dev.yml up -d
```


3. **Check service status**:
```shell script
docker-compose -f docker-compose.dev.yml ps
```


### Step 3: Initialize the Application

1. **Run database migrations**:
```shell script
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
```


2. **Create a superuser**:
```shell script
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```


3. **Collect static files**:
```shell script
docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput
```


### Step 4: Verify the Setup

1. **Check application is running**:
   - Open http://localhost:8000 in your browser
   - Should see Django welcome page or your application

2. **Check database admin**:
   - Open http://localhost:8080 in your browser
   - Login with database credentials to view Adminer

3. **Check Django admin**:
   - Go to http://localhost:8000/admin/
   - Login with superuser credentials

### Step 5: Load Sample Data (Optional)

Create a management command to load sample data:

```python
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from events.models import Event, Category
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Load sample data for development'

    def handle(self, *args, **options):
        # Create sample users
        if not User.objects.filter(email='organizer@example.com').exists():
            organizer = User.objects.create_user(
                email='organizer@example.com',
                password='password123',
                first_name='Event',
                last_name='Organizer'
            )
            self.stdout.write(self.style.SUCCESS('Created organizer user'))
        else:
            organizer = User.objects.get(email='organizer@example.com')

        # Create sample categories
        categories = ['Technology', 'Music', 'Sports', 'Arts', 'Business']
        for cat_name in categories:
            Category.objects.get_or_create(name=cat_name)

        # Create sample events
        locations = ['New York', 'London', 'Tokyo', 'Sydney', 'Berlin']
        for i in range(10):
            Event.objects.get_or_create(
                name=f'Sample Event {i+1}',
                defaults={
                    'description': f'This is a sample event {i+1} for testing purposes.',
                    'date': datetime.now() + timedelta(days=random.randint(1, 30)),
                    'location': random.choice(locations),
                    'organizer': organizer,
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully loaded sample data'))
```


Run the command:
```shell script
docker-compose -f docker-compose.dev.yml exec web python manage.py load_sample_data
```


---

## Development Workflow

### Daily Development Routine

1. **Start the development environment**:
```shell script
docker-compose -f docker-compose.dev.yml up -d
```


2. **View logs**:
```shell script
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f web
```


3. **Run Django commands**:
```shell script
# Run migrations
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# Create migrations
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations

# Run tests
docker-compose -f docker-compose.dev.yml exec web python manage.py test

# Django shell
docker-compose -f docker-compose.dev.yml exec web python manage.py shell
```


4. **Database operations**:
```shell script
# Access PostgreSQL directly
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d eventhub_dev

# Database backup
docker-compose -f docker-compose.dev.yml exec db pg_dump -U postgres eventhub_dev > backup.sql

# Restore database
docker-compose -f docker-compose.dev.yml exec -T db psql -U postgres -d eventhub_dev < backup.sql
```


### Code Changes and Hot Reloading

- **Python code changes**: Automatically reloaded (due to volume mounting)
- **Static files**: Run `collectstatic` if needed
- **Database schema**: Run `makemigrations` and `migrate`
- **New dependencies**: Rebuild the Docker image

### Managing Dependencies

1. **Add new Python package**:
```shell script
# Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Rebuild the image
docker-compose -f docker-compose.dev.yml build web
```


2. **Install package temporarily**:
```shell script
docker-compose -f docker-compose.dev.yml exec web pip install new-package
```


---

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Issues

**Problem**: `django.db.utils.OperationalError: could not connect to server`

**Solutions**:
```shell script
# Check database service status
docker-compose -f docker-compose.dev.yml ps db

# Check database logs
docker-compose -f docker-compose.dev.yml logs db

# Restart database service
docker-compose -f docker-compose.dev.yml restart db

# Check network connectivity
docker-compose -f docker-compose.dev.yml exec web ping db
```


#### 2. Port Already in Use

**Problem**: `Error starting userland proxy: bind: address already in use`

**Solutions**:
```shell script
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.dev.yml
ports:
  - "8001:8000"  # Map to different host port
```


#### 3. Permission Issues

**Problem**: Permission denied when accessing files

**Solutions**:
```shell script
# Fix ownership of media directory
sudo chown -R $USER:$USER media/

# Or run container as root temporarily
docker-compose -f docker-compose.dev.yml exec --user root web chown -R appuser:appuser /app
```


#### 4. Static Files Not Loading

**Problem**: Static files (CSS, JS) not loading in development

**Solutions**:
```shell script
# Collect static files
docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput

# Check STATIC_URL in settings
# Ensure DEBUG=True for development
```


#### 5. Database Migration Issues

**Problem**: Migration conflicts or errors

**Solutions**:
```shell script
# Check migration status
docker-compose -f docker-compose.dev.yml exec web python manage.py showmigrations

# Fake migrations if needed
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate --fake

# Reset database (WARNING: deletes all data)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```


### Debugging Tips

1. **Enable Django Debug Toolbar**:
```shell script
# Add to requirements.txt
echo "django-debug-toolbar==4.2.0" >> requirements.txt

# Add to settings.py INSTALLED_APPS
# Add to settings.py MIDDLEWARE
# Configure in settings.py
```


2. **Use Django Shell for debugging**:
```shell script
docker-compose -f docker-compose.dev.yml exec web python manage.py shell
```


3. **Check environment variables**:
```shell script
docker-compose -f docker-compose.dev.yml exec web env | grep -E "(DB|DJANGO|DEBUG)"
```


---

## Best Practices

### 1. Security Best Practices

- **Never commit `.env` files** to version control
- **Use strong passwords** for database and admin users
- **Regularly update Docker images** and Python packages
- **Use non-root users** in containers
- **Limit exposed ports** to only what's necessary

### 2. Performance Optimization

- **Use Docker layer caching** by copying requirements.txt first
- **Use Alpine Linux images** for smaller image sizes
- **Implement health checks** for all services
- **Use volumes** for persistent data
- **Configure proper logging** levels

### 3. Development Efficiency

- **Use meaningful container names** for easy identification
- **Implement auto-restart policies** for services
- **Use environment-specific configurations**
- **Document all custom commands** and procedures
- **Set up proper logging** and monitoring

### 4. Team Collaboration

- **Maintain comprehensive documentation**
- **Use consistent naming conventions**
- **Provide setup scripts** for new team members
- **Version control Docker configurations**
- **Document troubleshooting procedures**

---

## Summary

This comprehensive guide provides everything needed to dockerize your EventHub Django application for development. The setup includes:

✅ **Complete Docker configuration** with multi-service architecture
✅ **PostgreSQL database** with persistent storage
✅ **Redis caching** for improved performance
✅ **Development-optimized** Django settings
✅ **Hot reloading** for efficient development
✅ **Comprehensive troubleshooting** guide
✅ **Best practices** for security and performance

### Next Steps

1. **Implement the configuration** following the step-by-step guide
2. **Test thoroughly** with your existing codebase
3. **Set up production environment** (separate guide needed)
4. **Configure CI/CD pipeline** for automated testing and deployment
5. **Add monitoring and logging** for production readiness

This setup provides a solid foundation for professional Django development with Docker, ensuring consistency across different development environments and team members.
