# 🚀 Deployment Guide

This guide covers deploying the Room Booking System across Development, Staging, and Production environments.

## Table of Contents
- [Overview](#overview)
- [Environment Setup](#environment-setup)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Deployment Procedures](#deployment-procedures)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Room Booking System uses a three-tier deployment strategy:

| Environment | Branch | Purpose | Auto-Deploy |
|------------|--------|---------|-------------|
| **Development** | `dev` | Active development, testing new features | ✅ Yes |
| **Staging** | `staging` | Pre-production testing, QA validation | ✅ Yes |
| **Production** | `main` / `master` | Live application for end users | ✅ Yes |

---

## Environment Setup

### Prerequisites
- Python 3.11+
- MySQL 8.0+ (or PostgreSQL)
- Docker & Docker Compose (for containerized deployments)
- Git
- GitHub account with repository access

### Branch Strategy

```
main (production)
  ↑
staging (pre-release)
  ↑
dev (development)
  ↑
feature/* (feature branches)
```

**Workflow:**
1. Create feature branches from `dev`
2. Merge features into `dev` → triggers Development deployment
3. Merge `dev` into `staging` → triggers Staging deployment
4. Merge `staging` into `main` → triggers Production deployment

---

## GitHub Actions CI/CD

### Workflow Files

Each environment has its own workflow:
- `.github/workflows/dev.yml` - Development CI/CD
- `.github/workflows/staging.yml` - Staging CI/CD
- `.github/workflows/production.yml` - Production CI/CD

### Required GitHub Secrets

Navigate to **Settings > Secrets and variables > Actions** and add:

#### Development Secrets
```
DEV_DEEPSEEK_API_KEY         # AI API key for development
DEV_GROQ_API_KEY              # Alternative AI API key
DEV_APP_URL                   # Development app URL
```

#### Staging Secrets
```
STAGING_DEEPSEEK_API_KEY      # AI API key for staging
STAGING_GROQ_API_KEY          # Alternative AI API key
STAGING_APP_URL               # Staging app URL
DOCKER_USERNAME               # Docker Hub username
DOCKER_PASSWORD               # Docker Hub password/token
```

#### Production Secrets
```
PROD_APP_URL                  # Production app URL
DOCKER_USERNAME               # Docker Hub username
DOCKER_PASSWORD               # Docker Hub password/token
```

#### Optional Secrets
```
CODECOV_TOKEN                 # Code coverage reporting
SLACK_WEBHOOK_URL             # Deployment notifications
SENTRY_DSN                    # Error tracking
```

### GitHub Environment Configuration

Create protected environments in **Settings > Environments**:

1. **development**
   - No protection rules needed
   - Auto-deploy on push to `dev`

2. **staging**
   - Required reviewers: 1 (recommended)
   - Auto-deploy on push to `staging`

3. **production**
   - Required reviewers: 2+ (highly recommended)
   - Branch protection: only `main`/`master`
   - Deployment branch: `main`/`master` only

---

## Deployment Procedures

### 1. Development Deployment

**Automatic:** Push to `dev` branch
```bash
git checkout dev
git add .
git commit -m "feat: new feature"
git push origin dev
```

**What happens:**
1. ✅ Run tests
2. 🔍 Code quality checks (non-blocking)
3. 🐳 Build Docker image
4. 🚀 Deploy to development server
5. ✅ Deployment notification

**Manual deployment (local):**
```bash
# Use development settings
export DJANGO_SETTINGS_MODULE=room_booking_system.settings_dev

# Run migrations
python manage.py migrate

# Run server
python manage.py runserver 0.0.0.0:8000
```

---

### 2. Staging Deployment

**Automatic:** Push to `staging` branch
```bash
git checkout staging
git merge dev
git push origin staging
```

**What happens:**
1. ✅ Run full test suite
2. 🔒 Security scanning (safety, bandit)
3. 🔍 Code quality checks (flake8, pylint)
4. 🐳 Build and push Docker image
5. 🚀 Deploy to staging server
6. 🧪 Run smoke tests
7. ✅ Deployment notification

**Manual deployment:**
```bash
# Use staging settings
export DJANGO_SETTINGS_MODULE=room_booking_system.settings_staging

# Run with Docker Compose
docker-compose -f docker-compose.staging.yml up -d

# Or run directly
gunicorn room_booking_system.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4
```

---

### 3. Production Deployment

**Automatic:** Push to `main` or create a release tag
```bash
git checkout main
git merge staging
git push origin main

# Or create a release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

**What happens:**
1. 📦 Create database backup
2. ✅ Run comprehensive tests with coverage
3. 🔒 Security scanning (must pass)
4. 🔍 Code quality validation
5. 🐳 Build and push production Docker image
6. 🚀 Deploy to production server
7. 🗄️ Run database migrations
8. 📁 Collect static files
9. 🧪 Run smoke tests
10. 🔥 Warm up application cache
11. ✅ Deployment notification
12. ⚠️ Auto-rollback on failure

**Manual deployment:**
```bash
# ALWAYS create backup first
./scripts/backup_database.sh

# Use production settings
export DJANGO_SETTINGS_MODULE=room_booking_system.settings_production

# Deploy with Docker
docker-compose -f docker-compose.production.yml up -d

# Run migrations
docker-compose exec web python manage.py migrate --noinput

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Restart services
docker-compose restart web
```

---

## Environment Configuration

### Development (.env.dev)
```env
DEBUG=True
SECRET_KEY=dev-secret-key-change-me
ALLOWED_HOSTS=localhost,127.0.0.1

USE_SQLITE=True
# Or MySQL for dev
DB_NAME=room_booking_dev
DB_USER=root
DB_PASSWORD=dev_password
DB_HOST=localhost
DB_PORT=3307

DJANGO_SETTINGS_MODULE=room_booking_system.settings_dev
```

### Staging (.env.staging)
```env
DEBUG=False
SECRET_KEY=staging-secret-key-from-secrets-manager
ALLOWED_HOSTS=staging.yourdomain.com

MYSQL_DATABASE=room_booking_staging
MYSQL_USER=staging_user
MYSQL_PASSWORD=secure_staging_password
MYSQL_HOST=staging-db.internal
MYSQL_PORT=3306

REDIS_URL=redis://staging-redis:6379/1

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=staging@yourdomain.com
EMAIL_HOST_PASSWORD=app_specific_password

SECURE_SSL_REDIRECT=True
DJANGO_SETTINGS_MODULE=room_booking_system.settings_staging
```

### Production (.env.production)
```env
DEBUG=False
SECRET_KEY=production-secret-from-secrets-manager
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

MYSQL_DATABASE=room_booking_prod
MYSQL_USER=prod_user
MYSQL_PASSWORD=very_secure_production_password
MYSQL_HOST=prod-db.internal
MYSQL_PORT=3306

REDIS_URL=redis://prod-redis:6379/0

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=app_specific_password

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

SENTRY_DSN=https://your-sentry-dsn
DJANGO_SETTINGS_MODULE=room_booking_system.settings_production
```

---

## Docker Deployment

### Build Production Image
```bash
docker build -t room-booking-system:prod .
```

### Run with Docker Compose
```bash
# Development
docker-compose up -d

# Staging
docker-compose -f docker-compose.staging.yml up -d

# Production
docker-compose -f docker-compose.production.yml up -d
```

### Useful Docker Commands
```bash
# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Access Django shell
docker-compose exec web python manage.py shell

# Restart services
docker-compose restart

# Stop and remove containers
docker-compose down
```

---

## Health Checks

Add health check endpoints for monitoring:

```python
# booking/views.py or create health/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Simple health check endpoint"""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)
```

---

## Monitoring and Logging

### Recommended Tools
- **Sentry**: Error tracking and monitoring
- **New Relic**: Application performance monitoring
- **Datadog**: Infrastructure and application monitoring
- **Prometheus + Grafana**: Metrics and visualization
- **ELK Stack**: Centralized logging

### Log Locations
- Development: Console output
- Staging: `/app/logs/staging.log`
- Production: `/app/logs/production.log` + Sentry

---

## Rollback Procedures

### Automatic Rollback
Production workflow includes automatic rollback on deployment failure.

### Manual Rollback

**Docker:**
```bash
# Find previous image
docker images | grep room-booking-system

# Rollback to previous version
docker tag room-booking-system:previous room-booking-system:latest
docker-compose up -d
```

**Database:**
```bash
# Restore from backup
mysql -u root -p room_booking_prod < backup_2024_01_22.sql
```

---

## Troubleshooting

### Common Issues

**1. Tests failing in CI/CD**
- Check test database configuration
- Verify environment variables are set
- Review test logs in GitHub Actions

**2. Docker build fails**
- Clear Docker cache: `docker builder prune`
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt

**3. Deployment succeeds but app doesn't work**
- Check environment variables
- Verify database migrations ran
- Review application logs
- Test database connection

**4. Static files not loading**
```bash
python manage.py collectstatic --noinput
```

**5. Database migration errors**
```bash
# Check migration status
python manage.py showmigrations

# Fake migration if needed (careful!)
python manage.py migrate --fake app_name migration_name
```

---

## Best Practices

1. **Never commit secrets** - Use environment variables or secrets managers
2. **Always test in staging** before production deployment
3. **Create database backups** before migrations
4. **Use feature flags** for gradual rollouts
5. **Monitor deployments** for errors and performance issues
6. **Document changes** in commit messages and release notes
7. **Review code** before merging to staging/production
8. **Run tests locally** before pushing

---

## Support and Resources

- **GitHub Issues**: Report bugs and request features
- **Documentation**: `/docs` folder
- **Team Contact**: Your team communication channel
- **Emergency Contact**: On-call engineer details

---

**Last Updated:** January 2026
**Maintained by:** Development Team
