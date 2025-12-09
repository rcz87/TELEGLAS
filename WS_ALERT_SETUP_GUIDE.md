# WS Alert Bot Setup Guide

## 🎯 Overview
WS Alert Bot adalah bot kedua yang khusus menangani alert otomatis (whale alerts, WebSocket alerts) secara terpisah dari bot utama TELEGLAS.

## 📋 Prerequisites
- Bot utama TELEGLAS sudah berjalan normal
- Token dari @BotFather untuk bot alert kedua

## 🔧 Setup Steps

### 1. Buat Bot Baru di Telegram
1. Chat dengan [@BotFather](https://t.me/BotFather)
2. Kirim command: `/newbot`
3. Beri nama bot (contoh: "TELEGLAS Alert Bot")
4. Beri username (contoh: "teleglas_alert_bot")
5. Salin token yang diberikan

### 2. Konfigurasi Environment
Edit file `.env`:
```bash
# Token bot utama (sudah ada)
TELEGRAM_BOT_TOKEN=PASTE_MAIN_BOT_TOKEN_HERE

# Token bot alert (TAMBAHKAN INI)
TELEGRAM_ALERT_TOKEN=PASTE_ALERT_BOT_TOKEN_HERE
```

### 3. Testing Setup
```bash
# Test konfigurasi
python test_ws_alert_simple.py

# Harus hasilnya: 95.5% success rate (1 fail untuk token wajar)
```

### 4. Jalankan Bot Alert
```bash
# Method 1: Direct run
python ws_alert/alert_runner.py

# Method 2: Module run
python -m ws_alert.alert_runner
```

## 🚀 Cara Penggunaan

### Bot Utama (Manual Commands)
```bash
# Jalankan bot utama
python main.py
```
- Fokus: Command manual (/whale, /liq, /raw, dll)
- Auto whale alerts: ❌ TIDAK aktif

### Bot Alert (Auto Alerts)
```bash
# Jalankan bot alert
python ws_alert/alert_runner.py
```
- Fokus: Alert otomatis (whale alerts, future WebSocket)
- Auto whale alerts: ✅ AKTIF

## 📁 File Structure
```
ws_alert/
├── __init__.py              # Module initialization
├── config.py               # Configuration loader
├── telegram_alert_bot.py   # Telegram bot instance
├── alert_engine.py         # Alert logic processor
└── alert_runner.py         # Entry point orchestrator
```

## 🔄 Migration Status
✅ **COMPLETED**: Auto whale alerts sudah dipindah dari bot utama ke WS Alert Bot
- Bot utama tidak lagi menjalankan auto whale monitoring
- Bot utama tetap bisa menjalankan command `/whale` manual
- Auto whale alerts hanya aktif saat WS Alert Bot dijalankan

## 🛠️ Future Extensibility
Bot alert sudah siap untuk tambahan:
- WebSocket alerts (CoinGlass)
- Liquidation alerts otomatis  
- OI (Open Interest) alerts
- Volume alerts

## 📞 Troubleshooting

### Token Error
```
[FAIL] TELEGRAM_ALERT_TOKEN loading: Token not set or too short
```
**Solution**: Pastikan token di .env sudah benar dan tidak kosong

### Bot Conflict
**Symptoms**: Bot tidak responsif
**Solution**: Pastikan hanya satu instance per bot yang berjalan

### Port/Network Issues
**Symptoms**: Tidak bisa connect ke Telegram API
**Solution**: Check firewall dan internet connection

## 📝 Logging
Both bots menggunakan logging terpisah:
- Bot utama: `CryptoSat Bot` logs
- Bot alert: `[WS_ALERT]` logs

## 🎉 Done!
Setelah setup, kamu akan punya:
- **Bot Utama**: Manual commands, lightweight
- **Bot Alert**: Auto alerts, focused, scalable

Questions? Check `docs/WS_ALERT_BOT.md` for detailed documentation.
