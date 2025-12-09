# Analisis Lengkap WebSocket Alert System - TELEGLAS

## Overview

Analisis ini menyajikan pemahaman menyeluruh tentang semua jenis alert yang dihasilkan melalui data WebSocket dalam implementasi TELEGLAS, termasuk sumber data, format output, dan frekuensi pemicu setiap alert.

---

## 📡 Sumber Data WebSocket

### Primary Provider: CoinGlass WebSocket API
- **Endpoint**: `wss://open-ws.coinglass.com/ws-api`
- **Authentication**: API Key via query parameter `cg-api-key`
- **Connection Management**: Auto-reconnect dengan exponential backoff
- **Ping/Pong**: Adaptive interval (10-120 seconds) berdasarkan kualitas koneksi

### WebSocket Channels yang Dimonitor
1. **`liquidationOrders`** - Real-time liquidation events
2. **`futures_trades@{exchange}@{symbol}@{usd_threshold}`** - Large whale trades

---

## 🚨 Jenis Alert dan Analisis Detail

### 1. Large Liquidation Alert

**Kanal WebSocket**: `liquidationOrders`

**Format Output**:
```
🔥 **Liquidation Alert – BTCUSDT**

Exchange   : Binance
Direction  : Long liq 📉
Nominal    : $850K
Harga      : $67,234.50
Waktu      : 2025-01-08 14:32:15 UTC

📊 *Details*:
• Kelompok: MAJORS
• Threshold: $500K
• Event ini melewati volume filter

#liquidation #BTC
```

**Threshold per Symbol Group**:
- **MAJORS** (BTC, ETH, SOL): $500K
- **LARGE_CAP** (BNB, XRP, ADA, DOGE, AVAX, DOT): $200K  
- **MID_CAP** (others): $100K

**Frekuensi Pemicu**:
- **Per Event**: Setiap liquidation yang melewati threshold
- **Cooldown**: 5 menit per symbol per direction (Long/Short)
- **Anti-spam**: Tidak mengirim alert yang sama dalam cooldown period

**Filtering Logic**:
```python
if vol_usd >= threshold AND not in_cooldown:
    send_alert()
    update_cooldown(symbol, alert_type)
```

---

### 2. Whale Trade Alert

**Kanal WebSocket**: `futures_trades@{exchange}@{symbol}@{usd_threshold}`

**Format Output**:
```
🐋 **Whale Trade – BTCUSDT**

Exchange   : Binance
Direction  : BUY 📈
Nominal    : $1.2M
Harga      : $67,234.50
Channel    : futures_trades@Binance_BTCUSDT@10000
Waktu      : 2025-01-08 14:32:15 UTC

📊 *Details*:
• Kelompok: MAJORS
• Di atas threshold: $1M

#whale #BTC
```

**Threshold per Symbol Group**:
- **MAJORS**: $1M minimum
- **LARGE_CAP**: $500K minimum
- **MID_CAP**: $200K minimum

**Frekuensi Pemicu**:
- **Per Event**: Setiap whale trade yang melewati threshold
- **Cooldown**: 5 menit per symbol per direction (Buy/Sell)
- **Real-time**: Langsung dari WebSocket feed

**Multi-Exchange Support**:
- Binance, Bybit, OKX, dan exchanges lainnya
- Dynamic channel subscription per exchange
- Exchange-specific normalization

---

### 3. Liquidation Storm Alert

**Kanal WebSocket**: `liquidationOrders` (via aggregation)

**Format Output**:
```
⚠️ **LIQUIDATION STORM – BTCUSDT**

Side        : Long Liquidations 📉
Total USD   : $2.5M
Events      : 8 in 30 sec
Note        : Possible capitulation / reversal zone

📊 *Storm Analysis*:
• Accumulated liquidations detected
• High volatility period
• Market stress indicator

#liquidation_storm #BTC #storm
```

**Storm Detection Logic**:
```python
# 30-second window analysis
liquidation_events = get_last_30_seconds(symbol)
group_by_side = long_vs_short_liquidations

if total_volume >= threshold AND event_count >= min_events:
    trigger_storm_alert()
```

**Threshold per Symbol Group**:
- **MAJORS**: $2M total volume, 3+ events
- **LARGE_CAP**: $1M total volume, 2+ events
- **MID_CAP**: $500K total volume, 2+ events

**Frekuensi Pemicu**:
- **Pattern-based**: Setiap terdeteksi pattern dalam 30-second window
- **Cooldown**: 5 menit per symbol
- **Detection Loop**: Setiap 5 detik scan semua active symbols
- **Window Analysis**: 30 detik rolling window

---

### 4. Whale Cluster Alert

**Kanal WebSocket**: `futures_trades@{exchange}@{symbol}@{usd_threshold}` (via aggregation)

**Format Output**:
```
🐋 **WHALE CLUSTER – BTCUSDT**

Cluster Type : BUY Dominance 📈
Total Volume : $3.5M
BUY Volume   : $2.8M (5 trades)
SELL Volume  : $700K (2 trades)
Dominance    : 80.0%
Window       : 30 seconds

📊 *Cluster Analysis*:
• Significant whale accumulation detected
• BUY pressure overwhelming
• Potential price movement expected

#whale_cluster #BTC
```

**Cluster Detection Logic**:
```python
# 30-second window analysis
trade_events = get_last_30_seconds(symbol)
group_by_side = buy_vs_sell_trades
calculate_dominance_ratio()

if total_volume >= threshold AND dominance >= min_ratio:
    trigger_cluster_alert()
```

**Threshold per Symbol Group**:
- **MAJORS**: $3M total, 70% dominance, 3+ trades
- **LARGE_CAP**: $1.5M total, 65% dominance, 2+ trades
- **MID_CAP**: $500K total, 60% dominance, 2+ trades

**Frekuensi Pemicu**:
- **Pattern-based**: Setiap terdeteksi cluster pattern
- **Cooldown**: 10 menit per symbol
- **Detection Loop**: Setiap 5 detik scan semua active symbols
- **Window Analysis**: 30 detik rolling window
- **Dominance Filter**: Filter balanced clusters (tidak signifikan)

---

### 5. Global Radar (Composite) Alert

**Kanal WebSocket**: Kombinasi `liquidationOrders` + `futures_trades`

**Format Output**:
```
🚀 **GLOBAL RADAR – BTCUSDT**

Pattern     : Liquidation Storm + Whale Cluster
Signal      : Extreme 🔴
Score       : 0.85/1.0
Volatility  : Extreme 🔴
Pressure    : Bearish 🔴 (Bearish)
Window      : 30 seconds

📊 *Market Activity*:
Storm USD   : $2.5M 📉
Whale Flow  : $3.5M 🔴
  BUY : $2.8M
  SELL: $700K

🎯 *Radar Analysis*:
• Extreme convergence: Storm + Whale Cluster detected
• Composite intelligence analysis
• Multi-pattern correlation detected

#global_radar #BTC #market_anomaly
```

**Composite Pattern Types**:
1. **Storm Only**: Hanya liquidation storm
2. **Cluster Only**: Hanya whale cluster  
3. **Storm + Cluster**: Keduanya terdeteksi
4. **Convergence**: Pattern ekstrem (keduanya dengan volume tinggi)

**Scoring Algorithm**:
```python
storm_score = min(storm_volume / (min_threshold * 3), 0.5)
cluster_score = min(cluster_volume / (min_threshold * 3), 0.5)
base_score = storm_score + cluster_score

if storm AND cluster:
    base_score += convergence_bonus  # 0.2-0.3
    
if base_score >= min_threshold OR convergence_detected:
    trigger_radar_alert()
```

**Signal Strength Levels**:
- **Weak** (0.0-0.4): Single pattern dengan volume rendah
- **Moderate** (0.4-0.6): Single pattern dengan volume sedang
- **Strong** (0.6-0.8): Multiple patterns atau volume tinggi
- **Extreme** (0.8+): Convergence pattern atau volume sangat tinggi

**Frekuensi Pemicu**:
- **Composite Intelligence**: Setiap 5 detik scan all active symbols
- **Cooldown**: 5 menit per symbol
- **Multi-pattern Correlation**: Menganalisis korelasi antar patterns
- **Market Context**: Mempertimbangkan volatility dan market pressure

---

## 🔄 Flow Alert System

### Event Flow Architecture
```
WebSocket Feed → Event Aggregator → Multiple Detectors → Smart Alert Engine → Telegram
                      ↓
               [30-second Buffer]
                      ↓
    ┌─────────────────┬─────────────────┬─────────────────┐
    │ Storm Detector │Cluster Detector │ Radar Engine    │
    └─────────────────┴─────────────────┴─────────────────┘
                      ↓
              Cooldown Management
                      ↓
              Message Formatting
                      ↓
                 Telegram Bot
```

### Timing Specifications

**Detection Intervals**:
- **Real-time Events**: Liquidation & Whale alerts (immediate)
- **Pattern Detection**: Storm, Cluster, Radar alerts (every 5 seconds)
- **Window Analysis**: 30-second rolling window
- **Cooldown Management**: Per-symbol tracking

**Performance Metrics**:
- **WebSocket Latency**: < 50ms connection time
- **Alert Processing**: < 10ms per event
- **Pattern Analysis**: < 100ms per symbol per cycle
- **Memory Buffer**: 30-second event window per symbol

---

## 📊 Provider & Exchange Coverage

### Primary Provider: CoinGlass
- **WebSocket API**: Real-time liquidation dan trade data
- **Coverage**: Multi-exchange aggregation
- **Data Types**: Liquidations, Large Futures Trades
- **Update Frequency**: Real-time streaming

### Exchange Support Matrix
| Exchange | Liquidation Data | Whale Trade Data | Status |
|----------|------------------|------------------|---------|
| Binance  | ✅ Full          | ✅ Full          | Active  |
| Bybit    | ✅ Full          | ✅ Full          | Active  |
| OKX      | ✅ Full          | ✅ Full          | Active  |
| Others   | ✅ Partial       | ✅ Partial       | Supported |

### Cross-Exchange Features
- **Normalization**: Standardized data format across exchanges
- **Correlation Analysis**: Cross-exchange pattern detection
- **Health Monitoring**: Per-exchange connection status
- **Failover**: Automatic provider switching

---

## 🛡️ Anti-Spam & Rate Limiting

### Cooldown Strategy
```python
cooldown_settings = {
    "liquidation_alert": {"per_symbol": 300, "per_direction": 300},  # 5 menit
    "whale_alert": {"per_symbol": 300, "per_direction": 300},        # 5 menit
    "storm_alert": {"per_symbol": 300},                              # 5 menit
    "cluster_alert": {"per_symbol": 600},                            # 10 menit
    "radar_alert": {"per_symbol": 300}                              # 5 menit
}
```

### Rate Limiting
- **Per-Auth Key**: 60 requests per minute
- **Global Limit**: 120 requests per minute
- **Burst Protection**: Automatic throttling
- **Circuit Breaker**: Fail on repeated failures

### Smart Filtering
- **Volume Thresholds**: Dynamic per symbol group
- **Pattern Recognition**: Multi-pattern correlation
- **Market Context**: Volatility-aware filtering
- **Duplicate Prevention**: Event deduplication

---

## 📈 Frekuensi Alert Summary

| Alert Type | Trigger Frequency | Cooldown | Typical Volume/Hour |
|------------|-------------------|----------|-------------------|
| Liquidation | Per Event (real-time) | 5 min | 5-15 alerts |
| Whale Trade | Per Event (real-time) | 5 min | 3-10 alerts |
| Storm | Pattern-based (5s interval) | 5 min | 2-5 alerts |
| Cluster | Pattern-based (5s interval) | 10 min | 1-3 alerts |
| Radar | Composite (5s interval) | 5 min | 1-2 alerts |

### Peak Load Scenarios
- **High Volatility**: 50+ alerts/hour
- **Market Stress**: 100+ alerts/hour (with storm/radar)
- **Normal Market**: 10-20 alerts/hour

---

## 🔧 Configuration & Customization

### Environment Variables
```bash
# Alert Thresholds
WHALE_TRANSACTION_THRESHOLD_USD=500000
LIQUIDATION_THRESHOLD_USD=1000000

# Cooldown Settings
WHALE_DEBOUNCE_MINUTES=5
LIQUIDATION_DEBOUNCE_MINUTES=2

# WebSocket Settings
WS_PING_INTERVAL=20
WS_PING_TIMEOUT=60
WS_ADAPTIVE_PING_ENABLED=true

# Rate Limiting
API_CALLS_PER_MINUTE=120
RATE_LIMIT_PER_AUTH_KEY=60
```

### Symbol Group Customization
```python
SYMBOL_GROUPS = {
    "MAJORS": {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "liq_min_usd": 500000,
        "whale_min_usd": 1000000,
        "cooldown_sec": 300
    },
    "LARGE_CAP": {
        "symbols": ["BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"],
        "liq_min_usd": 200000,
        "whale_min_usd": 500000,
        "cooldown_sec": 450
    }
}
```

---

## 🎯 Key Insights

### 1. Hierarchical Alert System
- **Level 1**: Real-time events (Liquidation, Whale)
- **Level 2**: Pattern detection (Storm, Cluster)
- **Level 3**: Composite intelligence (Global Radar)

### 2. Intelligent Filtering
- **Volume-based thresholds** per symbol group
- **Pattern correlation** untuk high-confidence signals
- **Market context** awareness untuk appropriateness

### 3. Performance Optimized
- **Adaptive ping** untuk connection quality
- **Memory-efficient** event buffering
- **Multi-threaded** pattern detection

### 4. Production Ready
- **Auto-reconnection** dengan exponential backoff
- **Circuit breaker** untuk API failures
- **Comprehensive error handling**
- **Graceful degradation** pada provider issues

---

## 📝 Kesimpulan

WebSocket Alert System TELEGLAS menyediakan monitoring market yang komprehensif dengan:

✅ **5 Jenis Alert** dengan logika pemicu yang berbeda
✅ **Real-time Processing** untuk immediate alerts
✅ **Pattern Recognition** untuk sophisticated analysis  
✅ **Anti-spam Protection** dengan intelligent cooldowns
✅ **Multi-exchange Support** dengan broad coverage
✅ **Composite Intelligence** untuk high-confidence signals
✅ **Production-grade Architecture** dengan robust error handling

System ini dirancang untuk memberikan intellegence market yang actionable sambil meminimalkan noise dan false alerts melalui smart filtering dan correlation analysis.
