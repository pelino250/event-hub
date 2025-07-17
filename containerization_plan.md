# EventHub Containerization Plan

## Introduction and Overview

This document outlines the plan for containerizing the EventHub application, a Django-based web application for event management. The containerization will provide consistent development environments, simplified deployment, and improved scalability.

## Project Overview

EventHub is a Django application with the following key components:
- Django 5.2.3 web framework
- Django REST Framework for API endpoints
- Custom user authentication system
- Media file handling for event images
- Currently using SQLite database (with potential to use PostgreSQL)
- Environment variable management with python-dotenv

## Docker Setup

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=eventhub.settings

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Run collectstatic (for production)
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "eventhub.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_DB=${DB_NAME}
    restart: unless-stopped

volumes:
  postgres_data:
```

## Environment Configuration

### .env.example file

```
# Django settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=eventhub
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

### Database Configuration

The application currently uses SQLite, but for containerized environments, we'll transition to PostgreSQL. This requires updating the settings.py file to use environment variables for database configuration:

```python
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}
```

## Development Workflow

1. **Setup**:
   - Clone the repository
   - Copy `.env.example` to `.env` and configure environment variables
   - Run `docker-compose up -d`

2. **Development**:
   - Code changes in the local directory will be reflected in the container due to volume mounting
   - Run migrations with `docker-compose exec web python manage.py migrate`
   - Create superuser with `docker-compose exec web python manage.py createsuperuser`

3. **Testing**:
   - Run tests with `docker-compose exec web python manage.py test`

## Production Considerations

For production deployment, the following adjustments are recommended:

1. **Security**:
   - Set `DEBUG=False` in production
   - Use a strong, randomly generated `SECRET_KEY`
   - Configure `ALLOWED_HOSTS` properly
   - Use HTTPS with proper SSL certificates

2. **Performance**:
   - Use Gunicorn as the WSGI server
   - Configure a proper number of workers based on available CPU cores
   - Add Nginx as a reverse proxy for static files and SSL termination

3. **Static and Media Files**:
   - Configure a volume for persistent media storage
   - Consider using cloud storage (AWS S3, Google Cloud Storage) for media files
   - Serve static files through Nginx

4. **Database**:
   - Use a managed PostgreSQL service or properly configured PostgreSQL container
   - Configure database backups
   - Consider read replicas for high-traffic scenarios

## CI/CD Integration

### GitHub Actions Workflow Example

```yaml
name: EventHub CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: eventhub_test
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      env:
        DB_ENGINE: django.db.backends.postgresql
        DB_NAME: eventhub_test
        DB_USER: postgres
        DB_PASSWORD: postgres
        DB_HOST: localhost
        DB_PORT: 5432
      run: |
        python manage.py test

  build-and-push:
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: yourusername/eventhub:latest
```

## Next Steps

1. **Implementation**:
   - Create Dockerfile and docker-compose.yml
   - Update settings.py to use environment variables
   - Create .env.example file
   - Test containerized application locally

2. **Documentation**:
   - Update README.md with Docker setup instructions
   - Document environment variables

3. **CI/CD**:
   - Set up GitHub Actions or other CI/CD pipeline
   - Configure automated testing and deployment
