# Complete Guide to Dockerizing EventHub Django Application for Production

## Table of Contents
1. [Production Environment Overview](#production-environment-overview)
2. [Security Considerations](#security-considerations)
3. [Infrastructure Architecture](#infrastructure-architecture)
4. [Docker Configuration for Production](#docker-configuration-for-production)
5. [Environment Configuration](#environment-configuration)
6. [Application Configuration Updates](#application-configuration-updates)
7. [Database Configuration](#database-configuration)
8. [SSL/TLS Configuration](#ssl-tls-configuration)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Deployment Process](#deployment-process)
11. [Performance Optimization](#performance-optimization)
12. [Backup and Recovery](#backup-and-recovery)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance and Updates](#maintenance-and-updates)

---

## Production Environment Overview

### Key Differences from Development

Production environments require:
- **Enhanced security** with HTTPS, secure headers, and proper authentication
- **High availability** with load balancing and redundancy
- **Performance optimization** with caching, CDN, and database tuning
- **Monitoring and alerting** for proactive issue detection
- **Automated backups** and disaster recovery procedures
- **Scalability** to handle varying traffic loads
- **Zero-downtime deployments** for continuous service

### Production Architecture Components

- **Web Server**: Nginx as reverse proxy and static file server
- **WSGI Server**: Gunicorn with multiple workers
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis for session storage and caching
- **Message Queue**: Redis/Celery for background tasks
- **Monitoring**: Prometheus, Grafana, and ELK stack
- **Load Balancer**: For distributing traffic across multiple instances

---

## Security Considerations

### 1. Container Security

- Use official, minimal base images
- Run containers as non-root users
- Implement proper secrets management
- Regular security updates and vulnerability scanning
- Network isolation and firewall rules

### 2. Application Security

- HTTPS enforcement with strong TLS configuration
- Secure session management
- CSRF and XSS protection
- Input validation and sanitization
- Rate limiting and DDoS protection

### 3. Database Security

- Encrypted connections (SSL/TLS)
- Strong authentication and authorization
- Regular security patches
- Database activity monitoring
- Backup encryption

---

## Infrastructure Architecture

### Multi-Container Production Setup
```

┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                 Reverse Proxy (Nginx)                      │
└─────────────┬───────────────────────────┬───────────────────┘
              │                           │
┌─────────────┴─────────────┐  ┌─────────┴─────────────┐
│    Web App Instance 1     │  │    Web App Instance 2 │
│    (Django + Gunicorn)    │  │    (Django + Gunicorn)│
└─────────────┬─────────────┘  └─────────┬─────────────┘
              │                           │
┌─────────────┴───────────────────────────┴─────────────┐
│                PostgreSQL Cluster                     │
│           (Primary + Read Replicas)                   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    Redis Cluster                       │
│              (Cache + Session Store)                   │
└─────────────────────────────────────────────────────────┘
```
---

## Docker Configuration for Production

### 1. Production Dockerfile

Create `Dockerfile.prod`:
```
dockerfile
# Multi-stage build for production
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Collect static files
RUN python manage.py collectstatic --noinput

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Start application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gevent", "eventhub.wsgi:application"]
```
### 2. Nginx Configuration

Create `nginx/nginx.conf`:
```
nginx
upstream django {
    server web1:8000;
    server web2:8000;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Client settings
    client_max_body_size 100M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /app/media/;
        expires 1M;
        add_header Cache-Control "public";
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Auth endpoints with stricter rate limiting
    location /auth/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
    }

    # Health check
    location /health/ {
        access_log off;
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
    }

    # All other requests
    location / {
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
    }
}
```
### 3. Production Docker Compose

Create `docker-compose.prod.yml`:
```
yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: eventhub_db_prod
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 30s
      timeout: 10s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: eventhub_redis_prod
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # Web Application Instance 1
  web1:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: eventhub_web1_prod
    env_file:
      - .env.prod
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media
    networks:
      - backend
      - frontend
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  # Web Application Instance 2
  web2:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: eventhub_web2_prod
    env_file:
      - .env.prod
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media
    networks:
      - backend
      - frontend
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: eventhub_nginx_prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/ssl
      - static_files:/app/staticfiles
      - media_files:/app/media
    networks:
      - frontend
    depends_on:
      - web1
      - web2
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # Celery Worker for Background Tasks
  celery:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: eventhub_celery_prod
    command: celery -A eventhub worker -l info
    env_file:
      - .env.prod
    volumes:
      - media_files:/app/media
    networks:
      - backend
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  # Celery Beat for Scheduled Tasks
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: eventhub_celery_beat_prod
    command: celery -A eventhub beat -l info
    env_file:
      - .env.prod
    volumes:
      - celery_beat:/app/celerybeat-schedule
    networks:
      - backend
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M

  # Database Backup Service
  backup:
    image: postgres:15-alpine
    container_name: eventhub_backup_prod
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./backups:/backups
      - ./scripts/backup.sh:/backup.sh
    networks:
      - backend
    depends_on:
      - db
    restart: "no"
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  static_files:
    driver: local
  media_files:
    driver: local
  celery_beat:
    driver: local

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```
---

## Environment Configuration

### 1. Production Environment Variables

Create `.env.prod`:

```bash
# Django Configuration
DEBUG=False
SECRET_KEY=your-super-secret-production-key-here-make-it-long-and-random
DJANGO_SETTINGS_MODULE=eventhub.settings.production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=eventhub_prod
DB_USER=eventhub_user
DB_PASSWORD=your-super-secure-database-password
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

# Security Configuration
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
X_FRAME_OPTIONS=DENY

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Media and Static Files
MEDIA_URL=/media/
STATIC_URL=/static/
STATIC_ROOT=/app/staticfiles

# Logging Configuration
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn-here

# Monitoring
HEALTH_CHECK_TOKEN=your-health-check-token
```
```


### 2. Secrets Management

Create `secrets/` directory structure:

```
secrets/
├── db_password.txt
├── secret_key.txt
├── email_password.txt
└── ssl/
    ├── yourdomain.crt
    └── yourdomain.key
```


Use Docker secrets in production:

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  secret_key:
    file: ./secrets/secret_key.txt
  email_password:
    file: ./secrets/email_password.txt

services:
  web1:
    secrets:
      - db_password
      - secret_key
      - email_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
      SECRET_KEY_FILE: /run/secrets/secret_key
      EMAIL_PASSWORD_FILE: /run/secrets/email_password
```


---

## Application Configuration Updates

### 1. Create Production Settings

Create `eventhub/settings/production.py`:

```python
"""
Production settings for EventHub Django application.
"""

from .base import *
import os

# Security settings
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
        'CONN_MAX_AGE': 600,
    }
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
        },
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CSRF settings
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# Static and media files
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'json',
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
        'eventhub': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Celery configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Monitoring
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True
    )
```


### 2. Health Check Endpoint

Create `eventhub/health.py`:

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.db import connection
from django.core.cache import cache
import time

@csrf_exempt
@never_cache
def health_check(request):
    """
    Health check endpoint for load balancer and monitoring.
    """
    health_data = {
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0',
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_data['checks']['database'] = 'healthy'
    except Exception as e:
        health_data['checks']['database'] = f'unhealthy: {str(e)}'
        health_data['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'test', 30)
        if cache.get('health_check') == 'test':
            health_data['checks']['cache'] = 'healthy'
        else:
            health_data['checks']['cache'] = 'unhealthy: cache not working'
            health_data['status'] = 'unhealthy'
    except Exception as e:
        health_data['checks']['cache'] = f'unhealthy: {str(e)}'
        health_data['status'] = 'unhealthy'

    status_code = 200 if health_data['status'] == 'healthy' else 503
    return JsonResponse(health_data, status=status_code)
```


Add to `eventhub/urls.py`:

```python
from django.urls import path
from .health import health_check

urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ... other URLs
]
```


---

## SSL/TLS Configuration

### 1. SSL Certificate Setup

```shell script
# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate for testing
openssl req -x509 -newkey rsa:4096 -keyout ssl/yourdomain.key -out ssl/yourdomain.crt -days 365 -nodes

# For production, use Let's Encrypt
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```


### 2. SSL Renewal Script

Create `scripts/ssl_renewal.sh`:

```shell script
#!/bin/bash
# SSL Certificate Renewal Script

# Renew certificates
certbot renew --quiet

# Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# Log renewal
echo "$(date): SSL certificates renewed" >> /var/log/ssl_renewal.log
```


Add to crontab:
```shell script
# Check for renewal twice daily
0 0,12 * * * /path/to/scripts/ssl_renewal.sh
```


---

## Monitoring and Logging

### 1. Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'eventhub'
    static_configs:
      - targets: ['web1:8000', 'web2:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
    scrape_interval: 30s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```


### 2. Grafana Dashboard

Create `monitoring/grafana/dashboards/eventhub.json`:

```json
{
  "dashboard": {
    "title": "EventHub Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(django_http_requests_total[5m])",
            "legendFormat": "{{method}} {{handler}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(django_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(django_http_responses_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```


### 3. ELK Stack for Logs

Create `logging/docker-compose.elk.yml`:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```


---

## Deployment Process

### 1. Deployment Script

Create `scripts/deploy.sh`:

```shell script
#!/bin/bash
set -e

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/deployment.log"

# Functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

backup_database() {
    log "Creating database backup..."
    mkdir -p "$BACKUP_DIR"
    docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/database.sql"
    log "Database backup created: $BACKUP_DIR/database.sql"
}

health_check() {
    log "Performing health check..."
    for i in {1..30}; do
        if curl -f http://localhost/health/ > /dev/null 2>&1; then
            log "Health check passed"
            return 0
        fi
        sleep 10
    done
    log "Health check failed"
    return 1
}

rollback() {
    log "Rolling back deployment..."
    docker-compose -f "$COMPOSE_FILE" down
    docker-compose -f "$COMPOSE_FILE" up -d
    log "Rollback completed"
}

# Main deployment process
main() {
    log "Starting deployment process..."

    # Backup database
    backup_database

    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull

    # Build new images
    log "Building new application images..."
    docker-compose -f "$COMPOSE_FILE" build

    # Run database migrations
    log "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" run --rm web1 python manage.py migrate

    # Collect static files
    log "Collecting static files..."
    docker-compose -f "$COMPOSE_FILE" run --rm web1 python manage.py collectstatic --noinput

    # Rolling deployment
    log "Performing rolling deployment..."

    # Update web1
    docker-compose -f "$COMPOSE_FILE" stop web1
    docker-compose -f "$COMPOSE_FILE" up -d web1

    # Wait and health check
    sleep 30
    if ! health_check; then
        rollback
        exit 1
    fi

    # Update web2
    docker-compose -f "$COMPOSE_FILE" stop web2
    docker-compose -f "$COMPOSE_FILE" up -d web2

    # Final health check
    sleep 30
    if ! health_check; then
        rollback
        exit 1
    fi

    # Restart other services
    docker-compose -f "$COMPOSE_FILE" restart celery celery-beat

    log "Deployment completed successfully"
}

# Execute main function
main "$@"
```


### 2. CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: |
          python manage.py test

      - name: Run security checks
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to production
        uses: appleboy/ssh-action@v0.1.5
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /path/to/eventhub
            git pull origin main
            chmod +x scripts/deploy.sh
            ./scripts/deploy.sh
```


---

## Performance Optimization

### 1. Database Optimization

Create `scripts/db_optimize.sql`:

```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_date ON events_event(date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_location ON events_event(location);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_organizer ON events_event(organizer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_category ON events_event(category_id);

-- Partial indexes for active events
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_active
ON events_event(date) WHERE date > NOW();

-- Analyze tables
ANALYZE events_event;
ANALYZE events_category;
ANALYZE accounts_customuser;
```


### 2. Caching Strategy

Update `eventhub/settings/production.py`:

```python
# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
        },
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL') + '/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

# Cache timeouts
CACHE_TIMEOUT = {
    'default': 300,  # 5 minutes
    'events': 900,   # 15 minutes
    'users': 1800,   # 30 minutes
}
```


### 3. Gunicorn Configuration

Create `gunicorn.conf.py`:

```python
# Gunicorn configuration for production

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests
timeout = 30
keepalive = 5

# Logging
accesslog = "/app/logs/gunicorn_access.log"
errorlog = "/app/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "eventhub"

# Worker recycling
preload_app = True
```


---

## Backup and Recovery

### 1. Database Backup Script

Create `scripts/backup.sh`:

```shell script
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=30
DB_NAME=${DB_NAME:-eventhub_prod}
DB_USER=${DB_USER:-eventhub_user}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
echo "Starting database backup..."
pg_dump -h db -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Media files backup
echo "Starting media files backup..."
tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" -C /app media/

# Clean old backups
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $TIMESTAMP"
```


### 2. Restore Script

Create `scripts/restore.sh`:

```shell script
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME=${DB_NAME:-eventhub_prod}
DB_USER=${DB_USER:-eventhub_user}

# Function to list available backups
list_backups() {
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No database backups found"
}

# Function to restore database
restore_database() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        echo "Backup file not found: $backup_file"
        exit 1
    fi

    echo "Restoring database from: $backup_file"

    # Stop web services
    docker-compose -f docker-compose.prod.yml stop web1 web2

    # Restore database
    gunzip -c "$backup_file" | psql -h db -U "$DB_USER" "$DB_NAME"

    # Start web services
    docker-compose -f docker-compose.prod.yml start web1 web2

    echo "Database restore completed"
}

# Function to restore media files
restore_media() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        echo "Media backup file not found: $backup_file"
        exit 1
    fi

    echo "Restoring media files from: $backup_file"
    tar -xzf "$backup_file" -C /app/
    echo "Media files restore completed"
}

# Main function
main() {
    case "${1:-}" in
        list)
            list_backups
            ;;
        db)
            restore_database "$2"
            ;;
        media)
            restore_media "$2"
            ;;
        *)
            echo "Usage: $0 {list|db|media} [backup_file]"
            echo "  list          - List available backups"
            echo "  db <file>     - Restore database from backup file"
            echo "  media <file>  - Restore media files from backup file"
            exit 1
            ;;
    esac
}

main "$@"
```


### 3. Automated Backup Schedule

Add to crontab:

```shell script
# Daily database backup at 2 AM
0 2 * * * /path/to/scripts/backup.sh

# Weekly media backup on Sunday at 3 AM
0 3 * * 0 /path/to/scripts/backup.sh media

# Monthly full backup on 1st day at 4 AM
0 4 1 * * /path/to/scripts/backup.sh full
```


---

## Troubleshooting

### 1. Common Production Issues

#### High CPU Usage
```shell script
# Check container resource usage
docker stats

# Analyze slow queries
docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"
```


#### Memory Issues
```shell script
# Check memory usage
docker-compose -f docker-compose.prod.yml exec web1 free -h

# Analyze Django memory usage
docker-compose -f docker-compose.prod.yml exec web1 python manage.py shell -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
"
```


#### Database Connection Issues
```shell script
# Check database connections
docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "
SELECT count(*) as connection_count, state
FROM pg_stat_activity
GROUP BY state;"

# Check database locks
docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;"
```


### 2. Log Analysis

```shell script
# Check application logs
docker-compose -f docker-compose.prod.yml logs -f web1 | grep ERROR

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx | grep -E "(4[0-9]{2}|5[0-9]{2})"

# Check database logs
docker-compose -f docker-compose.prod.yml logs db | grep -i error
```


---

## Maintenance and Updates

### 1. Security Updates

```shell script
# Update base images
docker-compose -f docker-compose.prod.yml pull

# Rebuild with security patches
docker-compose -f docker-compose.prod.yml build --no-cache

# Update Python packages
pip list --outdated
pip install --upgrade package_name
```


### 2. Performance Monitoring

```shell script
# Monitor key metrics
docker-compose -f docker-compose.prod.yml exec web1 python manage.py shell -c "
from django.core.cache import cache
from django.db import connection

# Cache hit rate
print('Cache info:', cache.get_many(['key1', 'key2']))

# Database query count
print('DB queries:', len(connection.queries))
"
```


### 3. Regular Maintenance Tasks

Create `scripts/maintenance.sh`:

```shell script
#!/bin/bash
# Regular maintenance tasks

# Clean up old Docker images
docker system prune -f

# Vacuum database
docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Clean up old log files
find /app/logs -name "*.log" -mtime +7 -delete

# Clear expired cache entries
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB

echo "Maintenance completed: $(date)"
```


---

## Summary

This comprehensive production guide provides:

✅ **Production-ready Docker configuration** with security best practices
✅ **Multi-container architecture** with load balancing and redundancy
✅ **SSL/TLS encryption** and security headers
✅ **Monitoring and logging** with Prometheus, Grafana, and ELK stack
✅ **Automated deployment** with CI/CD pipeline
✅ **Performance optimization** with caching and database tuning
✅ **Backup and recovery** procedures
✅ **Troubleshooting guides** for common issues
✅ **Maintenance procedures** for ongoing operations

### Key Production Features

1. **High Availability**: Multiple web instances with load balancing
2. **Security**: HTTPS, secure headers, secrets management
3. **Performance**: Redis caching, database optimization, CDN ready
4. **Monitoring**: Comprehensive monitoring and alerting
5. **Scalability**: Easily scalable architecture
6. **Reliability**: Automated backups and recovery procedures

This setup provides enterprise-grade production deployment for your EventHub Django application with all necessary components for reliable, secure, and scalable operations.
```
This production guide covers all the essential aspects of deploying your EventHub Django application in a production environment, including security, performance, monitoring, and maintenance considerations. The configuration is designed to be robust, scalable, and maintainable for real-world production use.
```
