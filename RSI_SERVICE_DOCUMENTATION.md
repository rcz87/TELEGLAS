# RSI Service Documentation

## Overview

The RSI (Relative Strength Index) service provides market sentiment indicators for cryptocurrencies across multiple timeframes. This service has been added to `services/raw_data_service.py` and uses the CoinGlass API v4 indicators endpoint.

## New Method Added

### `get_rsi_1h_4h_1d(symbol: str) -> Dict[str, Any]`

**Description**: Fetches RSI data specifically for 1h, 4h, and 1d timeframes and formats it as requested.

**Parameters**:
- `symbol` (str): The cryptocurrency symbol (e.g., "BTC", "ETH", "SOL")

**Returns**: Dictionary with the following structure:
```python
{
    "rsi_1h": float or None,        # RSI value for 1h timeframe
    "rsi_4h": float or None,        # RSI value for 4h timeframe  
    "rsi_1d": float or None,        # RSI value for 1d timeframe
    "rsi_summary": str,              # Formatted string: "RSI (1h/4h/1d): 62.37/63.96/22.05"
    "raw_data": {                    # Raw data for all timeframes
        "1h": float or None,
        "4h": float or None,
        "1d": float or None
    }
}
```

## Usage Examples

### Basic Usage

```python
from services.raw_data_service import raw_data_service

# Get RSI data for Bitcoin
result = await raw_data_service.get_rsi_1h_4h_1d('BTC')

# Access individual RSI values
rsi_1h = result['rsi_1h']
rsi_4h = result['rsi_4h']
rsi_1d = result['rsi_1d']

# Get formatted summary string
summary = result['rsi_summary']
print(summary)  # Output: "RSI (1h/4h/1d): 62.37/63.96/22.05"
```

### Error Handling

```python
try:
    result = await raw_data_service.get_rsi_1h_4h_1d('BTC')
    
    if result['rsi_1h'] is not None:
        print(f"RSI 1h: {result['rsi_1h']:.2f}")
    else:
        print("RSI 1h data not available")
        
except Exception as e:
    print(f"Error fetching RSI data: {e}")
```

### Multiple Symbols

```python
symbols = ["BTC", "ETH", "SOL"]

for symbol in symbols:
    result = await raw_data_service.get_rsi_1h_4h_1d(symbol)
    print(f"{symbol}: {result['rsi_summary']}")
```

## RSI Interpretation

- **RSI > 70**: Overbought condition (potential sell signal)
- **RSI < 30**: Oversold condition (potential buy signal)
- **RSI 30-70**: Normal trading range
- **RSI ~50**: Neutral sentiment

## Technical Details

### API Endpoint
- Uses CoinGlass API v4: `/api/futures/indicators/rsi`
- Exchange: Binance (default)
- Window: 14 periods (standard RSI setting)
- Series Type: Close price

### Data Validation
- RSI values are validated to be within 0-100 range
- Invalid values are set to `None` and logged as warnings
- 0.00 values are considered valid and may indicate actual market conditions

### Error Handling
- Network errors are logged and return `None` values
- Invalid RSI values (>100 or <0) are rejected and set to `None`
- API errors return formatted "N/A" values

### Performance
- Fetches all three timeframes concurrently for efficiency
- Uses async/await pattern for non-blocking operations
- Caches API responses where applicable

## Integration Points

This service can be integrated with:

1. **Telegram Bot**: Add RSI summaries to market updates
2. **Trading Signals**: Combine with other indicators for decision making
3. **Market Analysis**: Use in automated market sentiment analysis
4. **Alert Systems**: Trigger alerts when RSI crosses thresholds

## Testing

A comprehensive test suite is available in `test_rsi_service.py`:

```bash
python test_rsi_service.py
```

The test verifies:
- ✅ Correct API connectivity
- ✅ Proper format of output string
- ✅ Valid RSI value ranges (0-100)
- ✅ Error handling for invalid symbols
- ✅ Multiple symbol support

## Example Output

```
BTC: RSI (1h/4h/1d): 62.37/63.96/22.05
ETH: RSI (1h/4h/1d): 45.23/48.91/52.67
SOL: RSI (1h/4h/1d): N/A/N/A/N/A
```

## Rate Limits

The service respects CoinGlass API rate limits:
- Standard tier: ~120 calls per minute
- Requests are spaced automatically
- Failed requests are retried with exponential backoff

## Dependencies

- `services.coinglass_api`: CoinGlass API wrapper
- `asyncio`: For concurrent API calls
- `loguru`: For structured logging
- `typing`: For type hints

## Future Enhancements

Potential improvements:
1. **Customizable timeframes**: Allow users to specify custom intervals
2. **Multiple exchanges**: Add support for other exchanges beyond Binance
3. **RSI divergence detection**: Identify bullish/bearish divergences
4. **Historical RSI trends**: Track RSI changes over time
5. **Alert thresholds**: Configurable RSI alert levels

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify CoinGlass API key is valid and active
3. Ensure symbol is supported by CoinGlass
4. Run the test suite to verify functionality
