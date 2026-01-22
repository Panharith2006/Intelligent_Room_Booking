# Room Booking System

A Django-based room booking application with an analytics dashboard and AI integrations, featuring automated CI/CD deployment pipelines for dev, staging, and production environments.

## Overview
- **Web backend:** Django project (`room_booking_system`) powering booking, users, and notifications
- **Analytics:** Streamlit dashboard (`dashboard_analytics.py`) for visualization and reporting
- **AI integrations:** `ai/` contains adapters and plugins for booking automation and chatbot features
- **Notifications:** Telegram integration and Google Calendar utilities in `booking/`
- **Deployment:** GitHub Actions workflows for automated testing and deployment across environments

## Quickstart (Windows)
1. Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure environment variables
- Copy `.env.example` to `.env` and fill in your configuration:

```powershell
Copy-Item .env.example .env
# Edit .env with your settings
```

- Essential variables: `SECRET_KEY`, database settings, API keys for AI services
- See [.env.example](.env.example) for all available configuration options

4. Apply migrations and create a superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

5. Run the development server:

```powershell
python manage.py runserver
```

## Running the Analytics Dashboard
Start the Streamlit dashboard locally:

```powershell
streamlit run dashboard_analytics.py
```

Or use the provided helper on Windows:

```powershell
.\
un_dashboard.bat
```

## Docker / Production
A `docker-compose.yml` is included for containerized setups:

```powershell
docker-compose up --build
```

For specific environments, use the appropriate settings file:
- **Development:** `room_booking_system/settings_dev.py`
- **Staging:** `room_booking_system/settings_staging.py`
- **Production:** `room_booking_system/settings_production.py`

## Deployment & CI/CD

This project includes automated deployment pipelines for three environments:

| Environment | Branch | Auto-Deploy | Purpose |
|------------|--------|-------------|---------|
| **Development** | `dev` | ✅ Yes | Feature development and testing |
| **Staging** | `staging` | ✅ Yes | Pre-production QA validation |
| **Production** | `main`/`master` | ✅ Yes | Live application |

### Quick Deploy
```bash
# Deploy to development
git push origin dev

# Deploy to staging
git checkout staging
git merge dev
git push origin staging

# Deploy to production
git checkout main
git merge staging
git push origin main
```

### GitHub Actions Workflows
- `.github/workflows/dev.yml` - Development CI/CD
- `.github/workflows/staging.yml` - Staging CI/CD with security scans
- `.github/workflows/production.yml` - Production CI/CD with full validation

**📚 For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**

### Required GitHub Secrets
Configure in **Settings > Secrets and variables > Actions**:
- `DEV_DEEPSEEK_API_KEY`, `DEV_GROQ_API_KEY`, `DEV_APP_URL`
- `STAGING_*` equivalents + `DOCKER_USERNAME`, `DOCKER_PASSWORD`
- `PROD_APP_URL` and production credentials

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup guide.

## Tests
- Run tests with `pytest` (if available) or Django's test runner:

```powershell
pytest -q
# or
python manage.py test
```

## Useful Files
- **Project entry:** `manage.py`
- **Django settings:** 
  - `room_booking_system/settings.py` (base)
  - `room_booking_system/settings_dev.py` (development)
  - `room_booking_system/settings_staging.py` (staging)
  - `room_booking_system/settings_production.py` (production)
- **Dashboard:** `dashboard_analytics.py` and [DASHBOARD_README.md](DASHBOARD_README.md)
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- **Environment config:** [.env.example](.env.example) - Configuration template
- **AI adapters and plugins:** `ai/`
- **Booking app:** `booking/`
- **CI/CD workflows:** `.github/workflows/`

## Features
- 🏢 Room booking management with approval workflow
- 👥 User authentication with Google OAuth integration
- 📊 Real-time analytics dashboard with Streamlit
- 🤖 AI-powered chatbot for automated booking assistance
- 📧 Email notifications for booking confirmations
- 📱 Telegram notifications integration
- 📅 Google Calendar synchronization
- 🔐 Role-based access control (Admin, Faculty, Student)
- 🐳 Docker support for easy deployment
- 🚀 Automated CI/CD pipelines for all environments

## Project Structure
```
.
├── .github/workflows/       # CI/CD pipelines
├── accounts/                # User management
├── ai/                      # AI integrations (DeepSeek, Groq, HF)
├── booking/                 # Core booking functionality
├── chatbot/                 # AI chatbot application
├── room_booking_system/     # Django project settings
├── static/                  # Static assets (CSS, JS)
├── templates/              # HTML templates
├── DEPLOYMENT.md           # Deployment documentation
├── .env.example            # Environment configuration template
└── requirements.txt        # Python dependencies
```

## Documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide for all environments
- **[DASHBOARD_README.md](DASHBOARD_README.md)** - Analytics dashboard documentation
- **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** - System architecture overview
- **[TELEGRAM_SETUP_GUIDE.md](TELEGRAM_SETUP_GUIDE.md)** - Telegram bot setup instructions

## Notes & Next Steps
✅ `.env.example` provided with all configuration options  
✅ CI/CD pipelines configured for dev, staging, and production  
✅ Comprehensive deployment documentation available  
✅ Multiple environment settings files for different deployment targets  

**Need help?** Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup and troubleshooting guides.
