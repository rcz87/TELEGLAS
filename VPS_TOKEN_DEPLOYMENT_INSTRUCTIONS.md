# VPS Token Fix Deployment Instructions

## 🚨 CRITICAL - Fix the Telegram Bot Token Issue

The VPS is still using the old invalid token `7983466046:AAEdnC5_6NsmSPCJwvrN6JusysM4ubvNXIg`. Follow these instructions to fix it.

## 🔧 Quick Fix Steps

### Step 1: SSH into VPS
```bash
ssh root@your_vps_ip
cd /opt/TELEGLAS
```

### Step 2: Run the Fix Script
```bash
python scripts/fix_vps_token_final.py
```

This script will:
- ✅ Backup current `.env` file
- ✅ Create new `.env` with correct token `7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI`
- ✅ Update `config/settings.py` with explicit .env loading
- ✅ Verify configuration is correct

### Step 3: Restart the Bot Service
```bash
systemctl restart teleglas
```

### Step 4: Verify the Fix
```bash
# Check service status
systemctl status teleglas

# View recent logs
journalctl -u teleglas -n 50 --no-pager

# Follow live logs
journalctl -u teleglas -f
```

## 📋 Expected Results

After running the fix, you should see:
- ✅ `Loaded .env from: /opt/TELEGLAS/.env`
- ✅ Token: `7659959497:AAGwJJvKR...BtnDtmZ8SI`
- ✅ `Telegram bot initialized successfully`
- ✅ `Bot Info: @Teleglas_bot (TELEGLAS)`

## 🚫 What NOT to Do

- ❌ Don't manually edit the `.env` file
- ❌ Don't copy from Windows `.env` (has different paths)
- ❌ Don't restart before running the fix script
- ❌ Don't skip the verification step

## 🔍 Manual Verification

If the script fails, you can verify manually:

```bash
# Check token in .env
grep TELEGRAM_BOT_TOKEN .env

# Test the token directly
curl -s "https://api.telegram.org/bot$(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2)/getMe" | jq .

# Should return bot info like:
# {
#   "ok": true,
#   "result": {
#     "id": 7659959497,
#     "is_bot": true,
#     "first_name": "TELEGLAS",
#     "username": "Teleglas_bot"
#   }
# }
```

## 🆘 Troubleshooting

### If service won't start:
```bash
# Check logs for errors
journalctl -u teleglas -n 100 --no-pager

# Check Python environment
which python
python --version
pip list | grep python-telegram-bot

# Test bot manually
cd /opt/TELEGLAS
python -c "from config.settings import settings; print(settings.TELEGRAM_BOT_TOKEN)"
```

### If token still invalid:
```bash
# Check for multiple .env files
find /opt/TELEGLAS -name ".env*" -type f

# Check environment variables
env | grep TELEGRAM

# Force reload environment
source ~/.bashrc
```

## 📞 Support

If you encounter issues:
1. Run the verification steps above
2. Check the service logs
3. Ensure the correct token is in the `.env` file
4. Verify the `config/settings.py` has the updated loading logic

## ✅ Success Indicators

The fix is successful when:
- Bot starts without token errors
- Service shows `active (running)` status
- Logs show `Telegram bot initialized successfully`
- Bot responds to commands in Telegram

---

**⚠️ IMPORTANT**: Run the fix script before attempting any manual changes. The script handles all necessary updates and backups automatically.
