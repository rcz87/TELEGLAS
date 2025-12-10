# GPT API Deployment Guide - Complete Implementation

## 🎯 Overview

GPT API telah berhasil diimplementasikan sebagai service HTTP terpisah yang tidak mengganggu bot utama dan bot alert WebSocket. API ini menyediakan data market dalam format JSON yang rapi untuk GPT Actions.

## 📁 Struktur Folder

```
gpt_api/
├── __init__.py                 # Package initialization
├── gpt_api_main.py            # Entry point utama
├── config.py                  # Konfigurasi API
├── auth.py                    # Autentikasi & keamanan
├── schemas.py                 # Pydantic response models
├── cache.py                   # Redis cache layer
├── analytics.py               # Analytics & metrics
├── webhooks.py                # Webhook support
├── graphql.py                 # GraphQL endpoint
├── multi_exchange.py          # Multi-exchange support
├── requirements.txt           # Dependencies
├── .env                       # Environment variables
├── .env.example              # Environment template
├── ecosystem.config.js        # PM2 configuration
├── Dockerfile                # Docker configuration
└── tests/
    ├── __init__.py
    ├── test_api_endpoints.py
    ├── test_staging_integration.py
    └── run_staging_tests.py
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp gpt_api/.env.example gpt_api/.env

# Edit configuration
nano gpt_api/.env
```

### 2. Install Dependencies

```bash
# Install requirements
pip install -r gpt_api/requirements.txt

# Or using virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r gpt_api/requirements.txt
```

### 3. Run Development Server

```bash
# From root directory
uvicorn gpt_api.gpt_api_main:app --host 0.0.0.0 --port 8000 --reload

# Or using Python module
python -m gpt_api.gpt_api_main
```

## 🔧 PM2 Deployment

### 1. Install PM2

```bash
# Install PM2 globally
npm install -g pm2

# Or using yarn
yarn global add pm2
```

### 2. PM2 Configuration

File `gpt_api/ecosystem.config.js` sudah disediakan:

```javascript
module.exports = {
  apps: [{
    name: 'teleglas-gpt-api',
    script: 'gpt_api/gpt_api_main.py',
    interpreter: 'python',
    interpreter_args: '-m',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      GPT_API_HOST: '0.0.0.0',
      GPT_API_PORT: 8000,
      ENVIRONMENT: 'production'
    },
    env_production: {
      NODE_ENV: 'production',
      GPT_API_HOST: '0.0.0.0',
      GPT_API_PORT: 8000,
      ENVIRONMENT: 'production',
      LOG_LEVEL: 'INFO'
    },
    error_file: './logs/gpt-api-error.log',
    out_file: './logs/gpt-api-out.log',
    log_file: './logs/gpt-api-combined.log',
    time: true
  }]
};
```

### 3. Start PM2 Service

```bash
# Start service
pm2 start gpt_api/ecosystem.config.js --env production

# Check status
pm2 status

# View logs
pm2 logs teleglas-gpt-api

# Monitor
pm2 monit
```

### 4. PM2 Management Commands

```bash
# Restart service
pm2 restart teleglas-gpt-api

# Stop service
pm2 stop teleglas-gpt-api

# Delete service
pm2 delete teleglas-gpt-api

# Save PM2 configuration
pm2 save

# Setup PM2 startup script
pm2 startup
```

## 🔐 Security Configuration

### API Key Authentication

```bash
# Set secure API key in .env
API_KEY=your_secure_api_key_here_12345

# Use in requests
curl -H "X-API-Key: your_secure_api_key_here_12345" \
     http://localhost:8000/gpt/raw?symbol=BTC
```

### IP Whitelist

```bash
# Configure allowed IPs
ALLOWED_IPS=127.0.0.1,::1,192.168.1.100

# For production, add your server IPs
ALLOWED_IPS=127.0.0.1,::1,your_server_ip
```

## 📊 Available Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/info` | API information |
| GET | `/symbols` | Supported symbols |

### GPT Actions Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gpt/raw?symbol=BTC` | Raw market data |
| GET | `/gpt/whale?symbol=BTC` | Whale transactions |
| GET | `/gpt/liq?symbol=BTC` | Liquidation data |
| GET | `/gpt/orderbook?symbol=BTC` | Orderbook data |

### Advanced Features

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gpt/whale?radar=true` | Whale radar |
| POST | `/webhooks` | Webhook support |
| POST | `/graphql` | GraphQL queries |
| GET | `/analytics` | Usage analytics |

## 🧪 Testing

### Manual Testing

```bash
# Health check
curl -H "X-API-Key: test_api_key_12345" \
     http://localhost:8000/health

# Raw data
curl -H "X-API-Key: test_api_key_12345" \
     http://localhost:8000/gpt/raw?symbol=BTC

# Whale data
curl -H "X-API-Key: test_api_key_12345" \
     http://localhost:8000/gpt/whale?symbol=BTC&limit=10

# Liquidation data
curl -H "X-API-Key: test_api_key_12345" \
     http://localhost:8000/gpt/liq?symbol=BTC

# Orderbook data
curl -H "X-API-Key: test_api_key_12345" \
     http://localhost:8000/gpt/orderbook?symbol=BTC&depth=20
```

### Automated Testing

```bash
# Run all tests
cd gpt_api
python tests/run_staging_tests.py

# Run specific tests
python -m pytest tests/test_api_endpoints.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t teleglas-gpt-api:latest .

# Run container
docker run -d \
  --name teleglas-gpt-api \
  -p 8000:8000 \
  --env-file gpt_api/.env \
  teleglas-gpt-api:latest
```

### Docker Compose

```yaml
version: '3.8'
services:
  gpt-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - gpt_api/.env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

## 🚦 Production Checklist

### Security

- [ ] Set strong API key
- [ ] Configure IP whitelist
- [ ] Enable HTTPS (reverse proxy)
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Monitor logs

### Performance

- [ ] Configure Redis cache
- [ ] Set up monitoring
- [ ] Configure log rotation
- [ ] Set up alerts
- [ ] Optimize database queries

### Reliability

- [ ] Set up PM2 auto-restart
- [ ] Configure health checks
- [ ] Set up backup procedures
- [ ] Test failover scenarios
- [ ] Document recovery procedures

## 🔄 Integration with Existing Bots

### No Impact on Main Bot

- ✅ Main bot (`main.py`) unchanged
- ✅ Telegram handlers unchanged
- ✅ Database operations unchanged
- ✅ WebSocket alerts unchanged

### No Impact on Alert Bot

- ✅ Alert WebSocket unchanged
- ✅ Alert engine unchanged
- ✅ Event aggregation unchanged

### Shared Services

- ✅ Market data core shared
- ✅ No duplicate logic
- ✅ Consistent data sources

## 📈 Monitoring & Analytics

### Built-in Analytics

```bash
# View usage stats
curl -H "X-API-Key: admin_key" \
     http://localhost:8000/analytics

# View system health
curl -H "X-API-Key: admin_key" \
     http://localhost:8000/health
```

### Log Monitoring

```bash
# View PM2 logs
pm2 logs teleglas-gpt-api

# View application logs
tail -f logs/gpt_api.log

# View error logs
tail -f logs/gpt-api-error.log
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Kill process on port
   sudo lsof -ti:8000 | xargs kill -9
   # Or use different port
   GPT_API_PORT=8001
   ```

2. **Import errors**
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"
   # Install missing dependencies
   pip install -r gpt_api/requirements.txt
   ```

3. **Authentication errors**
   ```bash
   # Check API key in .env
   grep API_KEY gpt_api/.env
   # Verify IP whitelist
   grep ALLOWED_IPS gpt_api/.env
   ```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG
GPT_API_DEBUG=true

# Run with verbose output
uvicorn gpt_api.gpt_api_main:app --log-level debug
```

## 📚 API Documentation

### Interactive Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Response Format

All responses follow consistent format:

```json
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "symbol": "BTC",
  "data": { ... }
}
```

### Error Handling

```json
{
  "success": false,
  "timestamp": "2025-01-01T00:00:00Z",
  "error": "Error message",
  "error_code": "ERROR_CODE"
}
```

## 🎯 Production Deployment Example

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL Certificate

```bash
# Using Let's Encrypt
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📞 Support

### Log Analysis

```bash
# Check error patterns
grep "ERROR" logs/gpt-api-error.log | tail -20

# Check API usage
grep "GET /gpt/" logs/gpt-api-out.log | wc -l

# Check response times
grep "processing_time" logs/gpt-api-combined.log
```

### Performance Monitoring

```bash
# Check PM2 metrics
pm2 show teleglas-gpt-api

# Monitor system resources
pm2 monit

# Check memory usage
pm2 show teleglas-gpt-api | grep memory
```

---

## ✅ Implementation Status

- [x] ✅ GPT API service created
- [x] ✅ All endpoints implemented
- [x] ✅ Security & authentication
- [x] ✅ JSON schema responses
- [x] ✅ PM2 configuration
- [x] ✅ Docker support
- [x] ✅ Documentation complete
- [x] ✅ Testing framework
- [x] ✅ Production ready

**🎉 GPT API implementation is complete and production-ready!**
