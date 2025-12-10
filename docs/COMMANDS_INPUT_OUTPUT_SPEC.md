# TELEGLAS BOT COMMANDS INPUT/OUTPUT SPECIFICATION
**Phase 2 - Input/Output Analysis & Requirements**

## 📋 Executive Summary

Dokumen ini mendefinisikan spesifikasi input, output, dan error handling untuk setiap command di bot TELEGLAS. Analisis ini mengidentifikasi kebutuhan parameter, format output, dan area yang perlu perbaikan.

---

## 🗂️ Command Specifications

### 1. /start

**Deskripsi:**
Menampilkan welcome message dan main menu keyboard untuk user baru.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/start` atau `/start@botname`

**Output:**
- **Format:** Markdown + ReplyKeyboardMarkup
- **Sections:**
  - Welcome message dengan username
  - Bot description
  - Command list dengan examples
  - Real-time monitoring status
  - Inline keyboard buttons

**Error Handling:**
- ✅ **Ada:** Access control via `@require_access`
- ✅ **Ada:** User identification check
- ⚠️ **Note:** Tidak ada validasi khusus (command tidak butuh parameter)

**UX Score:** Good
**Catatan:** Command ini well-structured dengan jelas instructions.

---

### 2. /help

**Deskripsi:**
Menampilkan help documentation dan daftar lengkap command.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/help`

**Output:**
- **Format:** Markdown
- **Sections:**
  - Command categories
  - Detailed usage examples
  - Alert thresholds information
  - Update frequency info

**Error Handling:**
- ✅ **Ada:** Access control via `@require_access`
- ⚠️ **Note:** Tidak ada validasi khusus (command tidak butuh parameter)

**UX Score:** Good
**Catatan:** Help message comprehensive dengan examples.

---

### 3. /raw

**Deskripsi:**
Menampilkan comprehensive market data multi-timeframe untuk satu symbol.

**Input:**
- **Required:** Symbol (string)
- **Optional:** None
- **Format:** `/raw <SYMBOL>`
- **Valid Examples:** `/raw BTC`, `/raw ETH`, `/raw SOL`
- **Invalid Examples:** `/raw` (tanpa symbol), `/raw ` (kosong)

**Output:**
- **Format:** Plain text (no Markdown)
- **Length:** Potentially very long (~2000-3000 chars)
- **Sections:**
  - Info Umum (symbol, timeframe, timestamp)
  - Price Change multi-timeframe
  - Open Interest total dan per exchange
  - Volume data
  - Funding rates dengan history
  - Liquidations data
  - Long/Short ratios
  - Taker Flow multi-timeframe
  - RSI (1h/4h/1d)
  - CG Levels (support/resistance)
  - Orderbook snapshot

**Error Handling:**
- ✅ **Ada:** Parameter validation (symbol required)
- ✅ **Ada:** Symbol not supported handling
- ✅ **Ada:** Service error handling
- ✅ **Ada:** API timeout handling
- ⚠️ **Issue:** Error message dalam bahasa Indonesia, tapi help dalam bahasa Inggris

**UX Score:** Needs Improvement
**Catatan:** 
- Output terlalu panjang untuk mobile (risk kena Telegram limit)
- Inconsistent language (error Bahasa, help English)
- Need pagination atau summary version

---

### 4. /raw_orderbook

**Deskripsi:**
Menampilkan orderbook depth analysis dan imbalance data.

**Input:**
- **Required:** Symbol (string)
- **Optional:** Exchange (default: Binance)
- **Format:** `/raw_orderbook <SYMBOL>`
- **Valid Examples:** `/raw_orderbook BTC`, `/raw_orderbook SOL`
- **Invalid Examples:** `/raw_orderbook` (tanpa symbol)

**Output:**
- **Format:** Plain text
- **Sections:**
  - Info Umum (exchange, symbol, interval)
  - Snapshot Orderbook (Level Price - History 1H)
  - Binance Orderbook Depth (1D)
  - Aggregated Orderbook Depth (Multi-Exchange 1H)
  - TL;DR Orderbook Bias summary

**Error Handling:**
- ✅ **Ada:** Parameter validation
- ✅ **Ada:** Data availability check
- ✅ **Ada:** Symbol not supported fallback
- ✅ **Ada:** User-friendly error message dengan alternatives
- ⚠️ **Issue:** Fallback message masih panjang

**UX Score:** Good
**Catatan:** Well-structured dengan clear fallback ke `/raw` command.

---

### 5. /liq

**Deskripsi:**
Menampilkan liquidation data untuk specific coin dalam 24 jam.

**Input:**
- **Required:** Symbol (string)
- **Optional:** None
- **Format:** `/liq <SYMBOL>`
- **Valid Examples:** `/liq BTC`, `/liq ETH`
- **Invalid Examples:** `/liq` (tanpa symbol)

**Output:**
- **Format:** Plain text
- **Sections:**
  - Header: LIQUIDATION RADAR – SYMBOL (24H)
  - Ringkasan (Total, Long, Short, L/S Ratio)
  - Market Context (Price 24H, Volume 24H, Data Source)
  - Interpretasi Cepat (analysis dari dominant side)
  - TL;DR (bias direction dan setup advice)

**Error Handling:**
- ✅ **Ada:** Parameter validation dengan jelas usage example
- ✅ **Ada:** Service error handling
- ✅ **Ada:** User-friendly error messages
- ⚠️ **Issue:** Mixed language (error English, output Bahasa)

**UX Score:** Needs Improvement
**Catatan:** Output dalam Bahasa Indonesia tapi error messages dalam Bahasa Inggris.

---

### 6. /sentiment

**Deskripsi:**
Menampilkan market sentiment analysis dari multiple sources.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/sentiment`

**Output:**
- **Format:** Markdown
- **Sections:**
  - Fear & Greed Index (jika available)
  - Market Trend analysis
  - Funding Sentiment
  - OI Trend
  - L/S Ratio sentiment
  - Data sources info

**Error Handling:**
- ✅ **Ada:** Multiple fallback mechanisms
- ✅ **Ada:** Graceful degradation (partial data OK)
- ✅ **Ada:** Service unavailable handling
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Good
**Catatan:** Robust fallback system, good error handling.

---

### 7. /whale

**Deskripsi:**
Menampilkan recent whale transactions dari Hyperliquid.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/whale`

**Output:**
- **Format:** Plain text
- **Length:** Potentially long (dipotong jika >4000 chars)
- **Sections:**
  - Header: WHALE RADAR – HYPERLIQUID
  - Top 3 Paling Panas (Notional)
  - Ringkasan Aktivitas (top 7 symbols)
  - Sample Transaksi Terbaru (5 trades)
  - Interpretasi Cepat (BTC/ETH analysis)
  - TL;DR (focus summary)

**Error Handling:**
- ✅ **Ada:** Service error handling
- ✅ **Ada:** No data handling
- ✅ **Ada:** Message length handling (auto-chunk)
- ⚠️ **Note:** Tidak ada parameter validation

**UX Score:** Good
**Catatan:** Auto-chunking untuk long messages adalah good feature.

---

### 8. /subscribe

**Deskripsi:**
Subscribe user ke alerts untuk specific symbol.

**Input:**
- **Required:** Symbol (string) - TAPI dianggap optional di code
- **Optional:** None
- **Format:** `/subscribe [SYMBOL]`
- **Valid Examples:** `/subscribe BTC`, `/subscribe ETH`
- **Edge Case:** `/subscribe` (tanpa symbol) → menampilkan inline keyboard

**Output:**
**Dengan Symbol:**
- Success/failure message
- Alert types yang di-subscribe
- Threshold information

**Tanpa Symbol:**
- Inline keyboard dengan alert type selection
- Default symbol BTC

**Error Handling:**
- ⚠️ **Issue:** Parameter validation tidak konsisten
- ✅ **Ada:** Database error handling
- ✅ **Ada:** Success/failure feedback

**UX Score:** Needs Improvement
**Catatan:** 
- Parameter validation inconsistent (code anggap optional tapi help bilang required)
- Inline keyboard approach good tapi confusing flow

---

### 9. /unsubscribe

**Deskripsi:**
Unsubscribe user dari alerts untuk specific symbol.

**Input:**
- **Required:** Symbol (string)
- **Optional:** None
- **Format:** `/unsubscribe <SYMBOL>`
- **Valid Examples:** `/unsubscribe BTC`, `/unsubscribe ETH`
- **Invalid Examples:** `/unsubscribe` (tanpa symbol)

**Output:**
- Success/failure message
- Confirmation unsubscription details

**Error Handling:**
- ✅ **Ada:** Parameter validation dengan usage example
- ✅ **Ada:** Database error handling
- ✅ **Ada:** Non-existent subscription handling

**UX Score:** Good
**Catatan:** Clear parameter validation dan error messages.

---

### 10. /alerts

**Deskripsi:**
Menampilkan daftar alert subscriptions aktif untuk user.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/alerts`

**Output:**
- **Format:** Markdown
- **Sections:**
  - Header dengan jumlah subscriptions
  - List per symbol: alert types, subscription date
  - No subscriptions message dengan guidance

**Error Handling:**
- ✅ **Ada:** Database error handling
- ✅ **Ada:** Empty list handling
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Good
**Catatan:** Clear formatting dan helpful empty state message.

---

### 11. /status

**Deskripsi:**
Menampilkan bot status dan performance metrics.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/status`

**Output:**
- **Format:** Markdown
- **Sections:**
  - System operational status
  - Monitoring services status
  - Performance metrics (polling intervals)
  - API rate limit info
  - Security status

**Error Handling:**
- ⚠️ **Note:** Tidak ada error handling spesifik (static data)
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Good
**Catatan:** Static information, reliable display.

---

### 12. /alerts_status

**Deskripsi:**
Menampilkan status alert system (ON/OFF).

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/alerts_status`

**Output:**
- **Format:** Markdown
- **Sections:**
  - Whale alerts status
  - Broadcast alerts status
  - Manual only modules list
  - Control commands reference

**Error Handling:**
- ⚠️ **Note:** Static status dari config, tidak ada error handling
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Good
**Catatan:** Informative tapi status bisa jadi outdated jika config berubah.

---

### 13. /alerts_on_w

**Deskripsi:**
Turn ON whale alerts.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/alerts_on_w`

**Output:**
- **Format:** Markdown
- **Scenarios:**
  - Already enabled: confirmation message
  - Disabled: configuration required instructions

**Error Handling:**
- ✅ **Ada:** Configuration check
- ✅ **Ada:** User guidance for manual config change
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Needs Improvement
**Catatan:** Tidak bisa dinamis change, harus manual config edit.

---

### 14. /alerts_off_w

**Deskripsi:**
Turn OFF whale alerts.

**Input:**
- **Required:** None
- **Optional:** None
- **Format:** `/alerts_off_w`

**Output:**
- **Format:** Markdown
- **Scenarios:**
  - Already disabled: confirmation message
  - Enabled: configuration required instructions

**Error Handling:**
- ✅ **Ada:** Configuration check
- ✅ **Ada:** User guidance for manual config change
- ⚠️ **Note:** Tidak ada parameter validation (tidak perlu)

**UX Score:** Needs Improvement
**Catatan:** Sama seperti `/alerts_on_w`, butuh manual config change.

---

## 🔍 Cross-Cutting Issues Analysis

### 1. Language Inconsistency
**Commands dengan mixed languages:**
- `/liq`, `/raw_orderbook`, `/whale`: Output Bahasa Indonesia
- Error messages: Bahasa Inggris
- `/help`, `/status`, dll: Bahasa Inggris

**Recommendation:** Standardize ke Bahasa Inggris atau Bahasa Indonesia.

### 2. Parameter Validation Patterns
**Good Examples:**
- `/unsubscribe`, `/liq`, `/raw_orderbook`: Clear validation dengan usage examples
- Error messages helpful

**Needs Improvement:**
- `/subscribe`: Inconsistent parameter handling
- `/raw`: Basic validation tapi error message language mismatch

### 3. Output Length Management
**Problematic Commands:**
- `/raw`: Very long output (2000-3000 chars)
- `/whale`: Potentially long (tapi ada auto-chunk)

**Good Examples:**
- `/liq`: Well-structured, reasonable length
- `/raw_orderbook`: Well-organized sections

### 4. Error Handling Quality
**Excellent:**
- `/sentiment`: Multiple fallback mechanisms
- `/raw_orderbook`: Graceful degradation with alternatives
- `/raw`: Comprehensive error handling

**Needs Work:**
- `/alerts_on_w` / `/alerts_off_w`: Limited functionality
- `/subscribe`: Confusing parameter logic

### 5. Data Source Consistency
**Multi-Exchange Aggregated:**
- `/raw`: Full multi-exchange data
- `/liq`: Multi-exchange liquidation
- `/raw_orderbook`: Binance + aggregated depth

**Single Source:**
- `/whale`: Hyperliquid only
- `/sentiment`: Mixed sources (Fear & Greed, CoinGlass)

---

## 📊 Command Quality Summary

| Command | Parameter Validation | Error Handling | Output Quality | Language Consistency | Overall Score |
|---------|-------------------|----------------|---------------|-------------------|---------------|
| `/start` | N/A | Good | Good | English | ✅ Good |
| `/help` | N/A | Good | Good | English | ✅ Good |
| `/raw` | Basic | Excellent | Too Long | Mixed | ⚠️ Needs Work |
| `/raw_orderbook` | Good | Excellent | Good | Mixed | ✅ Good |
| `/liq` | Good | Good | Good | Mixed | ⚠️ Needs Work |
| `/sentiment` | N/A | Excellent | Good | English | ✅ Good |
| `/whale` | N/A | Good | Good | Mixed | ⚠️ Needs Work |
| `/subscribe` | Confusing | Good | Good | English | ⚠️ Needs Work |
| `/unsubscribe` | Good | Good | Good | English | ✅ Good |
| `/alerts` | N/A | Good | Good | English | ✅ Good |
| `/status` | N/A | Basic | Good | English | ✅ Good |
| `/alerts_status` | N/A | Basic | Good | English | ✅ Good |
| `/alerts_on_w` | N/A | Good | Good | English | ⚠️ Needs Work |
| `/alerts_off_w` | N/A | Good | Good | English | ⚠️ Needs Work |

---

## 🎯 Priority Improvements for Phase 3

### High Priority
1. **Standardize Language** - Pilih Bahasa Inggris atau Indonesia
2. **Fix /raw Output Length** - Add pagination atau summary
3. **Fix /subscribe Parameter Logic** - Clear required/optional handling
4. **Add Dynamic Alert Control** - Remove need for manual config edits

### Medium Priority
1. **Improve Error Message Consistency** - Standardize format dan language
2. **Add Output Format Options** - Compact vs detailed modes
3. **Enhanced Parameter Validation** - More specific error messages

---

**Report Generated:** 2025-12-10 10:47:00 UTC  
**Commands Analyzed:** 15 commands  
**Files Reviewed:** `handlers/telegram_bot.py`, `handlers/raw_orderbook.py`, `utils/message_builders.py`
