# TELEGLAS GPT API - Advanced Features Documentation

## Overview

TELEGLAS GPT API menyediakan fitur-fitur advanced untuk monitoring, analytics, webhooks, GraphQL, dan multi-exchange integration.

## 🚀 Advanced Features

### 1. Caching Layer with Redis

#### Overview
Redis caching untuk meningkatkan performance dan mengurangi load ke external APIs.

#### Configuration
```bash
# Environment variables
GPT_API_CACHE_ENABLED=true
GPT_API_CACHE_TTL=300
GPT_API_REDIS_URL=redis://localhost:6379/0
```

#### Features
- **Intelligent Caching**: Automatic caching untuk market data
- **Cache Warming**: Pre-load popular data
- **TTL Management**: Configurable expiration times
- **Cache Invalidation**: Smart invalidation strategies

#### Cache Keys
```
market_data:{symbol}:{type}
aggregated_data:{symbol}
multi_ticker:{symbol}
multi_orderbook:{symbol}
```

#### Usage Example
```python
# Manual cache operations
from gpt_api.cache import cache_manager

# Set cache
await cache_manager.set("market_data", "BTC", data, ttl=300)

# Get cache
data = await cache_manager.get("market_data", "BTC")

# Delete cache
await cache_manager.delete("market_data", "BTC")
```

### 2. Analytics Module

#### Overview
Lightweight analytics tracking untuk API usage monitoring.

#### Features
- **Request Tracking**: Log semua API requests
- **Performance Metrics**: Response time, success rates
- **Usage Analytics**: Top endpoints, symbols, users
- **Real-time Dashboard**: Live monitoring

#### Analytics Data Points
- Request timestamp
- Endpoint and method
- Response time
- Status code
- API key (partial for privacy)
- Symbol queried
- Error messages

#### Analytics Endpoints
```bash
# Get analytics stats
GET /admin/analytics/stats?period_hours=24

# Get real-time metrics
GET /admin/analytics/realtime

# Export analytics data
GET /admin/analytics/export?start_date=2024-01-01&end_date=2024-01-02&format=json
```

#### Analytics Configuration
```bash
GPT_API_ANALYTICS_ENABLED=true
GPT_API_ANALYTICS_RETENTION_DAYS=30
GPT_API_ANALYTICS_EXPORT_FORMAT=json
```

### 3. Webhooks System

#### Overview
Real-time data push mechanism untuk registered endpoints.

#### Features
- **Event-driven**: Automatic notifications on events
- **Reliable Delivery**: Retry mechanism with exponential backoff
- **Security**: HMAC signature verification
- **Rate Limiting**: Prevent spam
- **Flexible Filtering**: Symbol and event type filters

#### Supported Events
- `whale` - Large transactions
- `liquidation` - Liquidation events
- `price_alert` - Price threshold alerts

#### Webhook Management

##### Register Webhook
```bash
POST /webhooks/register
{
  "url": "https://your-endpoint.com/webhook",
  "events": ["whale", "liquidation"],
  "symbols": ["BTC", "ETH"],
  "secret": "your-webhook-secret"
}
```

##### Webhook Payload Format
```json
{
  "event_id": "evt_1234567890",
  "event_type": "whale",
  "symbol": "BTC",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "transaction_id": "tx_123",
    "amount": 10.5,
    "price": 45000,
    "usd_value": 472500,
    "side": "buy"
  }
}
```

##### Signature Verification
```python
import hmac
import hashlib

def verify_signature(payload: str, signature: str, secret: str):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={expected}" == signature
```

#### Webhook Configuration
```bash
GPT_API_WEBHOOKS_ENABLED=true
GPT_API_WEBHOOK_MAX_SUBSCRIPTIONS=100
GPT_API_WEBHOOK_RATE_LIMIT_SECONDS=30
GPT_API_WEBHOOK_MAX_FAILURES=5
```

### 4. GraphQL Endpoint

#### Overview
Flexible data querying dengan GraphQL untuk complex data requirements.

#### GraphQL Endpoint
```
POST /graphql
```

#### GraphQL Schema

##### Queries
```graphql
# Get price data
query GetPrice($symbol: String!) {
  price(symbol: $symbol) {
    price
    change_24h
    volume_24h
    timestamp
  }
}

# Get whale transactions with filters
query GetWhaleTransactions($symbol: String!, $filter: WhaleFilter) {
  whaleTransactions(symbol: $symbol, filter: $filter) {
    id
    symbol
    side
    amount
    price
    usdValue
    timestamp
    exchange
  }
}

# Get complete market data
query GetMarketData($symbol: String!) {
  marketData(symbol: $symbol) {
    symbol
    price {
      price
      change_24h
      volume_24h
    }
    whaleTransactions {
      id
      amount
      usdValue
    }
    liquidations {
      id
      amount
      usdValue
    }
    orderbook {
      bids {
        price
        amount
        total
      }
      asks {
        price
        amount
        total
      }
      spread
    }
    timestamp
  }
}
```

##### Input Types
```graphql
input WhaleFilter {
  minUsdValue: Float
  side: String
  limit: Int
}

input LiquidationFilter {
  minUsdValue: Float
  side: String
  limit: Int
}

input OrderbookFilter {
  depth: Int
  minSpread: Float
}
```

##### Subscriptions
```graphql
subscription PriceUpdates($symbols: [String!]!) {
  priceUpdates(symbols: $symbols) {
    symbol
    price
    change_24h
    timestamp
  }
}
```

#### GraphQL Authentication
```bash
# Set API key in header
Authorization: Bearer your-api-key
```

### 5. Multi-Exchange Integration

#### Overview
Support untuk multiple cryptocurrency exchanges dengan data aggregation.

#### Supported Exchanges
- Binance
- Coinbase
- Kraken
- Bybit
- OKX
- Huobi
- KuCoin

#### Exchange Features
- **Public Data**: Ticker, orderbook, trades
- **Aggregated Data**: Weighted averages across exchanges
- **Symbol Mapping**: Automatic symbol format conversion
- **Health Monitoring**: Real-time exchange status
- **Rate Limiting**: Respect exchange rate limits

#### Multi-Exchange Endpoints

##### Aggregated Ticker
```bash
GET /multi/ticker/{symbol}
```

Response:
```json
{
  "success": true,
  "symbol": "BTC",
  "exchange": "aggregated",
  "price": 45234.56,
  "bid": 45230.00,
  "ask": 45240.00,
  "volume_24h": 1234567890,
  "change_24h": 2.5,
  "high_24h": 46000,
  "low_24h": 44000,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

##### Aggregated Orderbook
```bash
GET /multi/orderbook/{symbol}?depth=20
```

##### Exchange Health
```bash
GET /multi/health
```

##### Supported Symbols
```bash
GET /multi/symbols?exchange=binance
```

##### Exchange Trades
```bash
GET /multi/trades/{symbol}?limit=50&exchange=binance
```

#### Symbol Mapping
```python
# Automatic symbol format conversion
{
  "BTC": {
    "binance": "BTC/USDT",
    "coinbase": "BTC-USD",
    "kraken": "XBT/USD",
    "bybit": "BTCUSDT",
    "okx": "BTC-USDT",
    "huobi": "btcusdt",
    "kucoin": "BTC-USDT"
  }
}
```

#### Exchange Configuration
```python
# Add exchange API keys (optional, for private data)
GPT_API_BINANCE_API_KEY=your-api-key
GPT_API_BINANCE_SECRET=your-secret
GPT_API_COINBASE_API_KEY=your-api-key
GPT_API_COINBASE_SECRET=your-secret
GPT_API_COINBASE_PASSPHRASE=your-passphrase
```

## 🔧 Configuration

### Environment Variables

#### Basic Configuration
```bash
# Server
GPT_API_HOST=0.0.0.0
GPT_API_PORT=8000
GPT_API_DEBUG=false

# Security
GPT_API_API_KEYS=key1,key2,key3
GPT_API_REQUIRE_AUTH=true
GPT_API_IP_ALLOWLIST=127.0.0.1,192.168.1.100

# Rate Limiting
GPT_API_RATE_LIMIT_REQUESTS=100
GPT_API_RATE_LIMIT_WINDOW=60
```

#### Advanced Configuration
```bash
# Caching
GPT_API_CACHE_ENABLED=true
GPT_API_CACHE_TTL=300
GPT_API_REDIS_URL=redis://localhost:6379/0

# Analytics
GPT_API_ANALYTICS_ENABLED=true
GPT_API_ANALYTICS_RETENTION_DAYS=30

# Webhooks
GPT_API_WEBHOOKS_ENABLED=true
GPT_API_WEBHOOK_MAX_SUBSCRIPTIONS=100

# Multi-Exchange
GPT_API_EXCHANGE_SANDBOX=false
GPT_API_EXCHANGE_RATE_LIMIT=1200
```

## 📊 Performance Optimization

### Caching Strategy
1. **Market Data**: 30-60 seconds TTL
2. **Analytics**: 1 minute TTL
3. **Multi-Exchange**: 10-30 seconds TTL
4. **Static Data**: 1 hour TTL

### Rate Limiting
- **Per API Key**: 100 requests/minute
- **Per IP**: 1000 requests/minute
- **Global**: 10000 requests/minute

### Monitoring
- **Response Time**: < 500ms average
- **Success Rate**: > 99%
- **Cache Hit Rate**: > 80%

## 🔒 Security

### Authentication
- **API Key**: Bearer token authentication
- **IP Allowlist**: Optional IP restriction
- **CORS**: Configurable origin restrictions

### Webhook Security
- **HMAC Signatures**: SHA256 verification
- **Rate Limiting**: Prevent webhook spam
- **HTTPS Required**: Secure webhook delivery

### Data Privacy
- **PII Redaction**: Partial API keys in logs
- **Data Retention**: Configurable retention periods
- **Access Logs**: Comprehensive audit trail

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t teleglas-gpt-api .

# Run with Redis
docker-compose up -d
```

### PM2 Deployment
```bash
# Install dependencies
pip install -r gpt_api/requirements.txt

# Start service
pm2 start gpt_api/gpt_api_main.py --name teleglas-gpt-api

# Monitor
pm2 monit
```

### Systemd Deployment
```bash
# Copy service file
sudo cp gpt_api/systemd/teleglas-gpt-api.service /etc/systemd/system/

# Enable and start
sudo systemctl enable teleglas-gpt-api
sudo systemctl start teleglas-gpt-api
```

## 📈 Monitoring

### Health Checks
```bash
# Basic health
GET /health

# Detailed health
GET /health/detailed

# Component health
GET /health/cache
GET /health/exchanges
GET /health/webhooks
```

### Metrics
```bash
# Application metrics
GET /metrics

# Analytics stats
GET /admin/analytics/stats

# Real-time metrics
GET /admin/analytics/realtime
```

### Logging
- **Application Logs**: `/var/log/teleglas/gpt-api.log`
- **Access Logs**: `/var/log/teleglas/access.log`
- **Analytics Logs**: `/var/log/teleglas/analytics/`

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
pytest gpt_api/tests/

# Run specific test
pytest gpt_api/tests/test_analytics.py

# Coverage report
pytest --cov=gpt_api gpt_api/tests/
```

### Integration Tests
```bash
# API tests
python gpt_api/tests/test_api_integration.py

# Webhook tests
python gpt_api/tests/test_webhooks.py

# Multi-exchange tests
python gpt_api/tests/test_multi_exchange.py
```

### Load Testing
```bash
# Install load testing tool
pip install locust

# Run load test
locust -f gpt_api/tests/load_test.py --host=http://localhost:8000
```

## 📚 API Reference

### REST Endpoints

#### Market Data
- `GET /gpt/raw?symbol={symbol}` - Raw market data
- `GET /gpt/whale?symbol={symbol}` - Whale transactions
- `GET /gpt/liq?symbol={symbol}` - Liquidations
- `GET /gpt/orderbook?symbol={symbol}` - Orderbook

#### Multi-Exchange
- `GET /multi/ticker/{symbol}` - Aggregated ticker
- `GET /multi/orderbook/{symbol}` - Aggregated orderbook
- `GET /multi/health` - Exchange health
- `GET /multi/symbols` - Supported symbols
- `GET /multi/trades/{symbol}` - Recent trades

#### Webhooks
- `POST /webhooks/register` - Register webhook
- `DELETE /webhooks/{id}` - Unregister webhook
- `GET /webhooks` - List webhooks
- `POST /webhooks/{id}/test` - Test webhook

#### Analytics
- `GET /admin/analytics/stats` - Analytics stats
- `GET /admin/analytics/realtime` - Real-time metrics
- `GET /admin/analytics/export` - Export data

#### GraphQL
- `POST /graphql` - GraphQL endpoint
- `GET /graphql` - GraphQL playground (dev)

### Error Responses

```json
{
  "success": false,
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Symbol XYZ is not supported",
    "details": {
      "supported_symbols": ["BTC", "ETH", "SOL"]
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔄 Migration Guide

### From v1.0 to v2.0
1. **Breaking Changes**: None (backward compatible)
2. **New Features**: All advanced features added
3. **Configuration**: New environment variables optional
4. **Dependencies**: Additional dependencies installed automatically

### Data Format Changes
- **Response Format**: Consistent across all endpoints
- **Timestamp Format**: ISO 8601 standard
- **Error Format**: Standardized error objects

## 🛠️ Troubleshooting

### Common Issues

#### Cache Connection Failed
```bash
# Check Redis connection
redis-cli ping

# Check configuration
echo $GPT_API_REDIS_URL
```

#### Exchange API Limits
```bash
# Check exchange health
curl http://localhost:8000/multi/health

# Monitor rate limits
curl http://localhost:8000/admin/analytics/realtime
```

#### Webhook Delivery Failures
```bash
# Test webhook
curl -X POST http://localhost:8000/webhooks/{id}/test

# Check webhook status
curl http://localhost:8000/webhooks
```

### Debug Mode
```bash
# Enable debug logging
GPT_API_LOG_LEVEL=DEBUG
GPT_API_DEBUG=true

# Run with verbose output
python -m gpt_api.gpt_api_main --debug
```

## 📞 Support

### Documentation
- **API Docs**: `http://localhost:8000/docs`
- **GraphQL Playground**: `http://localhost:8000/graphql`
- **Analytics Dashboard**: `http://localhost:8000/admin/analytics`

### Logs
- **Application**: `/var/log/teleglas/gpt-api.log`
- **Analytics**: `/var/log/teleglas/analytics/`
- **Webhooks**: `/var/log/teleglas/webhooks.log`

### Health Monitoring
- **Service Status**: `systemctl status teleglas-gpt-api`
- **PM2 Status**: `pm2 status teleglas-gpt-api`
- **Docker Status**: `docker ps | grep teleglas`

---

## 🎯 Best Practices

### Performance
1. Enable Redis caching for production
2. Use appropriate TTL values
3. Monitor cache hit rates
4. Implement rate limiting

### Security
1. Use strong API keys
2. Enable IP allowlisting
3. Use HTTPS for webhooks
4. Regular key rotation

### Monitoring
1. Set up health checks
2. Monitor response times
3. Track error rates
4. Set up alerts for anomalies

### Scalability
1. Use load balancers
2. Implement horizontal scaling
3. Use Redis cluster for caching
4. Monitor resource usage

---

*Last updated: December 2024*
