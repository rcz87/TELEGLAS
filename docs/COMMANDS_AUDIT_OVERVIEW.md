# TELEGLAS BOT COMMANDS AUDIT OVERVIEW
**Phase 1 - Discovery: Complete Command Mapping**

## 📋 Executive Summary

Bot TELEGLAS memiliki 15 command utama yang terdaftar di bot utama (manual commands) dan 0 command di bot alert (khusus alert otomatis). Bot alert berfungsi sebagai sender murni tanpa command handler manual.

## 🗂️ Command Mapping Table

### Bot Utama (Manual Commands)

| Command | Handler Function | File Location | Deskripsi | Status | Catatan |
|---------|------------------|---------------|-----------|--------|---------|
| `/start` | `handle_start` | `handlers/telegram_bot.py` | Menampilkan welcome message dan main menu | ACTIVE | Menu utama dengan tombol shortcut |
| `/help` | `handle_help` | `handlers/telegram_bot.py` | Menampilkan help message dan daftar command | ACTIVE | Dokumentasi lengkap command |
| `/raw` | `handle_raw_data` | `handlers/telegram_bot.py` | Data market komprehensif multi-timeframe | ACTIVE | Butuh parameter symbol |
| `/raw_orderbook` | `raw_orderbook_handler` | `handlers/raw_orderbook.py` | Orderbook depth & imbalance analysis | ACTIVE | Handler terpisah, butuh symbol |
| `/liq` | `handle_liquidation` | `handlers/telegram_bot.py` | Data liquidation untuk specific coin | ACTIVE | Butuh parameter symbol |
| `/sentiment` | `handle_sentiment` | `handlers/telegram_bot.py` | Analisis market sentiment global | ACTIVE | Multi-source sentiment data |
| `/whale` | `handle_whale` | `handlers/telegram_bot.py` | Recent whale transactions | ACTIVE | Hyperliquid whale data |
| `/subscribe` | `handle_subscribe` | `handlers/telegram_bot.py` | Subscribe alert untuk symbol | ACTIVE | Butuh parameter symbol |
| `/unsubscribe` | `handle_unsubscribe` | `handlers/telegram_bot.py` | Unsubscribe alert untuk symbol | ACTIVE | Butuh parameter symbol |
| `/alerts` | `handle_alerts` | `handlers/telegram_bot.py` | Lihat daftar alert aktif user | ACTIVE | Management subscriptions |
| `/status` | `handle_status` | `handlers/telegram_bot.py` | Cek status bot dan performance | ACTIVE | System health check |
| `/alerts_status` | `handle_alerts_status` | `handlers/telegram_bot.py` | Status alert system ON/OFF | ACTIVE | Kontrol whale alerts |
| `/alerts_on_w` | `handle_alerts_on_whale` | `handlers/telegram_bot.py` | Turn ON whale alerts | ACTIVE | Need config change |
| `/alerts_off_w` | `handle_alerts_off_whale` | `handlers/telegram_bot.py` | Turn OFF whale alerts | ACTIVE | Need config change |

### Bot Alert (WS Alert - No Manual Commands)

| Command | Handler Function | File Location | Deskripsi | Status | Catatan |
|---------|------------------|---------------|-----------|--------|---------|
| - | - | - | **NO MANUAL COMMANDS** | N/A | Bot alert murni sender otomatis |

## 📊 Command Categories

### 1. Market Data Commands (Primary)
- `/raw` - Comprehensive market data
- `/raw_orderbook` - Orderbook analysis
- `/liq` - Liquidation data
- `/sentiment` - Market sentiment
- `/whale` - Whale transactions

### 2. Alert Management Commands
- `/subscribe` - Subscribe alerts
- `/unsubscribe` - Unsubscribe alerts
- `/alerts` - View subscriptions
- `/alerts_status` - Alert system status
- `/alerts_on_w` - Enable whale alerts
- `/alerts_off_w` - Disable whale alerts

### 3. System & Help Commands
- `/start` - Welcome & main menu
- `/help` - Help documentation
- `/status` - System status

## 🔍 Command Registration Analysis

### Command Handlers Registration (di `_add_handlers()`)
```python
# Core command handlers
self.application.add_handler(CommandHandler("start", self.handle_start))
self.application.add_handler(CommandHandler("help", self.handle_help))
self.application.add_handler(CommandHandler("liq", self.handle_liquidation))
self.application.add_handler(CommandHandler("sentiment", self.handle_sentiment))
self.application.add_handler(CommandHandler("whale", self.handle_whale))
self.application.add_handler(CommandHandler("subscribe", self.handle_subscribe))
self.application.add_handler(CommandHandler("unsubscribe", self.handle_unsubscribe))
self.application.add_handler(CommandHandler("status", self.handle_status))
self.application.add_handler(CommandHandler("alerts", self.handle_alerts))
self.application.add_handler(CommandHandler("raw", self.handle_raw_data))

# Alert control commands
self.application.add_handler(CommandHandler("alerts_status", self.handle_alerts_status))
self.application.add_handler(CommandHandler("alerts_on_w", self.handle_alerts_on_whale))
self.application.add_handler(CommandHandler("alerts_off_w", self.handle_alerts_off_whale))

# External handler
self.application.add_handler(CommandHandler("raw_orderbook", raw_orderbook_handler))
```

### Bot Commands Setup (di `_setup_bot_commands()`)
Bot commands yang muncul di menu Telegram client:
- `/start` - Start the bot and see main menu
- `/help` - Show help and available commands
- `/raw` - Get comprehensive market data for a symbol
- `/raw_orderbook` - Orderbook depth & imbalance analysis
- `/liq` - Get liquidation data for a symbol
- `/sentiment` - Show market sentiment analysis
- `/whale` - Show recent whale transactions
- `/subscribe` - Subscribe to alerts for a symbol
- `/unsubscribe` - Unsubscribe from alerts
- `/alerts` - View your alert subscriptions
- `/status` - Check bot status and performance
- `/alerts_status` - Show alert system status
- `/alerts_on_w` - Turn ON whale alerts
- `/alerts_off_w` - Turn OFF whale alerts

## 🛡️ Access Control

### Authentication Decorators
1. **`@require_access`** - Untuk command yang butuh whitelist:
   - Semua command kecuali status publik
   - Check `is_user_allowed(user_id)` dari `utils/auth.py`
   - Log access attempts

2. **`@require_public_access`** - Untuk command publik:
   - Tidak digunakan saat ini (semua command pakai `@require_access`)
   - Hanya deny jika user tidak bisa diidentifikasi

## 📁 File Structure

### Main Bot Files
- `handlers/telegram_bot.py` - 14 command handlers
- `handlers/raw_orderbook.py` - 1 command handler (external)
- `main.py` - Bot orchestrator (tidak ada command handlers langsung)

### Alert Bot Files
- `ws_alert/telegram_alert_bot.py` - Alert functions, no command handlers
- `ws_alert/alert_runner.py` - Alert engine runner

## 🎯 Priority Commands for Audit

### High Priority (Core Market Data)
1. `/raw` - Most comprehensive, used frequently
2. `/liq` - Critical liquidation data
3. `/whale` - Key whale transactions
4. `/raw_orderbook` - Orderbook analysis

### Medium Priority (Alert Management)
1. `/subscribe` / `/unsubscribe` - User subscriptions
2. `/sentiment` - Market analysis
3. `/alerts` - Alert management

### Low Priority (System)
1. `/start` / `/help` - Documentation
2. `/status` - System monitoring
3. `/alerts_*` - Alert control commands

## ⚠️ Potential Issues Found

### 1. Missing Parameter Validation
- Commands yang butuh parameter: `/raw`, `/liq`, `/subscribe`, `/unsubscribe`, `/raw_orderbook`
- Beberapa command sudah ada validation, tapi perlu consistency check

### 2. Error Handling Variations
- Different approaches to error handling across commands
- Need standardization for user experience

### 3. Data Source Consistency
- Command yang menggunakan CoinGlass API vs data sources lain
- Need audit untuk multi-exchange aggregated data

### 4. Command Naming
- `/alerts_on_w` / `/alerts_off_w` naming convention (suffix "_w")
- Could be more intuitive: `/whale_alerts_on` / `/whale_alerts_off`

## 📋 Next Steps for Phase 2

1. **Input/Output Analysis** - Detail parameter requirements dan output format
2. **Error Handling Audit** - Standardize error messages dan validation
3. **Data Source Verification** - Check multi-exchange aggregation consistency
4. **UX Evaluation** - User experience dan message formatting

---

**Report Generated:** 2025-12-10 10:45:00 UTC  
**Total Commands Identified:** 15 (Main Bot) + 0 (Alert Bot) = 15 commands  
**Files Analyzed:** `handlers/telegram_bot.py`, `handlers/raw_orderbook.py`, `ws_alert/telegram_alert_bot.py`
