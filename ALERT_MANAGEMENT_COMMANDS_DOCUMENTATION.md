# TELEGLAS ALERT MANAGEMENT COMMANDS - DOKUMENTASI LENGKAP
**Analisis Teknis & Panduan Penggunaan Tanpa Modifikasi Kode**

---

## 📋 OVERVIEW

Dokumentasi ini menjelaskan secara lengkap 6 alert-management commands yang ada di TELEGLAS bot, termasuk fungsi, flow kerja, lokasi file handler, dan contoh output aktual tanpa melakukan perubahan kode apa pun.

**Commands yang Didokumentasikan:**
1. `/subscribe` - Berlangganan alert untuk simbol tertentu
2. `/unsubscribe` - Berhenti berlangganan alert untuk simbol tertentu  
3. `/alerts` - Melihat daftar alert aktif pengguna
4. `/alerts_status` - Melihat status sistem alert
5. `/alerts_on_w` - Mengaktifkan whale alerts
6. `/alerts_off_w` - Menonaktifkan whale alerts

---

## 🎯 COMMAND 1: `/subscribe`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Menambahkan user ke sistem alert untuk simbol kripto tertentu
**Use Case:** User ingin menerima notifikasi otomatis untuk events penting di simbol yang dipilih
**Alert Types:** Liquidations (> $1M), Whale Transactions (> $500K), Extreme Funding Rates (±1%)

### 🔄 Flow Kerja (Simplified)
```
User input: /subscribe BTC
           ↓
1. Parameter validation (symbol required)
           ↓
2. Create UserSubscription object
           ↓
3. Database operation (async)
   - user_id: ID Telegram user
   - symbol: "BTC" (uppercase)
   - alert_types: ["liquidation", "whale", "funding"]
           ↓
4. Success/Failure response ke user
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 800-850 (tergantung versi)  
**Decorator:** `@require_access` (whitelist protection)

### 🗄️ Konfigurasi & Dependencies
**Database Manager:** `core/database.py` - `db_manager` instance  
**Model Used:** `UserSubscription` (dataclass)  
**Key Fields:** `user_id`, `symbol`, `alert_types`  
**Security:** `@require_access` decorator untuk whitelist validation

### 📤 Contoh Output Aktual

#### ✅ Output Sukses:
```
✅ SUBSCRIPTION SUCCESSFUL

You're now subscribed to all alerts for BTC:
• 🚨 Massive Liquidations (>$1M)
• 🐋 Whale Transactions (>$500,000)
• 💰 Extreme Funding Rates (±1%)

Use /alerts to manage your subscriptions.
```

#### ⚠️ Output Tanpa Symbol (Fallback ke Inline Keyboard):
```
🔔 Subscribe to Alerts

Choose alert type for BTC:

[🔥 Liquidations] [🐋 Whales] [💰 Funding Rates] [📊 All Alerts]
```

#### ❌ Output Error Database:
```
❌ Subscription Failed

Could not process your subscription. Please try again.
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Database integration: `core/database.py`
- [x] Parameter validation: Symbol required
- [x] Security: Whitelist protected
- [x] Error handling: Database failures handled
- [x] User feedback: Clear success/failure messages

---

## 🎯 COMMAND 2: `/unsubscribe`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Menghapus user dari sistem alert untuk simbol tertentu
**Use Case:** User tidak lagi ingin menerima notifikasi untuk simbol yang dipilih
**Scope:** Menghapus semua alert types (liquidation, whale, funding) untuk simbol tersebut

### 🔄 Flow Kerja (Simplified)
```
User input: /unsubscribe BTC
           ↓
1. Parameter validation (symbol required)
           ↓
2. Database operation (async)
   - db_manager.remove_user_subscription(user_id, "BTC")
           ↓
3. Success/Failure response ke user
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 850-900  
**Decorator:** `@require_access`

### 🗄️ Konfigurasi & Dependencies
**Database Manager:** `core/database.py` - `db_manager.remove_user_subscription()`  
**Parameters:** `user_id` (int), `symbol` (str)  
**Return:** Boolean success/failure  
**Security:** Same whitelist protection as other commands

### 📤 Contoh Output Aktual

#### ✅ Output Sukses:
```
✅ UNSUBSCRIBED SUCCESSFULLY

You've been unsubscribed from all alerts for BTC:
• 🚨 Massive Liquidations
• 🐋 Whale Transactions
• 💰 Extreme Funding Rates

💡 Use /alerts to view remaining subscriptions
💡 Use /subscribe SYMBOL to resubscribe
```

#### ❌ Output Symbol Kosong:
```
❌ SYMBOL REQUIRED

Usage: /unsubscribe [SYMBOL]

Examples:
• /unsubscribe BTC
• /unsubscribe ETH
• /unsubscribe SOL
```

#### ❌ Output Gagal/Tidak Ada Subscription:
```
❌ UNSUBSCRIBE FAILED

You may not have an active subscription for this symbol.
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Database integration: `core/database.py`
- [x] Parameter validation: Symbol required dengan examples
- [x] Security: Whitelist protected
- [x] Error handling: Database failures + invalid subscription handled
- [x] User feedback: Clear confirmation + guidance

---

## 🎯 COMMAND 3: `/alerts`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Menampilkan daftar semua alert subscriptions yang aktif untuk user
**Use Case:** User ingin melihat simbol-simbol yang sedang dipantau dan jenis alertnya
**Information Displayed:** Symbol, alert types, subscription date

### 🔄 Flow Kerja (Simplified)
```
User input: /alerts
           ↓
1. Database query (async)
   - db_manager.get_user_subscriptions(user_id)
           ↓
2. Process subscription list
   - Format each subscription with alert types + date
           ↓
3. Generate response message
   - Empty state message jika tidak ada
   - Formatted list jika ada subscriptions
           ↓
4. Send response ke user
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 750-800  
**Decorator:** `@require_access`

### 🗄️ Konfigurasi & Dependencies
**Database Manager:** `core/database.py` - `db_manager.get_user_subscriptions()`  
**Return Type:** List of `UserSubscription` objects  
**Data Displayed:** Symbol, alert_types list, created_at timestamp  
**Formatting:** Markdown dengan bullet points dan emojis

### 📤 Contoh Output Aktual

#### ✅ Output Dengan Subscriptions:
```
🔔 YOUR ALERT SUBSCRIPTIONS

📊 ACTIVE SUBSCRIPTIONS: 3

🔹 1. BTC
   🚨 Liquidation | 🐋 Whale | 💰 Funding
   🕐 Subscribed: 2025-01-01

🔹 2. ETH
   🚨 Liquidation | 🐋 Whale
   🕐 Subscribed: 2025-01-02

🔹 3. SOL
   🐋 Whale
   🕐 Subscribed: 2025-01-03

🔧 MANAGEMENT COMMANDS:
• /unsubscribe [SYMBOL] - Remove alerts
• /subscribe [SYMBOL] - Add new alerts
• /alerts_status - System status

🌐 DATA SOURCES: CoinGlass + Hyperliquid
⚡ UPDATE FREQUENCY: Real-time (5-30s)
🛡️ PRIVACY: Your subscriptions are confidential
```

#### 📭 Output Tanpa Subscriptions:
```
📭 NO ACTIVE SUBSCRIPTIONS

You're not subscribed to any alerts.

💡 QUICK START:
• /subscribe BTC - Subscribe to BTC alerts
• /subscribe ETH - Subscribe to ETH alerts
• /subscribe SOL - Subscribe to SOL alerts

🔔 WHAT YOU'LL GET:
• 🚨 Massive Liquidations (>$1M)
• 🐋 Whale Transactions (>$500K)
• 💰 Extreme Funding Rates (±1%)

⚡ REAL-TIME MONITORING ACTIVE 24/7
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Database integration: `core/database.py`
- [x] No parameter required: Direct query
- [x] Security: Whitelist protected
- [x] Empty state handling: Helpful guidance
- [x] Rich formatting: Icons, sections, management commands

---

## 🎯 COMMAND 4: `/alerts_status`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Menampilkan status keseluruhan sistem alert (ON/OFF state)
**Use Case:** User ingin mengetahui apakah sistem alert sedang aktif atau tidak
**Information Displayed:** Whale alert status, broadcast status, subscription count

### 🔄 Flow Kerja (Simplified)
```
User input: /alerts_status
           ↓
1. Check configuration settings
   - settings.ENABLE_WHALE_ALERTS
   - settings.ENABLE_BROADCAST_ALERTS
           ↓
2. Query user subscriptions (async)
   - Count active subscriptions for user
           ↓
3. Generate status message
   - Dynamic indicators (🟢/🔴)
   - Real-time information
   - Control command references
           ↓
4. Send response ke user
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_alerts_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 950-1000  
**Decorator:** `@require_access`

### 🗄️ Konfigurasi & Dependencies
**Settings Module:** `config/settings.py`  
**Key Settings:** 
- `ENABLE_WHALE_ALERTS` (boolean)
- `ENABLE_BROADCAST_ALERTS` (boolean)
- `TELEGRAM_ALERT_CHANNEL_ID` (string)
**Database:** `core/database.py` untuk subscription count  
**Logging:** Access attempt logging untuk audit trail

### 📤 Contoh Output Aktual

#### ✅ Output Status Lengkap:
```
🔔 ALERT SYSTEM STATUS

📊 REAL-TIME MONITORING:
🐋 Whale Alerts: 🟢 ENABLED
📢 Broadcast Alerts: 🟢 ENABLED
🔔 Your Subscriptions: 📊 3 active

🔧 SERVICE STATUS:
✅ Liquidation Monitor: MANUAL ONLY
✅ Funding Rate Radar: MANUAL ONLY
✅ Market Sentiment: MANUAL ONLY
✅ Raw Data Analysis: MANUAL ONLY

💡 CONTROL COMMANDS:
• /alerts_on_w - Enable whale alerts
• /alerts_off_w - Disable whale alerts
• /alerts_status - Show this status
• /alerts - Manage subscriptions

🛡️ SECURITY: WHITELIST ACCESS CONTROL ENABLED
⚡ STATUS GENERATED: 2025-12-10 12:00:00 UTC
```

#### 🔄 Output Status Berbeda:
```
🔔 ALERT SYSTEM STATUS

📊 REAL-TIME MONITORING:
🐋 Whale Alerts: 🔴 DISABLED
📢 Broadcast Alerts: 🟢 ENABLED
🔔 Your Subscriptions: 📊 0 active

[... rest of the message ...]
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Settings integration: `config/settings.py`
- [x] Database integration: Subscription counting
- [x] Dynamic status: Real-time configuration checking
- [x] Security: Whitelist protected + access logging
- [x] User guidance: Control command references

---

## 🎯 COMMAND 5: `/alerts_on_w`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Mengaktifkan whale alerts secara dinamis (runtime)
**Use Case:** User ingin mengaktifkan notifikasi transaksi whale tanpa restart bot
**Scope:** Mengubah status whale monitoring dari disabled ke enabled

### 🔄 Flow Kerja (Simplified)
```
User input: /alerts_on_w
           ↓
1. Check whale watcher service availability
   - whale_watcher service exists?
   - Has enable_alerts() method?
           ↓
2. Attempt to enable whale alerts (async)
   - await whale_watcher.enable_alerts()
           ↓
3. Update settings if possible
   - settings.ENABLE_WHALE_ALERTS = True
           ↓
4. Generate response based on result
   - Success confirmation
   - Service unavailable message
   - Configuration required guidance
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_alerts_on_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 1000-1050  
**Decorator:** `@require_access`

### 🗄️ Konfigurasi & Dependencies
**Whale Watcher Service:** `services/whale_watcher.py`  
**Key Methods:** `enable_alerts()` (async, returns boolean)  
**Settings:** `config/settings.py` - `ENABLE_WHALE_ALERTS`  
**Threshold:** `settings.WHALE_TRANSACTION_THRESHOLD_USD` (default: $500,000)  
**Logging:** Access dan action logging untuk audit

### 📤 Contoh Output Aktual

#### ✅ Output Sukses Mengaktifkan:
```
🐋 WHALE ALERTS ENABLED

✅ Whale monitoring is now ACTIVE

🔔 You'll receive alerts for transactions >$500,000
⚡ Real-time monitoring from Hyperliquid
📊 Multi-coin whale detection

💡 Use /alerts_off_w to disable anytime
```

#### ⚠️ Output Service Unavailable:
```
⚠️ SERVICE UNAVAILABLE

Whale monitoring service is currently unavailable.
Please try again in a few moments.
```

#### ⚠️ Output Configuration Required:
```
⚠️ SERVICE CONFIGURATION REQUIRED

Whale monitoring service is not properly configured.

Please check:
• Whale watcher service is running
• Hyperliquid API is accessible
• Alert system is initialized

Contact admin for assistance.
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Service integration: `services/whale_watcher.py`
- [x] Dynamic control: Runtime enable/disable
- [x] Settings update: `config/settings.py`
- [x] Error handling: Service unavailable + configuration issues
- [x] User feedback: Clear confirmation + guidance
- [x] Security: Whitelist protected + action logging

---

## 🎯 COMMAND 6: `/alerts_off_w`

### 📝 Fungsi & Tujuan
**Primary Purpose:** Menonaktifkan whale alerts secara dinamis (runtime)
**Use Case:** User ingin berhenti menerima notifikasi transaksi whale tanpa restart bot
**Scope:** Mengubah status whale monitoring dari enabled ke disabled

### 🔄 Flow Kerja (Simplified)
```
User input: /alerts_off_w
           ↓
1. Check whale watcher service availability
   - whale_watcher service exists?
   - Has disable_alerts() method?
           ↓
2. Attempt to disable whale alerts (async)
   - await whale_watcher.disable_alerts()
           ↓
3. Update settings if possible
   - settings.ENABLE_WHALE_ALERTS = False
           ↓
4. Generate response based on result
   - Success confirmation
   - Service unavailable message
   - Alternative access information
```

### 📁 Lokasi File & Handler
**Primary Handler:** `handlers/telegram_bot.py`  
**Function Name:** `handle_alerts_off_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE)`  
**Line Location:** ~Baris 1050-1100  
**Decorator:** `@require_access`

### 🗄️ Konfigurasi & Dependencies
**Whale Watcher Service:** `services/whale_watcher.py`  
**Key Methods:** `disable_alerts()` (async, returns boolean)  
**Settings:** `config/settings.py` - `ENABLE_WHALE_ALERTS`  
**Fallback:** Manual whale checks via `/whale` command tetap available  
**Logging:** Access dan action logging untuk audit trail

### 📤 Contoh Output Aktual

#### ✅ Output Sukses Menonaktifkan:
```
🐋 WHALE ALERTS DISABLED

✅ Whale monitoring is now INACTIVE

🔔 You will NOT receive whale transaction alerts
📊 Manual whale checks still available via /whale
⚡ Real-time monitoring paused

💡 Use /alerts_on_w to re-enable anytime
```

#### ⚠️ Output Service Unavailable:
```
⚠️ SERVICE UNAVAILABLE

Whale monitoring service is currently unavailable.
Please try again in a few moments.
```

#### ⚠️ Output Configuration Required:
```
⚠️ SERVICE CONFIGURATION REQUIRED

Whale monitoring service is not properly configured.

Please check:
• Whale watcher service is running
• Hyperliquid API is accessible
• Alert system is initialized

Contact admin for assistance.
```

### 🎯 Status Implementasi
- [x] Handler exists: `handlers/telegram_bot.py`
- [x] Service integration: `services/whale_watcher.py`
- [x] Dynamic control: Runtime enable/disable
- [x] Settings update: `config/settings.py`
- [x] Fallback information: Manual checks still available
- [x] Error handling: Service unavailable + configuration issues
- [x] User feedback: Clear confirmation + guidance
- [x] Security: Whitelist protected + action logging

---

## 📊 SUMMARY TABLE

| Command | Fungsi Utama | Handler Location | Database | Service Integration | Status |
|---------|----------------|-----------------|-----------|-------------------|---------|
| `/subscribe` | Tambah alert subscription | `handlers/telegram_bot.py` | ✅ `UserSubscription` | ❌ Tidak ada | ✅ Production Ready |
| `/unsubscribe` | Hapus alert subscription | `handlers/telegram_bot.py` | ✅ Remove operation | ❌ Tidak ada | ✅ Production Ready |
| `/alerts` | Lihat daftar subscription | `handlers/telegram_bot.py` | ✅ Query operation | ❌ Tidak ada | ✅ Production Ready |
| `/alerts_status` | Status sistem alert | `handlers/telegram_bot.py` | ✅ Count operation | ❌ Tidak ada | ✅ Production Ready |
| `/alerts_on_w` | Aktifkan whale alerts | `handlers/telegram_bot.py` | ❌ Tidak ada | ✅ `whale_watcher` | ✅ Production Ready |
| `/alerts_off_w` | Nonaktifkan whale alerts | `handlers/telegram_bot.py` | ❌ Tidak ada | ✅ `whale_watcher` | ✅ Production Ready |

---

## 🔗 INTER-COMMAND RELATIONSHIPS

### Workflow Alami User:
1. **Discovery:** `/alerts` (lihat subscription aktif)
2. **Add:** `/subscribe BTC` (tambah simbol)
3. **Check:** `/alerts_status` (verifikasi sistem aktif)
4. **Control:** `/alerts_on_w` atau `/alerts_off_w` (kontrol whale)
5. **Remove:** `/unsubscribe BTC` (hapus simbol)

### Data Flow:
```
Database (core/database.py)
    ↓ ↑
User Management Commands (/subscribe, /unsubscribe, /alerts)
    ↓ ↑
System Status Commands (/alerts_status)
    ↓ ↑
Service Control Commands (/alerts_on_w, /alerts_off_w)
    ↓ ↑
External Services (services/whale_watcher.py)
```

---

## 🛡️ SECURITY & ACCESS CONTROL

### ✅ Consistent Security Pattern:
**Semua 6 commands menggunakan:**
- `@require_access` decorator untuk whitelist validation
- User identification via Telegram user ID
- Access logging untuk audit trail
- Input sanitization untuk security

### 🔐 Access Control Flow:
```
User Command Input
        ↓
@require_access decorator
        ↓
is_user_allowed(user_id) check
        ↓
Whitelist validation
        ↓
Command execution (jika allowed)
        ↓
Access logging (success/denied)
```

---

## 📝 KONKLUSI

### ✅ IMPLEMENTASI STATUS:
- **6/6 Commands**: Semua sudah implemented dan production-ready
- **1 Central Handler**: `handlers/telegram_bot.py` untuk semua commands
- **Database Integration**: 3 commands menggunakan `core/database.py`
- **Service Integration**: 2 commands menggunakan `services/whale_watcher.py`
- **Security**: Semua commands memiliki whitelist protection
- **Error Handling**: Comprehensive error handling untuk semua scenarios
- **User Experience**: Consistent formatting dan clear guidance

### 🎯 KEKUATAN SISTEM:
1. **Complete Functionality**: Semua alert management needs tercover
2. **Database Driven**: Persistent storage untuk user preferences
3. **Dynamic Control**: Runtime enable/disable tanpa restart
4. **Security First**: Whitelist protection dan audit logging
5. **User Friendly**: Clear messages, examples, dan guidance
6. **Service Integration**: Real-time whale monitoring integration

### 📋 RECOMMENDATIONS (Tanpa Kode Changes):
1. **Documentation**: Gunakan dokumen ini untuk user training
2. **Monitoring**: Monitor command usage patterns untuk insights
3. **User Education**: Edukasi user tentang workflow lengkap
4. **Service Health**: Regular check untuk `whale_watcher` service status

---

**Dokumentasi Dibuat:** 2025-12-10 12:35:00 UTC  
**Status Analisis:** ✅ **COMPLETE**  
**Coverage:** 6/6 alert-management commands  
**Rekomendasi:** Sistem sudah stabil dan production-ready
