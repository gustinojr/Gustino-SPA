#!/usr/bin/env python3
"""
Test script to verify the Telegram bot integration flow.
This script checks that all the components are properly configured.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("GUSTINO SPA - Telegram Bot Integration Test")
print("=" * 60)

# 1. Check environment variables
print("\n1. Checking environment variables...")
required_vars = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_BOT_USERNAME", 
    "OWNER_CHAT_ID",
    "SECRET_KEY"
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "TOKEN" in var or "KEY" in var:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  ✓ {var}: {display_value}")
    else:
        print(f"  ✗ {var}: NOT SET")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  Missing variables: {', '.join(missing_vars)}")
    sys.exit(1)

# 2. Check if modules can be imported
print("\n2. Checking Python modules...")
modules_ok = True
try:
    from flask import Flask
    print("  ✓ Flask")
except ImportError as e:
    print(f"  ✗ Flask: {e}")
    modules_ok = False

try:
    import telebot
    print("  ✓ pyTelegramBotAPI")
except ImportError as e:
    print(f"  ✗ pyTelegramBotAPI: {e}")
    modules_ok = False

try:
    from flask_sqlalchemy import SQLAlchemy
    print("  ✓ Flask-SQLAlchemy")
except ImportError as e:
    print(f"  ✗ Flask-SQLAlchemy: {e}")
    modules_ok = False

if not modules_ok:
    print("\n⚠️  Some modules are missing. Run: pip install -r requirements.txt")
    sys.exit(1)

# 3. Test bot connection
print("\n3. Testing Telegram bot connection...")
try:
    import telebot
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    me = bot.get_me()
    print(f"  ✓ Bot connected: @{me.username}")
    print(f"    Bot ID: {me.id}")
    print(f"    Bot Name: {me.first_name}")
except Exception as e:
    print(f"  ✗ Bot connection failed: {e}")
    sys.exit(1)

# 4. Check file structure
print("\n4. Checking file structure...")
required_files = [
    "app/__init__.py",
    "app/telegram_polling.py",
    "app/telegram_utils.py",
    "app/models.py",
    "app/routes/home.py",
    "app/routes/register.py",
    "app/routes/booking.py",
    "app/templates/home.html",
    "app/templates/wait_for_chatid.html",
    "app/templates/registration.html",
    "app/templates/booking.html",
    "run.py",
    "config.py"
]

missing_files = []
for file_path in required_files:
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        print(f"  ✓ {file_path}")
    else:
        print(f"  ✗ {file_path}: NOT FOUND")
        missing_files.append(file_path)

if missing_files:
    print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
    sys.exit(1)

# 5. Summary
print("\n" + "=" * 60)
print("✅ ALL CHECKS PASSED!")
print("=" * 60)
print("\nYour Gustino SPA Telegram integration is ready!")
print("\nTo start the application:")
print("  python3 run.py")
print("\nFlow summary:")
print("  1. User clicks 'Attiva Bot' on home page")
print("  2. Server starts polling, redirects to /wait-for-chatid")
print("  3. JavaScript opens Telegram and polls /check-chatid")
print("  4. User sends message to bot")
print("  5. Bot saves chat_id, page shows it and redirects to registration")
print("  6. User completes registration form")
print("  7. User books appointment")
print("  8. All messages sent to both user and owner via Telegram")
print("\nBot link: https://t.me/" + os.getenv("TELEGRAM_BOT_USERNAME"))
print("=" * 60)
