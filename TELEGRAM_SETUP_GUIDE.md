# Telegram Notifications Setup Guide


## Step 1: Create Telegram Bot

### 1.1 Create Bot via BotFather
1. Open Telegram and search for `@BotFather`
2. Send `/start` command
3. Send `/newbot` command
4. Follow the instructions:
   - Choose a name (e.g., "RUPP Room Booking Bot")
   - Choose a username (e.g., "rupp_room_bot")
5. **Save the Bot Token** (e.g., `123456789:ABCDEFGHIJKLMNOPqrstuvwxyz`)

### 1.2 Get Admin Chat IDs
1. Send a message to your new bot
2. Visit this URL in your browser:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. Find your `chat_id` in the JSON response (e.g., `123456789`)
4. **Save all admin chat IDs** who should receive notifications

---

## Step 2: Configure Environment Variables

### 2.1 Update .env File
Add these variables to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPqrstuvwxyz
TELEGRAM_ADMIN_CHAT_IDS=123456789,987654321,555666777
```

### 2.2 Multiple Admins
For multiple admins, separate chat IDs with commas:
```bash
TELEGRAM_ADMIN_CHAT_IDS=123456789,987654321,555666777
```

### 4.2 Test Django Signals
```python
# Run in Django shell
python manage.py shell

# Test notification system
from booking.telegram_notifications import send_telegram_message
send_telegram_message('YOUR_CHAT_ID', 'Test notification from Django!')
```
