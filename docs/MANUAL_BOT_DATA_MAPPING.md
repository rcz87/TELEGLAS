# MANUAL BOT DATA MAPPING & GAP ANALYSIS

## Project Context
- **Project**: TELEGLAS - Manual Bot Commands Audit & Upgrade
- **Focus**: Bot manual (main.py) commands vs WebSocket alert bot consistency
- **Target**: Make manual bot data quality setara dengan CoinGlass Web UI

## COMMANDS AUDITED
Focus pada command utama:
1. `/raw` - RAW DATA MULTI-TF (price, OI, volume, funding, liq, dll)
2. `/liq` - liquidations (24h / 1h / heatmap)  
3. `/whale` - whale / large trades
4. Command lain yang menggunakan CoinGlass (RSI, funding, OI, dll)

## DATA MAPPING TABLE

| COMMAND | SERVICE FUNCTION | API ENDPOINT CoinGlass | Parameters | Output Fields Used | Gap Analysis |
|---------|------------------|------------------------|------------|-------------------|--------------|
| **`/raw`** | `raw_data_service.get_comprehensive_market_data()` | Multiple endpoints (see below) | symbol | Price, OI, Volume, Funding, Liq, L/S Ratio, RSI, Taker Flow | **HIGH GAP** - Funding rate hanya dari Binance, tidak aggregated |
| | `get_market()` | `/api/futures/coins-markets` | symbol | current_price, price_change_1h/4h/24h, volume_24h | **MEDIUM** - Data terbatas, hanya 100 coins pertama |
| | `get_open_interest()` | `/api/futures/open-interest/history` | symbol, exchange=Binance | close (OI value), time | **HIGH** - Hanya Binance, tidak multi-exchange |
| | `get_liquidations()` | `/api/futures/liquidation/aggregated-history` | symbol, interval=1d | aggregated_long_liquidation_usd, aggregated_short_liquidation_usd | **LOW** - Sudah aggregated ✓ |
| | `get_funding_rate()` | `/api/futures/funding-rate/history` | symbol, exchange=Binance, interval=8h | fundingRate, time | **HIGH** - Hanya Binance, tidak aggregated |
| | `get_long_short()` | `/api/futures/global-long-short-account-ratio/history` | symbol, exchange=Binance, interval=h1 | global_account_long_percent, global_account_short_percent, global_account_long_short_ratio | **MEDIUM** - Hanya Binance, tapi global account ✓ |
| | `get_taker_volume()` | `/api/futures/v2/taker-buy-sell-volume/history` | symbol, exchange=Binance, interval (5m/15m/1h/4h) | taker_buy_volume_usd, taker_sell_volume_usd | **MEDIUM** - Hanya Binance, tapi multi-timeframe ✓ |
| | `get_rsi_multi_tf()` | `/api/futures/indicators/rsi` | symbol, exchange=Binance, interval (5m/15m/1h/4h) | rsi_value | **MEDIUM** - Hanya Binance, tapi multi-timeframe ✓ |
| **`/liq`** | `build_liq_message()` → `liquidation_monitor.get_liquidation_data()` | `/api/futures/liquidation/aggregated-history` | symbol, range=24h | aggregated_long_liquidation_usd, aggregated_short_liquidation_usd, total_liq_24h | **LOW** - Sudah aggregated ✓ |
| **`/whale`** | `build_whale_message()` → `whale_watcher.get_whale_alerts()` | `/api/hyperliquid/whale-alert` | - | symbol, side, usd_value, timestamp | **LOW** - Data dari Hyperliquid, bukan CoinGlass aggregation |
| **`/sentiment`** | `handle_sentiment()` → Multiple endpoints | Various | - | Fear & Greed, Funding Sentiment, OI Trend, L/S Ratio | **MEDIUM** - Mix dari berbagai sources |

## CRITICAL FINDINGS

### 1. FUNDING RATE GAP (HIGH PRIORITY)
**Problem**: 
- Command `/raw BTC` menampilkan funding rate hanya dari Binance
- CoinGlass Web UI menampilkan **AGGREGATED funding rate** dari semua exchange
- Ini menyebabkan perbedaan signifikan antara bot dan UI

**Current Implementation**:
```python
# Di services/raw_data_service.py - get_funding_rate()
result = await self.api.get_funding_rate(symbol, "Binance")  # HARDCODE Binance!
```

**Expected Behavior**:
- Bot manual harus menampilkan **Funding (Global)** - aggregated dari semua exchange
- Opsional: Breakdown top 3 exchange (Binance, Bybit, OKX)

### 2. OPEN INTEREST GAP (HIGH PRIORITY)
**Problem**:
- OI data hanya dari Binance (`/api/futures/open-interest/history` dengan `exchange=Binance`)
- CoinGlass UI menampilkan **Total OI (all exchanges)**

**Current Implementation**:
```python
# Di get_open_interest()
result = await self.api.get_open_interest_exchange_list(symbol)  # Default Binance
```

### 3. LONG/SHORT RATIO GAP (MEDIUM PRIORITY)
**Problem**:
- L/S ratio hanya dari Binance (`/api/futures/global-long-short-account-ratio/history` dengan `exchange=Binance`)
- Seharusnya global account ratio (ini sudah benar sebenarnya)

**Current Status**: ✅ **PARTIALLY CORRECT**
- Endpoint `global-long-short-account-ratio` memang untuk global account ratio
- Tapi hanya diambil dari Binance, mungkin ada perbedaan dengan multi-exchange

### 4. VOLUME DATA GAP (MEDIUM PRIORITY)
**Problem**:
- Volume data hanya dari market endpoint yang terbatas (100 coins pertama)
- Tidak ada aggregated volume dari semua exchange

### 5. LIQUIDATIONS STATUS (LOW PRIORITY)
**Status**: ✅ **GOOD**
- Sudah menggunakan `/api/futures/liquidation/aggregated-history`
- Data sudah aggregated dan mencakup multiple exchanges

### 6. WHALE DATA STATUS (LOW PRIORITY)
**Status**: ✅ **ACCEPTABLE**
- Data dari Hyperliquid (bukan CoinGlass)
- Ini adalah source yang berbeda tapi valid untuk whale transactions
- Tidak ada gap karena domain data berbeda

## EXCHANGE AGGREGATION ANALYSIS

### Current Exchange Coverage:
| Data Type | Current Exchange | Should Be | Gap Level |
|------------|-------------------|-------------|-------------|
| Funding Rate | Binance ONLY | All Exchanges (Aggregated) | **HIGH** |
| Open Interest | Binance ONLY | All Exchanges (Aggregated) | **HIGH** |
| Long/Short Ratio | Binance (Global Account) | Multi-Exchange Global | **MEDIUM** |
| Volume | Binance (Limited) | Multi-Exchange Aggregated | **MEDIUM** |
| Liquidations | Aggregated ✅ | Aggregated ✅ | **LOW** |
| Taker Flow | Binance ONLY | Multi-Exchange | **MEDIUM** |
| RSI | Binance ONLY | Multi-Exchange | **MEDIUM** |

## COINGLASS API ENDPOINTS AVAILABILITY

### Available Endpoints for Aggregation:
1. **Funding Rate**:
   - `/api/futures/funding-rate/exchange-list` ✅ (Multi-exchange)
   - `/api/futures/funding-rate/history` ❌ (Single exchange)

2. **Open Interest**:
   - `/api/futures/open-interest/exchange-history-chart` ❌ (Per exchange)
   - `/api/futures/openInterest/ohlc-aggregated-history` ✅ (Aggregated)

3. **Liquidations**:
   - `/api/futures/liquidation/aggregated-history` ✅ (Already used)
   - `/api/futures/liquidation/exchange-list` ✅ (Multi-exchange)

## RECOMMENDATIONS FOR PHASE 2

### Priority 1: Fix Funding Rate Aggregation
- Replace single-exchange funding dengan aggregated funding
- Use `/api/futures/funding-rate/exchange-list` untuk multi-exchange data
- Display "Funding (Global)" + breakdown top exchanges

### Priority 2: Fix Open Interest Aggregation  
- Use aggregated OI endpoint instead of single exchange
- Display "Total OI (all exchanges)" dengan proper labeling

### Priority 3: Enhance Long/Short Ratio
- Keep current global account ratio (already correct)
- Add multi-exchange comparison untuk transparency

## MISSING FIELDS IDENTIFIED

### In /raw command:
1. **OI Change 24h** - Currently calculated/faked, should be real
2. **Funding History** - Limited data, should use proper endpoint
3. **Volume Breakdown** - Missing spot vs futures breakdown
4. **Support/Resistance** - Currently N/A, need proper endpoint
5. **Exchange-Specific Data** - Most data only from Binance

## NEXT STEPS

Phase 2 akan fokus pada:
1. **Funding Rate Aggregation** - Implement multi-exchange funding
2. **Open Interest Aggregation** - Use aggregated OI endpoints  
3. **Label Improvements** - Clarify data sources (single vs aggregated)
4. **Data Validation** - Remove fake/calculated data, use real API data

---
*Document created: 2025-12-10*  
*Analysis based on current codebase implementation*
