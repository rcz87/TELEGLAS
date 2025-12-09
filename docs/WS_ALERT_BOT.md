# WS Alert Bot - Dokumentasi

## Overview

WS Alert Bot adalah bot kedua yang dikhususkan untuk alert otomatis, dipisahkan dari bot manual TELEGLAS utama. Bot ini dirancang untuk menangani semua jenis alert otomatis (whale, liquidation, funding, dll) tanpa mengganggu operasi bot manual.

## Arsitektur

### Bot Manual (TELEGLAS Utama)
- **Fungsi**: Command manual seperti `/raw`, `/liq`, `/whale`, dll
- **Entry Point**: `main.py`
- **Token**: `TELEGRAM_TOKEN`
- **Status**: TIDAK menjalankan auto whale alert lagi

### Bot Alert (WS Alert Bot)
- **Fungsi**: Alert otomatis (whale, liquidation, funding, future WebSocket alerts)
- **Entry Point**: `ws_alert/alert_runner.py`
- **Token**: `TELEGRAM_ALERT_TOKEN`
- **Status**: Menjalankan auto whale alert yang dipindahkan dari bot utama

## Struktur Modul

```
ws_alert/
├── __init__.py              # Modul initialization
├── config.py               # Konfigurasi khusus alert bot
├── telegram_alert_bot.py   # Telegram bot instance untuk alert
├── alert_engine.py         # Logika pemrosesan semua alert
├── alert_runner.py         # Entry point & orchestrator
└── ws_client.py           # WebSocket client untuk real-time data
```

### Penjelasan File

#### `config.py`
- Membaca `TELEGRAM_ALERT_TOKEN` dari environment
- Konfigurasi default chat_id/channel_id untuk testing
- Settings untuk enable/disable berbagai jenis alert
- WebSocket API key configuration

#### `telegram_alert_bot.py`
- Inisialisasi bot Telegram dengan token khusus
- Fungsi `send_alert_text()` untuk pengiriman pesan
- Fungsi `process_alert_event()` untuk WebSocket integration
- Tidak ada handler command manual (pure sender/producer)

#### `alert_engine.py`
- Menampung logika bisnis semua jenis alert
- Logika whale alert yang dipindahkan dari `services/whale_watcher.py`
- WebSocket event handlers (liquidation, futures trades)
- Placeholder untuk future alert types (funding, OI)
- Shared methods untuk bot utama jika perlu akses data

#### `alert_runner.py`
- Entry point untuk menjalankan WS Alert Bot
- Menghubungkan alert_engine dengan telegram_alert_bot
- WebSocket client initialization dan event routing
- Test alert saat startup untuk verifikasi
- Main loop untuk WebSocket event consumption

#### `ws_client.py` (NEW)
- WebSocket client untuk CoinGlass real-time API
- Auto-reconnect dengan exponential backoff
- Ping/pong mechanism untuk connection health
- Channel subscriptions (liquidationOrders, futures_trades)
- Event listener dengan callback functions

## Konfigurasi Environment

### Variabel yang Dibutuhkan

```bash
# Token untuk bot alert (berbeda dari bot manual)
TELEGRAM_ALERT_TOKEN=PASTE_YOUR_ALERT_BOT_TOKEN_HERE

# WebSocket API key untuk real-time data
COINGLASS_API_KEY_WS=YOUR_KEY_HERE

# Konfigurasi existing (tetap digunakan)
TELEGRAM_TOKEN=YOUR_MAIN_BOT_TOKEN  # Bot manual
ENABLE_WHALE_ALERTS=true
```

### Setup Token

1. Buat bot baru melalui @BotFather di Telegram
2. Dapatkan token bot baru
3. Set ke `TELEGRAM_ALERT_TOKEN` di `.env`
4. Tambahkan bot ke channel/chat yang sama jika perlu
5. Dapatkan CoinGlass WebSocket API key dan set ke `COINGLASS_API_KEY_WS`

## Cara Menjalankan

### 1. Bot Manual (Existing)
```bash
# Bot manual tetap jalan seperti biasa
python main.py
```

### 2. Bot Alert (Baru) - Stage 2 dengan WebSocket
```bash
# Method 1: Direct run dengan WebSocket
python ws_alert/alert_runner.py

# Method 2: Module run
python -m ws_alert.alert_runner

# Method 3: Dengan virtual environment
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows
python ws_alert/alert_runner.py
```

### 3. Running Both Bots
```bash
# Terminal 1 - Bot Manual
python main.py

# Terminal 2 - Bot Alert dengan WebSocket
python ws_alert/alert_runner.py
```

## Stage 2: Real-Time WebSocket Integration

### Overview

Stage 2 mengimplementasikan WebSocket client untuk real-time data dari CoinGlass API, memungkinkan alert yang lebih cepat dan responsif.

### WebSocket Client Features

#### Connection Management
- **Auto-Reconnect**: Exponential backoff (2s, 4s, 8s, max 60s)
- **Connection Health**: Ping setiap 20 detik dengan pong timeout detection
- **Graceful Shutdown**: Signal handlers untuk SIGINT/SIGTERM
- **Error Handling**: Comprehensive error recovery dan logging

#### Channel Subscriptions
```python
# Default channels yang di-subscribe
DEFAULT_CHANNELS = [
    "liquidationOrders",                    # Semua liquidation events
    "futures_trades@Binance_BTCUSDT@10000",  # BTC trades >$10K
]
```

#### Event Types
1. **Liquidation Events** (`liquidationOrders`)
   - Real-time liquidation data
   - Multi-exchange coverage
   - Price, size, side information

2. **Futures Trade Events** (`futures_trades`)
   - Large transactions monitoring
   - Configurable USD thresholds
   - Exchange-specific channels

### WebSocket Event Flow

```
CoinGlass WebSocket → ws_client.py → alert_runner.py → alert_engine.py → telegram_alert_bot.py → Telegram
```

#### Event Processing
1. **Connection**: WebSocket client connects ke CoinGlass
2. **Subscription**: Auto-subscribe ke default channels
3. **Event Reception**: Messages diterima dan diparsing
4. **Routing**: Events di-redirect ke appropriate handlers
5. **Processing**: Alert logic applied (thresholds, filtering)
6. **Broadcast**: Alerts dikirim ke Telegram channels

### Alert Message Formats

#### Liquidation Alert
```
🔥 LIQUIDATION ALERT
📍 Exchange: Binance
📊 Symbol: BTCUSDT
💰 Price: $56,738.00
📉 Side: SHORT
💵 Size: $1,250,000
⏰ Time: 19:30:45
```

#### Whale Trade Alert
```
🐋 WHALE TRADE ALERT
📍 Exchange: Binance
📊 Symbol: BTCUSDT
💰 Price: $56,750.00
📈 Side: BUY
💵 Size: $2,500,000
⏰ Time: 19:31:12
```

### WebSocket Configuration

#### URL Format
```
wss://open-ws.coinglass.com/ws-api?cg-api-key={COINGLASS_API_KEY_WS}
```

#### Connection Parameters
- **Timeout**: 30 seconds untuk initial connection
- **Ping Interval**: 20 seconds
- **Max Message Size**: 10MB
- **Close Timeout**: 10 seconds

#### Subscription Format
```json
{
  "op": "subscribe",
  "args": ["liquidationOrders", "futures_trades@Binance_BTCUSDT@10000"]
}
```

## Migrasi Whale Alert

### Yang Dipindahkan ke WS Alert Bot
- ✅ Auto whale monitoring loop (polling mode)
- ✅ Real-time WebSocket whale detection
- ✅ Whale transaction detection dan filtering
- ✅ Whale signal analysis dengan confidence scoring
- ✅ Automatic alert broadcasting
- ✅ Debounce logic untuk mencegah spam
- ✅ Session management dan error handling

### Yang Tetap di Bot Manual
- ✅ Command `/whale` (manual trigger)
- ✅ Command manual lainnya (`/raw`, `/liq`, dll)
- ✅ Fungsi shared dari `alert_engine` jika needed

### Perubahan di Bot Manual
```python
# Sebelumnya: Auto whale monitoring dijalankan
if settings.ENABLE_WHALE_ALERTS:
    task = asyncio.create_task(whale_watcher.start_monitoring())

# Sekarang: Info bahwa auto whale monitoring pindah
logger.info("[INFO] Auto whale monitoring moved to WS Alert Bot")
logger.info("[INFO] To enable auto whale alerts: python -m ws_alert.alert_runner")
```

## WebSocket Event Handlers

### Liquidation Event Handler
```python
async def handle_liquidation_event(event: Dict[str, Any]):
    """Process real-time liquidation events"""
    # Extract data: symbol, exchange, price, side, volume
    # Apply threshold filtering
    # Format alert message
    # Send to all configured chat IDs
```

### Futures Trade Event Handler
```python
async def handle_futures_trade_event(event: Dict[str, Any]):
    """Process real-time whale trade events"""
    # Extract trade data
    # Filter by USD threshold
    # Send whale alerts for significant trades
```

## Testing & Verifikasi

### 1. Test WebSocket Connection
```bash
python ws_alert/alert_runner.py
```
Expected output:
- ✅ WebSocket client initialization
- ✅ Connection to CoinGlass WebSocket
- ✅ Channel subscription confirmations
- ✅ Startup message sent to Telegram

### 2. Test Real-Time Events
- **Liquidation**: Monitor Telegram untuk liquidation alerts real-time
- **Whale Trades**: Large transactions akan trigger instant alerts
- **Connection Stability**: Test auto-reconnect dengan network interruption

### 3. Test Fallback Mode
Jika WebSocket API key tidak dikonfigurasi:
- ✅ Automatic fallback ke polling mode
- ✅ Traditional whale monitoring tetap berjalan
- ✅ Startup message indicating fallback mode

### 4. Test Bot Manual
```bash
python main.py
```
Expected:
- ✅ Auto whale monitoring disabled info
- ✅ Manual commands still available
- ✅ No auto whale tasks started

## Performance & Reliability

### WebSocket Benefits
- **Latency**: Real-time alerts vs polling delays
- **Efficiency**: Push-based vs pull-based data
- **Scalability**: Multiple channels dalam single connection
- **Resource Usage**: Lower API call frequency

### Reliability Features
- **Auto-Reconnect**: Exponential backoff untuk network issues
- **Health Monitoring**: Continuous ping/pong checks
- **Error Recovery**: Graceful handling dari berbagai error scenarios
- **Fallback Mode**: Polling mode jika WebSocket unavailable

### Rate Limiting & Debounce
- **WebSocket**: Native rate limiting oleh server
- **Application**: Custom debounce logic per symbol
- **Telegram**: Rate limiting per bot token

## Troubleshooting

### WebSocket Specific Issues

#### 1. Connection Failed
```
[WS_CLIENT] ❌ Connection failed: Invalid API key
```
**Solusi**: 
- Verifikasi `COINGLASS_API_KEY_WS` di `.env`
- Pastikan API key valid dan aktif

#### 2. Subscription Failed
```
[WS_CLIENT] ❌ Subscribe failed: Channel not found
```
**Solusi**:
- Check channel name format
- Verifikasi API permissions untuk channel tersebut

#### 3. Connection Drops
```
[WS_CLIENT] ⚠️ Connection closed: 1006
```
**Solusi**:
- Auto-reconnect akan menangani
- Check network stability
- Monitor logs untuk reconnect patterns

#### 4. No Events Received
```
[WS_CLIENT] 🎧 Starting message listener... (tapi tidak ada events)
```
**Solusi**:
- Verify channel subscriptions
- Check API key permissions
- Test dengan different channels

### Common Issues (Existing)

#### 1. Token Error
```
Error: Invalid token
```
**Solusi**: Pastikan `TELEGRAM_ALERT_TOKEN` valid dan berbeda dari `TELEGRAM_TOKEN`

#### 2. Bot Not Receiving Messages
```
Warning: Failed to send alert
```
**Solusi**: 
- Pastikan bot ditambahkan ke channel/chat
- Check bot permissions
- Verifikasi chat_id configuration

#### 3. Import Errors
```
ModuleNotFoundError: No module named 'ws_alert'
```
**Solusi**: Jalankan dari root directory atau gunakan `python -m ws_alert.alert_runner`

#### 4. Missing Dependencies
```
ImportError: Required packages missing: pip install websockets aiohttp
```
**Solusi**: Install required packages
```bash
pip install websockets aiohttp
```

### Debug Commands

#### Check WebSocket Configuration
```python
import os
print("WS_API_KEY:", os.getenv("COINGLASS_API_KEY_WS"))
print("ALERT_TOKEN:", os.getenv("TELEGRAM_ALERT_TOKEN"))
```

#### Test WebSocket Connection
```python
from ws_alert.ws_client import CoinGlassWebSocketClient
import asyncio

async def test_ws():
    client = CoinGlassWebSocketClient()
    if await client.connect_ws():
        print("✅ WebSocket connection successful")
    else:
        print("❌ WebSocket connection failed")

asyncio.run(test_ws())
```

#### Check Alert Engine
```python
from ws_alert.alert_engine import alert_engine, handle_liquidation_event
# Test event handlers
```

## Logging

### WebSocket Client Logs
- Prefix: `[WS_CLIENT]`
- Connection status, subscription confirmations, event processing
- Error handling dan reconnect attempts

### Alert Engine Logs
- Prefix: `[ALERT_ENGINE]`
- Event processing, alert generation, handler registration
- WebSocket event routing information

### Runner Logs
- Prefix: `[RUNNER]`
- Initialization, startup/shutdown events
- Component coordination status

## Deployment

### Development
```bash
# Run both bots separately for development
python main.py &                    # Bot manual
python ws_alert/alert_runner.py &   # Bot alert dengan WebSocket
```

### Production (Systemd) - WebSocket Enabled
```ini
# /etc/systemd/system/telelas-manual.service
[Unit]
Description=TELEGLAS Manual Bot
After=network.target

[Service]
Type=simple
User=telelas
WorkingDirectory=/opt/telelas
ExecStart=/opt/telelas/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/telelas-alert.service
[Unit]
Description=TELEGLAS Alert Bot with WebSocket
After=network.target

[Service]
Type=simple
User=telelas
WorkingDirectory=/opt/telelas
Environment=COINGLASS_API_KEY_WS=your_production_key
ExecStart=/opt/telelas/venv/bin/python ws_alert/alert_runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Production (Docker) - WebSocket
```dockerfile
# Multi-stage build untuk kedua bots
FROM python:3.11-slim

# Install dependencies including WebSocket packages
COPY requirements.txt .
RUN pip install -r requirements.txt websockets aiohttp

# Copy application
COPY . .

# Environment variables untuk WebSocket
ENV COINGLASS_API_KEY_WS=${COINGLASS_API_KEY_WS}
ENV TELEGRAM_ALERT_TOKEN=${TELEGRAM_ALERT_TOKEN}

# CMD untuk bot manual (default)
CMD ["python", "main.py"]

# Atau gunakan docker-compose untuk kedua bots
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  telelas-manual:
    build: .
    command: python main.py
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
    
  telelas-alert:
    build: .
    command: python ws_alert/alert_runner.py
    environment:
      - TELEGRAM_ALERT_TOKEN=${TELEGRAM_ALERT_TOKEN}
      - COINGLASS_API_KEY_WS=${COINGLASS_API_KEY_WS}
```

## Security Considerations

### WebSocket Security
- ✅ API key stored in environment variables
- ✅ Secure WebSocket (wss://) connection
- ✅ Connection timeout dan validation
- ✅ Error handling tanpa exposing sensitive data

### Token Management
- ✅ Token terpisah untuk masing-masing bot
- ✅ Different permission sets jika needed
- ✅ Separate rate limiting per bot

### Access Control
- ✅ Bot alert bisa dibatasi ke channel tertentu
- ✅ Bot manual tetap dengan auth yang existing
- ✅ Tidak ada shared state antar bots

## Monitoring & Maintenance

### WebSocket Health Monitoring
```python
# Monitor connection status
client.is_connected  # Boolean
client.reconnect_attempts  # Integer
client.last_pong_time  # Timestamp
```

### Metrics
- WebSocket connection uptime
- Event processing latency
- Alert frequency per channel
- Reconnect success rate
- Error rates dan types

### Health Checks
```python
# Bot manual health
curl http://localhost:8080/health

# Bot alert health dengan WebSocket status
curl http://localhost:8081/health
```

### Backup & Recovery
- Configuration backup (.env dengan WebSocket keys)
- Log rotation untuk WebSocket events
- State persistence untuk connection status

## Future Enhancements

### Stage 3 Potential Features
1. **Additional Channels**: Open interest, funding rates
2. **Custom Filtering**: User-defined thresholds per symbol
3. **Alert Aggregation**: Group similar alerts dalam time windows
4. **Dashboard**: Real-time web interface
5. **Analytics**: Alert performance insights
6. **Multi-Exchange**: Support untuk lebih banyak exchanges

### WebSocket Optimizations
1. **Connection Pooling**: Multiple connections untuk load balancing
2. **Event Buffering**: Buffer events untuk batch processing
3. **Smart Filtering**: Server-side filtering untuk reduce bandwidth
4. **Compression**: Message compression untuk high-frequency data

## FAQ

### Q: Apa keuntungan WebSocket vs polling?
A: WebSocket memberikan real-time data dengan latency lebih rendah, lebih efisien secara bandwidth, dan bisa menangani multiple channels dalam single connection.

### Q: Bagaimana jika WebSocket connection putus?
A: Auto-reconnect dengan exponential backoff akan otomatis mencoba koneksi kembali dengan delay yang bertahap.

### Q: Apakah bot alert masih berjalan tanpa WebSocket?
A: Ya, ada fallback mode ke polling traditional jika WebSocket API key tidak dikonfigurasi.

### Q: Berapa latency improvement vs polling?
A: WebSocket bisa mengurangi latency dari 30-60 seconds (polling interval) menjadi sub-second untuk real-time events.

### Q: Bagaimana dengan rate limiting?
A: WebSocket memiliki rate limiting yang lebih baik daripada polling, dan setiap bot memiliki rate limiting terpisah.

## Summary

Stage 2 WebSocket Integration menyediakan:
- ✅ Real-time alert delivery
- ✅ Improved latency dan efficiency
- ✅ Auto-reconnect reliability
- ✅ Fallback mode compatibility
- ✅ Enhanced monitoring capabilities
- ✅ Production-ready deployment options

---

**Last Updated**: 2025-12-08
**Version**: 2.0.0 (Stage 2 WebSocket Integration)
**Compatibility**: TELEGLAS v2.x+
**Dependencies**: `websockets`, `aiohttp` (additional for WebSocket)
