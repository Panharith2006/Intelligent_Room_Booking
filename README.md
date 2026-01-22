# Room Booking System

A Django-based room booking application with an analytics dashboard and AI integrations.

## Overview
- Web backend: Django project (`room_booking_system`) powering booking, users, and notifications.
- Analytics: Streamlit dashboard (`dashboard_analytics.py`) for visualization and reporting.
- AI integrations: `ai/` contains adapters and plugins used for booking automation and chatbot features.
- Notifications: Telegram integration and Google Calendar utilities included in `booking/`.

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
- Copy any `.env` or set variables for `SECRET_KEY`, database connection, and OAuth credentials.
- Ensure `DJANGO_SETTINGS_MODULE` is set when running custom settings (defaults to `room_booking_system.settings`).

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
- A `docker-compose.yml` is included for containerized setups. Review environment variables and volumes before using:

```powershell
docker-compose up --build
```

For deployments, prefer the appropriate `settings_*.py` configuration files in `room_booking_system/`.

## Tests
- Run tests with `pytest` (if available) or Django's test runner:

```powershell
pytest -q
# or
python manage.py test
```

## Useful Files
- Project entry: `manage.py`
- Django settings: `room_booking_system/settings.py` and `room_booking_system/settings_production.py`
- Dashboard: `dashboard_analytics.py` and [DASHBOARD_README.md](DASHBOARD_README.md)
- AI adapters and plugins: `ai/`
- Booking app: `booking/`

## Notes & Next Steps
- Provide a `.env.example` with required environment variables for easier onboarding.
- Add CI for tests and linting, and document deployment steps for your target platform.

If you want, I can also:
- Add a `.env.example` file
- Add a short contributors / development section
- Create a one-click script to seed demo data
