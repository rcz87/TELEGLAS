# CONTOH PENGGUNAAN PRAKTIS ALERT MANAGEMENT COMMANDS
**Step-by-Step Examples dengan Hasil Aktual di Telegram**

---

## 📋 OVERVIEW

Dokumen ini memberikan contoh praktis bagaimana menggunakan 6 alert-management commands di TELEGLAS bot, lengkap dengan input yang harus diketik dan hasil yang akan muncul di Telegram.

**Commands yang Dibahas:**
1. `/subscribe` - Mulai berlangganan alert
2. `/unsubscribe` - Berhenti berlangganan alert  
3. `/alerts` - Lihat daftar berlangganan aktif
4. `/alerts_status` - Cek status sistem alert
5. `/alerts_on_w` - Aktifkan whale alerts
6. `/alerts_off_w` - Nonaktifkan whale alerts

---

## 🎯 COMMAND 1: `/subscribe`

### 📝 Cara Penggunaan:
```bash
/subscribe BTC
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ JIKA BERHASIL:
```
✅ SUBSCRIPTION SUCCESSFUL

You're now subscribed to all alerts for BTC:
• 🚨 Massive Liquidations (>$1M)
• 🐋 Whale Transactions (>$500,000)
• 💰 Extreme Funding Rates (±1%)

Use /alerts to manage your subscriptions.
```

#### ⚠️ JIKA TANPA SYMBOL:
```
❌ SYMBOL REQUIRED

Usage: /subscribe [SYMBOL]

Examples:
• /subscribe BTC
• /subscribe ETH
• /subscribe SOL
```

### 🎯 Tips Penggunaan:
- **Symbol harus huruf besar**: BTC, ETH, SOL (bukan btc, eth, sol)
- **Auto-subscribe semua tipe**: Liquidations, Whale, Funding
- **Bisa multiple simbol**: Subscribe untuk BTC, ETH, SOL secara terpisah

---

## 🎯 COMMAND 2: `/unsubscribe`

### 📝 Cara Penggunaan:
```bash
/unsubscribe BTC
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ JIKA BERHASIL:
```
✅ UNSUBSCRIBED SUCCESSFULLY

You've been unsubscribed from all alerts for BTC:
• 🚨 Massive Liquidations
• 🐋 Whale Transactions
• 💰 Extreme Funding Rates

💡 Use /alerts to view remaining subscriptions
💡 Use /subscribe SYMBOL to resubscribe
```

#### ❌ JIKA SYMBOL TIDAK ADA:
```
❌ UNSUBSCRIBE FAILED

You may not have an active subscription for this symbol.
```

#### ⚠️ JIKA TANPA SYMBOL:
```
❌ SYMBOL REQUIRED

Usage: /unsubscribe [SYMBOL]

Examples:
• /unsubscribe BTC
• /unsubscribe ETH
• /unsubscribe SOL
```

### 🎯 Tips Penggunaan:
- **Hapus semua tipe**: Unsubscribe akan menghapus liquidation, whale, dan funding alerts
- **Per simbol**: Unsubscribe BTC hanya berpengaruh ke BTC alerts
- **Bisa unsubscribe semua**: Lakukan untuk BTC, ETH, SOL satu per satu

---

## 🎯 COMMAND 3: `/alerts`

### 📝 Cara Penggunaan:
```bash
/alerts
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ JIKA ADA SUBSCRIPTION AKTIF:
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

#### 📭 JIKA TIDAK ADA SUBSCRIPTION:
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

### 🎯 Tips Penggunaan:
- **Cek status**: Lihat simbol apa yang sedang aktif
- **Tanggal berlangganan**: Tahu kapan mulai subscribe
- **Tipe alert per simbol**: Lihat jenis alert yang aktif
- **Guidance**: Dapat command management langsung dari sini

---

## 🎯 COMMAND 4: `/alerts_status`

### 📝 Cara Penggunaan:
```bash
/alerts_status
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ STATUS LENGKAP:
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

#### 🔄 STATUS DENGAN WHALE DISABLED:
```
🔔 ALERT SYSTEM STATUS

📊 REAL-TIME MONITORING:
🐋 Whale Alerts: 🔴 DISABLED
📢 Broadcast Alerts: 🟢 ENABLED
🔔 Your Subscriptions: 📊 2 active

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

### 🎯 Tips Penggunaan:
- **Cek aktif/non-aktif**: Status whale alerts (🟢/🔴)
- **Jumlah subscription**: Berapa simbol yang sedang aktif
- **Service status**: Lihat mana yang manual vs automatic
- **Real-time info**: Status generation timestamp

---

## 🎯 COMMAND 5: `/alerts_on_w`

### 📝 Cara Penggunaan:
```bash
/alerts_on_w
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ JIKA BERHASIL MENGAKTFIKAN:
```
🐋 WHALE ALERTS ENABLED

✅ Whale monitoring is now ACTIVE

🔔 You'll receive alerts for transactions >$500,000
⚡ Real-time monitoring from Hyperliquid
📊 Multi-coin whale detection

💡 Use /alerts_off_w to disable anytime
```

#### ⚠️ JIKA SERVICE UNAVAILABLE:
```
⚠️ SERVICE UNAVAILABLE

Whale monitoring service is currently unavailable.
Please try again in a few moments.
```

#### ⚠️ JIKA CONFIGURATION REQUIRED:
```
⚠️ SERVICE CONFIGURATION REQUIRED

Whale monitoring service is not properly configured.

Please check:
• Whale watcher service is running
• Hyperliquid API is accessible
• Alert system is initialized

Contact admin for assistance.
```

### 🎯 Tips Penggunaan:
- **Enable real-time**: Aktifkan notifikasi whale otomatis
- **Threshold**: Akan dapat alert untuk transaksi >$500,000
- **Multi-coin**: Monitor whale di semua simbol major
- **Bisa di-nonaktifkan**: Gunakan `/alerts_off_w` kapan saja

---

## 🎯 COMMAND 6: `/alerts_off_w`

### 📝 Cara Penggunaan:
```bash
/alerts_off_w
```

### 📤 Hasil yang Muncul di Telegram:

#### ✅ JIKA BERHASIL MENONAKTFIKAN:
```
🐋 WHALE ALERTS DISABLED

✅ Whale monitoring is now INACTIVE

🔔 You will NOT receive whale transaction alerts
📊 Manual whale checks still available via /whale
⚡ Real-time monitoring paused

💡 Use /alerts_on_w to re-enable anytime
```

#### ⚠️ JIKA SERVICE UNAVAILABLE:
```
⚠️ SERVICE UNAVAILABLE

Whale monitoring service is currently unavailable.
Please try again in a few moments.
```

#### ⚠️ JIKA CONFIGURATION REQUIRED:
```
⚠️ SERVICE CONFIGURATION REQUIRED

Whale monitoring service is not properly configured.

Please check:
• Whale watcher service is running
• Hyperliquid API is accessible
• Alert system is initialized

Contact admin for assistance.
```

### 🎯 Tips Penggunaan:
- **Pause monitoring**: Berhenti sementara notifikasi otomatis
- **Manual access tetap**: `/whale` command masih bisa digunakan
- **Flexibility**: Bisa on/off kapan saja tanpa restart bot
- **Data saving**: Tidak menerima notifikasi saat tidak perlu

---

## 🔄 WORKFLOW LENGKAP USER BARU

### 📋 Scenario: User Baru Ingin Setup Alerts

#### Step 1: Cek Status Awal
```bash
/alerts
```
**Expected Result:** 📭 No active subscriptions

#### Step 2: Subscribe ke Simbol Favorit
```bash
/subscribe BTC
```
**Expected Result:** ✅ Subscription successful

```bash
/subscribe ETH
```
**Expected Result:** ✅ Subscription successful

```bash
/subscribe SOL
```
**Expected Result:** ✅ Subscription successful

#### Step 3: Verifikasi Setup
```bash
/alerts
```
**Expected Result:** 🔔 Active subscriptions: 3 (BTC, ETH, SOL)

#### Step 4: Cek Status Sistem
```bash
/alerts_status
```
**Expected Result:** 🔔 System status dengan whale alerts status

#### Step 5: Aktifkan Whale Alerts (jika perlu)
```bash
/alerts_on_w
```
**Expected Result:** 🐋 Whale alerts enabled

#### Step 6: Monitoring & Management
```bash
/alerts
```
**Expected Result:** Daftar lengkap subscription aktif

### 📝 Hasil Akhir Workflow:
User akan memiliki:
- ✅ 3 simbol aktif (BTC, ETH, SOL)
- ✅ Semua tipe alert (liquidation, whale, funding)
- ✅ Whale alerts aktif untuk notifikasi real-time
- ✅ Clear overview status di `/alerts` dan `/alerts_status`

---

## 🎯 TROUBLESHOOTING COMMON SCENARIOS

### ❌ "Symbol Required" Error
**Problem:** Lupa menulis simbol
**Solution:** 
```bash
# SALAH
/subscribe

# BENAR
/subscribe BTC
```

### ❌ "Service Unavailable" Error
**Problem:** Whale watcher service sedang down
**Solution:** Tunggu beberapa menit, coba lagi:
```bash
/alerts_on_w
# Tunggu 1-2 menit
/alerts_on_w
```

### ❌ "Configuration Required" Error
**Problem:** Service tidak terkonfigurasi dengan benar
**Solution:** Contact admin, coba manual check:
```bash
/whale  # Masih bisa untuk cek manual
```

### 📭 Tidak Ada Subscriptions
**Problem:** User lupa sudah subscribe apa saja
**Solution:** Cek status:
```bash
/alerts  # Lihat daftar aktif
```

---

## 🎯 BEST PRACTICES

### ✅ Penggunaan Efektif:
1. **Start dengan `/alerts`** untuk lihat status saat ini
2. **Subscribe simbol major** (BTC, ETH, SOL) untuk coverage terbaik
3. **Cek `/alerts_status`** untuk verifikasi sistem aktif
4. **Gunakan `/alerts_on_w`** untuk aktifkan whale monitoring
5. **Regular check `/alerts`** untuk monitoring subscription

### 🛡️ Security Tips:
1. **Symbol format**: Selalu huruf besar (BTC, bukan btc)
2. **One command per message**: Tidak perlu spam command
3. **Verify dengan `/alerts`**: Pastikan subscription benar
4. **Contact admin**: Jika ada error berulang

### 📊 Monitoring Tips:
1. **Weekly check**: Gunakan `/alerts_status` untuk cek sistem
2. **Subscription audit**: Gunakan `/alerts` untuk review aktif
3. **Service health**: Perhatikan error messages untuk service issues
4. **Usage patterns**: Pantau simbol mana yang paling berguna

---

## 📞 QUICK REFERENCE CHEAT SHEET

| Command | Contoh Penggunaan | Fungsi |
|---------|-------------------|---------|
| `/subscribe BTC` | Tambah alert BTC | Subscribe ke semua alert types |
| `/unsubscribe ETH` | Hapus alert ETH | Unsubscribe semua alert ETH |
| `/alerts` | Lihat daftar aktif | Dashboard subscription |
| `/alerts_status` | Cek status sistem | Monitoring status keseluruhan |
| `/alerts_on_w` | Aktifkan whale | Enable whale monitoring |
| `/alerts_off_w` | Nonaktifkan whale | Disable whale monitoring |

---

## 🎯 KESIMPULAN

Dengan 6 alert-management commands ini, user dapat:
- ✅ **Mengontrol langganan** untuk simbol apapun
- ✅ **Monitoring real-time** untuk whale transactions
- ✅ **Manajemen status** sistem alert keseluruhan
- ✅ **Flexibilitas** untuk enable/disable kapan saja
- ✅ **Visibility lengkap** atas semua aktivitas alert

**Sistem TELEGLAS memberikan kontrol penuh kepada user untuk mengatur preferences alert sesuai kebutuhan trading masing-masing.**

---

**Dokumentasi Dibuat:** 2025-12-10 12:45:00 UTC  
**Tujuan:** Panduan praktis untuk penggunaan alert-management commands  
**Status:** ✅ Complete & Production-Ready
