"""
Quick Setup Guide for Analytics Dashboard
Run this script to install dependencies and test the dashboard
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages for the dashboard"""
    print("=" * 60)
    print("📦 Installing Analytics Dashboard Dependencies")
    print("=" * 60)
    print()
    
    packages = [
        "streamlit>=1.28.0",
        "pandas>=2.0.0", 
        "plotly>=5.17.0"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing {package}: {e}\n")
            return False
    
    return True

def check_django_setup():
    """Verify Django is configured correctly"""
    print("=" * 60)
    print("🔍 Checking Django Configuration")
    print("=" * 60)
    print()
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
        import django
        django.setup()
        
        from booking.models import Room, Booking
        
        room_count = Room.objects.count()
        booking_count = Booking.objects.count()
        
        print(f"✅ Django configured successfully")
        print(f"📊 Found {room_count} rooms and {booking_count} bookings\n")
        return True
        
    except Exception as e:
        print(f"❌ Django setup error: {e}\n")
        return False

def run_dashboard():
    """Start the Streamlit dashboard"""
    print("=" * 60)
    print("🚀 Starting Analytics Dashboard")
    print("=" * 60)
    print()
    print("Dashboard will open in your browser at: http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    print()
    
    subprocess.call([sys.executable, "-m", "streamlit", "run", "dashboard_analytics.py"])

def main():
    print("\n" + "=" * 60)
    print("🎯 Room Booking Analytics Dashboard Setup")
    print("=" * 60)
    print()
    
    # Step 1: Install dependencies
    print("Step 1: Installing dependencies...")
    if not install_requirements():
        print("\n❌ Installation failed. Please check errors above.")
        return
    
    # Step 2: Check Django
    print("Step 2: Checking Django setup...")
    if not check_django_setup():
        print("\n⚠️  Django check failed. Dashboard may not work correctly.")
        print("Please ensure Django is configured and migrations are run.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Step 3: Run dashboard
    print("\n✅ All checks passed!")
    response = input("\nStart the dashboard now? (y/n): ")
    
    if response.lower() == 'y':
        run_dashboard()
    else:
        print("\n📝 To start the dashboard later, run:")
        print("   streamlit run dashboard_analytics.py")
        print("   or")
        print("   python run_dashboard.bat")

if __name__ == "__main__":
    main()
