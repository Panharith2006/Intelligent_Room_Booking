#!/usr/bin/env python
"""
Quick test for Groq integration.
Run this to verify your GROQ_API_KEY works before testing the full chatbot.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
django.setup()

from django.conf import settings
from ai.groq_adapter import call_groq, GroqError

print("=" * 70)
print("Groq Integration Test")
print("=" * 70)

# Check configuration
groq_key = getattr(settings, 'GROQ_API_KEY', None)
groq_model = getattr(settings, 'GROQ_MODEL', None)

print(f"GROQ_API_KEY configured: {bool(groq_key)}")
print(f"GROQ_MODEL: {groq_model}")
print("=" * 70)

if not groq_key:
    print("\nERROR: GROQ_API_KEY not configured!")
    print("\nSteps to fix:")
    print("1. Go to https://console.groq.com/keys")
    print("2. Create a new API key")
    print("3. Copy the key (starts with 'gsk_...')")
    print("4. Update .env file: GROQ_API_KEY=gsk_your_key_here")
    print("5. Run this test again")
    sys.exit(1)

# Test the API
test_prompt = "Hello! I need to book a room for a meeting."
print(f"\nTest prompt: {test_prompt}")
print("-" * 70)

try:
    response = call_groq(test_prompt, api_key=groq_key, model=groq_model, timeout=30)
    print(f"✓ Success! Response:\n{response}")
    print("-" * 70)
    print("\n✓ Groq integration is working!")
    print("\nYou can now:")
    print("1. Start your Django server: python manage.py runserver 8000")
    print("2. Test the chatbot endpoint:")
    print("   Invoke-WebRequest -Uri http://127.0.0.1:8000/chatbot/chat/ -Method POST \\")
    print("     -ContentType 'application/json' \\")
    print("     -Body (@{message='Hello'; session_id='test1'} | ConvertTo-Json) \\")
    print("     -UseBasicParsing | Select-Object -Expand Content")
    print("\n3. Or test via ngrok (already exposed):")
    print("   Your chatbot is accessible via your ngrok URL")
    
except GroqError as e:
    print(f"Groq Error: {e}")
    print("\nTroubleshooting:")
    print("- Check your GROQ_API_KEY is valid at https://console.groq.com/keys")
    print("- Verify the model exists (try 'llama3-8b-8192' or 'mixtral-8x7b-32768')")
    print("- Check if you've exceeded rate limits (free tier has generous limits)")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 70)
