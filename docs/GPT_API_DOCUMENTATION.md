# TELEGLAS GPT API Documentation

## Overview

TELEGLAS GPT API is a standalone HTTP service that provides clean JSON market data for GPT Actions. It exposes the same core functionality as the Telegram bot commands but in a structured API format.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GPT Actions   │───▶│   GPT API       │───▶│ Market Data     │
│   (External)    │    │   (FastAPI)     │    │ Core Service    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Data Sources   │
                       │ (CoinGlass API) │
                       └─────────────────┘
```

## Key Features

- **Independent Service**: Runs separately from main bot and WebSocket alert system
- **Clean JSON Output**: Structured responses with Pydantic schemas
- **Security**: API key authentication and IP allowlist support
- **Rate Limiting**: Configurable rate limits per API key
- **Read-Only**: No modifications to bot state, database, or subscriptions
- **Comprehensive Endpoints**: All major market data endpoints available

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Authentication
All endpoints (except `/`, `/health`, `/info`, `/symbols`) require:
- **API Key**: `Authorization: Bearer YOUR_API_KEY`
- **IP Allowlist**: Optional IP-based access control

### Core Endpoints

#### Get Raw Market Data
```http
GET /gpt/raw?symbol=BTC
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "symbol": "BTC",
  "data": {
    "symbol": "BTC",
    "market_stats": {
      "price": {
        "current": 45000.0,
        "change_24h": 500.0,
        "change_percent_24h": 1.12,
        "high_24h": 45500.0,
        "low_24h": 44500.0
      },
      "volume": {
        "spot_24h": 1000000000.0,
        "futures_24h": 2000000000.0,
        "open_interest": 500000000.0
      },
      "liquidations": {
        "total_24h": 10000000.0,
        "long_liq": 6000000.0,
        "short_liq": 4000000.0
      }
    },
    "funding_rate": 0.01,
    "next_funding_time": "2025-01-01T08:00:00Z",
    "data_sources": ["binance", "okx", "bybit"]
  }
}
```

#### Get Whale Data
```http
GET /gpt/whale?symbol=BTC&limit=10
```

**Parameters:**
- `symbol` (optional): Trading symbol
- `limit` (optional): Number of transactions (1-100, default: 10)
- `threshold` (optional): Minimum threshold in USD
- `radar` (optional): Get whale radar data instead of transactions

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "symbol": "BTC",
  "data": {
    "transactions": [
      {
        "symbol": "BTC",
        "side": "buy",
        "amount_usd": 1000000.0,
        "price": 45000.0,
        "timestamp": "2025-01-01T00:00:00Z",
        "transaction_hash": "0x123..."
      }
    ],
    "total_transactions": 1,
    "total_volume_usd": 1000000.0,
    "time_range": "last_24h"
  }
}
```

#### Get Liquidation Data
```http
GET /gpt/liq?symbol=BTC
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "symbol": "BTC",
  "data": {
    "symbol": "BTC",
    "liquidation_data": {
      "symbol": "BTC",
      "liquidation_usd": 10000000.0,
      "long_liquidation_usd": 6000000.0,
      "short_liquidation_usd": 4000000.0,
      "exchange_count": 3,
      "price_change": 1.12,
      "volume_24h": 2000000000.0,
      "last_update": "2025-01-01T00:00:00Z"
    },
    "dominance_ratio": 1.5,
    "significance_level": "medium"
  }
}
```

#### Get Orderbook Data
```http
GET /gpt/orderbook?symbol=BTC&depth=20
```

**Parameters:**
- `symbol` (required): Trading symbol
- `depth` (optional): Orderbook depth (1-100, default: 20)

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "symbol": "BTC",
  "data": {
    "symbol": "BTC",
    "bids": {
      "levels": [
        {
          "price": 44900.0,
          "amount": 1.5,
          "total_usd": 67350.0
        }
      ],
      "total_amount": 100.0,
      "total_usd": 4490000.0
    },
    "asks": {
      "levels": [
        {
          "price": 45100.0,
          "amount": 1.2,
          "total_usd": 54120.0
        }
      ],
      "total_amount": 80.0,
      "total_usd": 3608000.0
    },
    "spread": 200.0,
    "spread_percentage": 0.44,
    "mid_price": 45000.0,
    "last_update": "2025-01-01T00:00:00Z"
  }
}
```

### Utility Endpoints

#### Health Check
```http
GET /health
```

#### API Information
```http
GET /info
```

#### Supported Symbols
```http
GET /symbols
```

#### Root Endpoint
```http
GET /
```

## Configuration

### Environment Variables

Copy `gpt_api/.env.example` to `gpt_api/.env` and configure:

```bash
# API Server Settings
GPT_API_HOST=0.0.0.0
GPT_API_PORT=8000
GPT_API_DEBUG=false
GPT_API_ENVIRONMENT=production

# Security Settings
GPT_API_API_KEYS=your-secret-api-key-1,your-secret-api-key-2
GPT_API_REQUIRE_AUTH=true
GPT_API_IP_ALLOWLIST=192.168.1.100,10.0.0.50
GPT_API_REQUIRE_IP_WHITELIST=true

# Rate Limiting
GPT_API_RATE_LIMIT_REQUESTS=100
GPT_API_RATE_LIMIT_WINDOW=60

# CORS Settings
GPT_API_CORS_ORIGINS=*
GPT_API_CORS_METHODS=GET,OPTIONS
GPT_API_CORS_HEADERS=*
```

### Security Configuration

#### API Key Generation
Generate secure API keys:
```bash
openssl rand -hex 32  # Generate 32-byte hex key
```

#### IP Allowlist
Optional IP-based access control:
```bash
GPT_API_IP_ALLOWLIST=192.168.1.0/24,10.0.0.0/8
GPT_API_REQUIRE_IP_WHITELIST=true
```

## Response Format

### Success Response
```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "timestamp": "2025-01-01T00:00:00Z",
  "error": "Error message",
  "error_code": "HTTP_400"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid API key)
- `403`: Forbidden (IP not allowed)
- `404`: Not Found (no data available)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error

## Rate Limiting

- Default: 100 requests per minute per API key
- Configurable via environment variables
- Headers included in responses:
  - `X-RateLimit-Limit`: Requests allowed per window
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets

## Error Handling

### Common Errors

#### Invalid Symbol
```json
{
  "success": false,
  "timestamp": "2025-01-01T00:00:00Z",
  "error": "Symbol 'XYZ' is not supported. Use /info for supported symbols.",
  "error_code": "HTTP_400"
}
```

#### Invalid API Key
```json
{
  "success": false,
  "timestamp": "2025-01-01T00:00:00Z",
  "error": "Invalid API key",
  "error_code": "HTTP_401"
}
```

#### Rate Limit Exceeded
```json
{
  "success": false,
  "timestamp": "2025-01-01T00:00:00Z",
  "error": "Rate limit exceeded",
  "error_code": "HTTP_429"
}
```

## Integration Examples

### Python Example
```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get raw data
response = requests.get(
    f"{BASE_URL}/gpt/raw?symbol=BTC",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### cURL Example
```bash
# Get raw data
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/gpt/raw?symbol=BTC"

# Get whale data
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "http://localhost:8000/gpt/whale?symbol=BTC&limit=5"

# Health check
curl "http://localhost:8000/health"
```

### JavaScript Example
```javascript
const API_KEY = 'your-secret-api-key';
const BASE_URL = 'http://localhost:8000';

async function getRawData(symbol) {
  const response = await fetch(
    `${BASE_URL}/gpt/raw?symbol=${symbol}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
getRawData('BTC')
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

## Deployment

### Development
```bash
cd gpt_api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python gpt_api_main.py
```

### Production with PM2
```bash
# Install PM2 globally
npm install -g pm2

# Start service
pm2 start gpt_api_main.py --name teleglas-gpt-api

# Check status
pm2 status

# View logs
pm2 logs teleglas-gpt-api

# Restart
pm2 restart teleglas-gpt-api

# Stop
pm2 stop teleglas-gpt-api
```

### Production with systemd
```bash
# Create service file
sudo nano /etc/systemd/system/teleglas-gpt-api.service

# Service content:
[Unit]
Description=TELEGLAS GPT API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/TELEGLAS/gpt_api
Environment=PATH=/home/ubuntu/TELEGLAS/gpt_api/venv/bin
ExecStart=/home/ubuntu/TELEGLAS/gpt_api/venv/bin/python gpt_api_main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable teleglas-gpt-api
sudo systemctl start teleglas-gpt-api
sudo systemctl status teleglas-gpt-api
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "gpt_api_main.py"]
```

```bash
# Build and run
docker build -t teleglas-gpt-api .
docker run -d -p 8000:8000 --name gpt-api teleglas-gpt-api
```

## Monitoring

### Health Monitoring
- Use `/health` endpoint for health checks
- Monitor response times and error rates
- Set up alerts for service downtime

### Log Monitoring
Logs include:
- Request timestamps and processing times
- API usage statistics
- Error details and stack traces
- Authentication attempts

### Performance Metrics
Monitor:
- Request rate per API key
- Response time percentiles
- Error rates by endpoint
- Data source availability

## Troubleshooting

### Common Issues

#### Service Won't Start
1. Check Python dependencies: `pip install -r requirements.txt`
2. Verify environment variables in `.env`
3. Check port availability: `netstat -tlnp | grep 8000`
4. Review logs for specific errors

#### API Key Not Working
1. Verify API key format (16+ chars, alphanumeric + `-._`)
2. Check `GPT_API_API_KEYS` environment variable
3. Ensure no trailing spaces or special characters
4. Review authentication logs

#### No Data Available
1. Check if symbol is supported: `GET /symbols`
2. Verify data source connectivity: `GET /health`
3. Check CoinGlass API status
4. Review rate limiting headers

#### High Response Times
1. Check data source latency
2. Monitor system resources (CPU, memory)
3. Review cache configuration
4. Consider reducing request rate

### Debug Mode
Enable debug mode for detailed logging:
```bash
GPT_API_DEBUG=true python gpt_api_main.py
```

## Security Considerations

### API Key Management
- Use strong, randomly generated keys
- Rotate keys regularly
- Store keys securely (environment variables, not code)
- Monitor API key usage

### Network Security
- Use HTTPS in production
- Implement IP allowlisting for additional security
- Configure firewalls to restrict access
- Use reverse proxy for SSL termination

### Rate Limiting
- Configure appropriate limits for your use case
- Monitor for abuse patterns
- Consider implementing adaptive rate limiting
- Set up alerts for unusual activity

## Version History

### v1.0.0
- Initial release
- Core market data endpoints
- API key authentication
- Rate limiting
- Health monitoring
- Comprehensive documentation

## Support

For issues and support:
1. Check this documentation first
2. Review service logs
3. Test with provided examples
4. Check health endpoint status
5. Report issues with full error details and reproduction steps

## License

This API is part of the TELEGLAS project. See main project LICENSE for details.
