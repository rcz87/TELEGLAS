# TELEGLAS GPT API Deployment Guide

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Python**: 3.9+
- **Memory**: Minimum 512MB, Recommended 1GB+
- **Storage**: 100MB free space
- **Network**: Outbound HTTPS access (port 443)

### Required Software
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install python3 python3-pip python3-venv git curl -y

# Install PM2 (Node.js process manager)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y
sudo npm install -g pm2
```

## Installation Steps

### 1. Clone Repository
```bash
cd /home/ubuntu  # or your preferred directory
git clone https://github.com/rcz87/TELEGLAS.git
cd TELEGLAS
```

### 2. Setup GPT API Environment
```bash
cd gpt_api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
nano .env  # Edit with your settings
```

### 3. Configure Environment Variables

Edit `.env` file with your configuration:

```bash
# API Server Settings
GPT_API_HOST=0.0.0.0
GPT_API_PORT=8000
GPT_API_DEBUG=false
GPT_API_ENVIRONMENT=production

# Generate secure API keys
GPT_API_API_KEYS=your-generated-api-key-1,your-generated-api-key-2
GPT_API_REQUIRE_AUTH=true

# Optional: IP restrictions (remove if not needed)
GPT_API_IP_ALLOWLIST=
GPT_API_REQUIRE_IP_WHITELIST=false

# Rate limiting
GPT_API_RATE_LIMIT_REQUESTS=100
GPT_API_RATE_LIMIT_WINDOW=60

# Logging
GPT_API_LOG_LEVEL=INFO
GPT_API_LOG_FILE=logs/gpt_api.log
```

### 4. Generate API Keys
```bash
# Generate secure API keys (32 bytes each)
API_KEY1=$(openssl rand -hex 32)
API_KEY2=$(openssl rand -hex 32)
echo "Generated API Keys:"
echo "Key 1: $API_KEY1"
echo "Key 2: $API_KEY2"

# Add to your .env file
sed -i "s/your-secret-api-key-1,your-secret-api-key-2/$API_KEY1,$API_KEY2/" .env
```

### 5. Create Log Directory
```bash
mkdir -p logs
chmod 755 logs
```

## Deployment Methods

### Method 1: PM2 (Recommended)

#### Start Service
```bash
cd /home/ubuntu/TELEGLAS/gpt_api

# Start with PM2
pm2 start gpt_api_main.py --name teleglas-gpt-api

# Save PM2 configuration
pm2 save

# Setup PM2 startup script
pm2 startup
# Follow the instructions to enable PM2 on boot
```

#### PM2 Management
```bash
# Check status
pm2 status

# View logs
pm2 logs teleglas-gpt-api

# Monitor in real-time
pm2 monit

# Restart service
pm2 restart teleglas-gpt-api

# Stop service
pm2 stop teleglas-gpt-api

# Delete service
pm2 delete teleglas-gpt-api
```

#### PM2 Configuration File (Optional)
Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'teleglas-gpt-api',
    script: 'gpt_api_main.py',
    interpreter: '/home/ubuntu/TELEGLAS/gpt_api/venv/bin/python',
    cwd: '/home/ubuntu/TELEGLAS/gpt_api',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production'
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_file: 'logs/pm2-combined.log',
    time: true
  }]
};
```

Start with configuration:
```bash
pm2 start ecosystem.config.js
```

### Method 2: systemd

#### Create Service File
```bash
sudo nano /etc/systemd/system/teleglas-gpt-api.service
```

Add the following content:
```ini
[Unit]
Description=TELEGLAS GPT API
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/TELEGLAS/gpt_api
Environment=PATH=/home/ubuntu/TELEGLAS/gpt_api/venv/bin
EnvironmentFile=/home/ubuntu/TELEGLAS/gpt_api/.env
ExecStart=/home/ubuntu/TELEGLAS/gpt_api/venv/bin/python gpt_api_main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=teleglas-gpt-api

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service on boot
sudo systemctl enable teleglas-gpt-api

# Start service
sudo systemctl start teleglas-gpt-api

# Check status
sudo systemctl status teleglas-gpt-api

# View logs
sudo journalctl -u teleglas-gpt-api -f
```

#### systemd Management
```bash
# Restart service
sudo systemctl restart teleglas-gpt-api

# Stop service
sudo systemctl stop teleglas-gpt-api

# Disable service
sudo systemctl disable teleglas-gpt-api
```

### Method 3: Docker

#### Create Dockerfile
```bash
cd /home/ubuntu/TELEGLAS/gpt_api
nano Dockerfile
```

Add the following:
```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "gpt_api_main.py"]
```

#### Build and Run
```bash
# Build image
docker build -t teleglas-gpt-api:latest .

# Run container
docker run -d \
  --name teleglas-gpt-api \
  -p 8000:8000 \
  --restart unless-stopped \
  -v /home/ubuntu/TELEGLAS/gpt_api/logs:/app/logs \
  teleglas-gpt-api:latest

# Check container
docker ps
docker logs teleglas-gpt-api
```

#### Docker Compose (Optional)
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  gpt-api:
    build: .
    container_name: teleglas-gpt-api
    ports:
      - "8000:8000"
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    environment:
      - GPT_API_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Run with Docker Compose:
```bash
docker-compose up -d
```

## Firewall Configuration

### Ubuntu (UFW)
```bash
# Allow API port
sudo ufw allow 8000/tcp

# Optional: Restrict to specific IP
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Check status
sudo ufw status
```

### CentOS (firewalld)
```bash
# Allow port
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# Optional: Restrict to specific IP
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="8000" accept'
sudo firewall-cmd --reload
```

## SSL/TLS Setup (Optional)

### Using Nginx Reverse Proxy

#### Install Nginx
```bash
sudo apt install nginx -y
```

#### Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/teleglas-gpt-api
```

Add the following:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # Replace with your domain

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # API proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}

# Rate limiting
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

#### Enable Site and Get SSL Certificate
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/teleglas-gpt-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Set up auto-renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Logging

### Log Management

#### Log Rotation
```bash
sudo nano /etc/logrotate.d/teleglas-gpt-api
```

Add the following:
```
/home/ubuntu/TELEGLAS/gpt_api/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        pm2 restart teleglas-gpt-api
    endscript
}
```

#### Systemd Log Configuration (if using systemd)
```bash
# Configure log rotation for journald
sudo nano /etc/systemd/journald.conf

# Add or modify these lines:
[Journal]
Storage=persistent
Compress=yes
SystemMaxUse=100M
SystemMaxFileSize=10M

# Restart journald
sudo systemctl restart systemd-journald
```

### Health Monitoring

#### Simple Health Check Script
```bash
nano /home/ubuntu/TELEGLAS/gpt_api/health_check.sh
```

Add the following:
```bash
#!/bin/bash

# Health check script for GPT API
API_URL="http://localhost:8000/health"
API_KEY="your-api-key"

response=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $API_KEY" \
  "$API_URL")

if [ "$response" = "200" ]; then
    echo "$(date): GPT API is healthy"
    exit 0
else
    echo "$(date): GPT API is unhealthy (HTTP $response)"
    # Restart service
    pm2 restart teleglas-gpt-api
    exit 1
fi
```

Make executable:
```bash
chmod +x /home/ubuntu/TELEGLAS/gpt_api/health_check.sh
```

#### Add to Cron
```bash
# Edit crontab
crontab -e

# Add health check every 5 minutes
*/5 * * * * /home/ubuntu/TELEGLAS/gpt_api/health_check.sh >> /home/ubuntu/TELEGLAS/gpt_api/logs/health_check.log 2>&1
```

### Performance Monitoring

#### Basic Metrics Script
```bash
nano /home/ubuntu/TELEGLAS/gpt_api/monitor.sh
```

Add the following:
```bash
#!/bin/bash

# Basic monitoring script
API_URL="http://localhost:8000/health"
LOG_FILE="/home/ubuntu/TELEGLAS/gpt_api/logs/monitor.log"

# Get response time
start_time=$(date +%s%N)
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL")
end_time=$(date +%s%N)

response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

if [ "$response" = "200" ]; then
    echo "$timestamp,healthy,$response_time" >> "$LOG_FILE"
else
    echo "$timestamp,unhealthy,$response_time" >> "$LOG_FILE"
fi
```

Make executable and add to cron:
```bash
chmod +x /home/ubuntu/TELEGLAS/gpt_api/monitor.sh

# Add to crontab for monitoring every minute
* * * * * /home/ubuntu/TELEGLAS/gpt_api/monitor.sh
```

## Testing the Deployment

### 1. Basic Connectivity Test
```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response
{
  "success": true,
  "timestamp": "2025-01-01T00:00:00Z",
  "overall_status": "healthy",
  "services": {...},
  "uptime": "...",
  "version": "1.0.0"
}
```

### 2. Authentication Test
```bash
# Test with API key
API_KEY="your-api-key"
curl -H "Authorization: Bearer $API_KEY" \
     http://localhost:8000/gpt/raw?symbol=BTC

# Test without API key (should fail)
curl http://localhost:8000/gpt/raw?symbol=BTC
```

### 3. External Access Test
```bash
# Test from external machine
API_KEY="your-api-key"
SERVER_IP="YOUR_SERVER_IP"

curl -H "Authorization: Bearer $API_KEY" \
     "http://$SERVER_IP:8000/gpt/raw?symbol=BTC"
```

### 4. Load Testing (Optional)
```bash
# Install Apache Bench
sudo apt install apache2-utils -y

# Load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -H "Authorization: Bearer YOUR_API_KEY" \
   "http://localhost:8000/gpt/raw?symbol=BTC"
```

## Troubleshooting

### Common Issues and Solutions

#### Service Won't Start
```bash
# Check logs
pm2 logs teleglas-gpt-api

# Check if port is available
sudo netstat -tlnp | grep 8000

# Check Python dependencies
cd /home/ubuntu/TELEGLAS/gpt_api
source venv/bin/activate
python gpt_api_main.py
```

#### API Key Authentication Fails
```bash
# Verify API key format
echo "API_KEY_LENGTH=${#API_KEY}"

# Check configuration
grep API_KEY .env

# Test manually
curl -v -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/health
```

#### High Memory Usage
```bash
# Check memory usage
pm2 monit

# Set memory limit in PM2
pm2 restart teleglas-gpt-api --max-memory-restart 300M

# Or in ecosystem.config.js
max_memory_restart: '300M'
```

#### Rate Limiting Issues
```bash
# Check rate limit headers
curl -I -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/gpt/raw?symbol=BTC

# Adjust limits in .env
GPT_API_RATE_LIMIT_REQUESTS=200
```

#### SSL/TLS Issues
```bash
# Check certificate
sudo certbot certificates

# Test SSL configuration
sudo nginx -t

# Check SSL expiration
sudo openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -text -noout | grep "Not After"
```

## Maintenance

### Regular Maintenance Tasks

#### Weekly
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Check logs
pm2 logs teleglas-gpt-api --lines 50

# Monitor disk space
df -h

# Update API keys if needed
```

#### Monthly
```bash
# Rotate API keys (optional)
# Generate new keys and update .env
# Restart service

# Clean old logs
find /home/ubuntu/TELEGLAS/gpt_api/logs -name "*.log" -mtime +30 -delete

# Update application
cd /home/ubuntu/TELEGLAS
git pull origin main
cd gpt_api
source venv/bin/activate
pip install -r requirements.txt
pm2 restart teleglas-gpt-api
```

### Backup and Recovery

#### Backup Configuration
```bash
# Create backup script
nano /home/ubuntu/TELEGLAS/gpt_api/backup.sh
```

Add the following:
```bash
#!/bin/bash

BACKUP_DIR="/home/ubuntu/backups/teleglas-gpt-api"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration
cp .env "$BACKUP_DIR/.env.$DATE"

# Backup PM2 configuration
pm2 save
cp ~/.pm2/dump.pm2 "$BACKUP_DIR/dump.pm2.$DATE"

# Keep last 7 days
find "$BACKUP_DIR" -name "*.env.*" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.dump.pm2.*" -mtime +7 -delete

echo "Backup completed: $DATE"
```

#### Recovery Procedure
```bash
# Stop service
pm2 stop teleglas-gpt-api

# Restore configuration
cp /home/ubuntu/backups/teleglas-gpt-api/.env.YYYYMMDD_HHMMSS .env

# Restore PM2 configuration
cp /home/ubuntu/backups/teleglas-gpt-api/dump.pm2.YYYYMMDD_HHMMSS ~/.pm2/dump.pm2

# Start service
pm2 start teleglas-gpt-api
```

## Security Best Practices

1. **Regular Updates**: Keep system and dependencies updated
2. **API Key Rotation**: Rotate API keys regularly
3. **Access Control**: Use IP allowlisting when possible
4. **SSL/TLS**: Always use HTTPS in production
5. **Monitoring**: Set up alerts for unusual activity
6. **Log Management**: Regular log review and rotation
7. **Firewall**: Restrict access to necessary ports only
8. **Rate Limiting**: Configure appropriate rate limits
9. **Backup**: Regular backups of configuration
10. **Testing**: Regular testing of disaster recovery procedures

## Support

For deployment issues:
1. Check this guide first
2. Review service logs
3. Test with provided examples
4. Check system resources
5. Consult the main documentation

Emergency contacts and escalation procedures should be documented separately based on your organization's policies.
