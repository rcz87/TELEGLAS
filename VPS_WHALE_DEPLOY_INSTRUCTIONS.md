# VPS Whale Command Deployment Instructions

## 🚀 Deployment Steps

### 1. SSH ke VPS
```bash
ssh root@your-vps-ip
cd /path/to/TELEGLAS
```

### 2. Pull Latest Changes
```bash
git pull origin master
```

### 3. Install Dependencies (jika ada yang baru)
```bash
pip install -r requirements.txt
```

### 4. Restart Bot Service
```bash
# Jika menggunakan systemd
systemctl restart tele Glas

# Atau jika menggunakan screen/pmgr
pm2 restart teleglas

# Atau manual
pkill -f python && python main.py &
```

### 5. Verify Deployment
```bash
# Check logs
tail -f logs/bot.log

# Test whale command di Telegram:
/whale
/whale 1M
/whale 250k
```

## 📋 What's Been Deployed

### New Features:
1. **Multi-Coin Whale Scanner**
   - Analyzes whale activity across ALL symbols
   - Real-time transaction sampling from Hyperliquid
   - Position ranking by volume

2. **Dynamic Threshold System**
   - Default: $500,000
   - Customizable: `/whale 1M`, `/whale 250k`, `/whale 2.5M`
   - Support formats: 500k, 1M, 250000

3. **Enhanced Output Format**
   - 3 structured sections
   - Plain text (no Markdown issues)
   - Clear numerical formatting

### Files Updated:
- `services/coinglass_api.py` - Added 3 whale API methods
- `handlers/telegram_bot.py` - Enhanced `/whale` command
- Documentation files added

## 🔍 Testing Checklist

### Basic Commands:
```bash
/whale                    # Should show multi-coin analysis
/whale 1M                 # Should show $1M+ threshold
/whale 250k               # Should show $250k+ threshold
```

### Expected Output Structure:
```
WHALE RADAR – Hyperliquid (Multi Coin)

1. BTC
   • Whale Flow : [BUY] BUY DOMINANT
   • Buy        : X tx ($X.XXM)
   • Sell       : X tx ($X.XXM)
   • Net Flow   : +$XXX,XXX

SAMPLE RECENT WHALE TRADES
1. [BUY] SYMBOL - BUY
   $XXX,XXX @ $XX.XXXX
   XX:XX:XX UTC

TOP WHALE POSITIONS (Hyperliquid)
• BTC : $XXX.XM (Long)
• ETH : $XXX.XM (Long)
• HYPE : $XXX.XM (Long)
```

## 🛠 Troubleshooting

### Common Issues:

1. **Bot doesn't restart**
   ```bash
   # Check running processes
   ps aux | grep python
   
   # Kill existing processes
   pkill -f main.py
   
   # Start fresh
   python main.py &
   ```

2. **API errors**
   ```bash
   # Check .env file
   cat .env | grep COINGLASS
   
   # Test API manually
   curl "https://www.coinglass.com/api/futures/v1/whale-alert"
   ```

3. **Memory issues**
   ```bash
   # Check memory usage
   free -h
   
   # Restart if needed
   systemctl restart teleglas
   ```

### Debug Mode:
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python main.py
```

## 📊 Expected Performance

### API Calls:
- **3 concurrent calls** per `/whale` command
- **Timeout**: 30 seconds total
- **Rate limiting**: Handled by CoinGlass API

### Memory Usage:
- **Minimal increase** (~5-10MB)
- **No persistent storage** required
- **Efficient data processing**

### Response Time:
- **Target**: <10 seconds
- **With timeout**: <30 seconds
- **Fallback**: Partial data if some endpoints fail

## 🔧 Configuration

### Environment Variables (verify these exist):
```bash
COINGLASS_API_KEY=your_key_here
ENABLE_WHALE_ALERTS=true
WHALE_POLL_INTERVAL=30
WHALE_TRANSACTION_THRESHOLD_USD=500000
```

### New Optional Variables:
```bash
# Custom default threshold (optional)
WHALE_DEFAULT_THRESHOLD=500000

# API timeout (optional)
WHALE_API_TIMEOUT=30
```

## 📈 Monitoring

### Log Monitoring:
```bash
# Watch for whale command usage
tail -f logs/bot.log | grep "/whale"

# Monitor API calls
tail -f logs/bot.log | grep "whale"
```

### Performance Metrics:
- Response time per command
- Success rate of API calls
- Error frequency
- User adoption rate

## 🎯 Success Criteria

### ✅ Deployment Successful When:
1. **Bot starts without errors**
2. **`/whale` command responds correctly**
3. **Multi-coin analysis shows data**
4. **Threshold parsing works**
5. **Output format is clean**
6. **No memory leaks or crashes**

### 🚨 Rollback Plan:
```bash
# If deployment fails:
git checkout previous_commit_hash
pip install -r requirements.txt
systemctl restart teleglas
```

## 📞 Support

### If Issues Occur:
1. **Check logs first**: `tail -f logs/bot.log`
2. **Verify API keys**: Check `.env` file
3. **Test API manually**: Use curl commands
4. **Check GitHub issues**: Latest troubleshooting
5. **Rollback if needed**: Use previous commit

---

## 🎉 Ready to Test

Deployment complete! You can now test the enhanced `/whale` command with:

1. **Basic usage**: `/whale`
2. **Custom threshold**: `/whale 1M`
3. **Low threshold**: `/whale 250k`

The new multi-coin scanner provides comprehensive whale activity analysis across all major cryptocurrencies with real-time data from Hyperliquid exchange.

**Expected response time**: <10 seconds  
**Data freshness**: Real-time (within 30 seconds)  
**Reliability**: Built-in fallback for partial API failures

Good luck and happy whale watching! 🐋
