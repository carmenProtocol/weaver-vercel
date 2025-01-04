from typing import Optional
from data_fetcher import create_okx_exchange, get_current_price
from config import TradingPairConfig

def scan_market(symbol: str) -> Optional[float]:
    """
    Scans the market for the current price of a given symbol.
    This is a basic implementation that only fetches the current price.
    More complex scanning logic will be added later.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
    
    Returns:
        Optional[float]: Current price if available, None if there's an error
    """
    try:
        # Create exchange instance
        exchange = create_okx_exchange()
        
        # Get current price
        current_price = get_current_price(exchange, symbol)
        
        # Return None if price is 0 (indicating an error)
        if current_price == 0:
            return None
            
        return current_price
        
    except Exception as e:
        print(f"Error scanning market for {symbol}: {str(e)}")
        return None

if __name__ == "__main__":
    # Example usage
    try:
        # Use the default trading pair from config
        symbol = TradingPairConfig.TRADING_PAIR
        
        # Scan market
        price = scan_market(symbol)
        
        if price is not None:
            print(f"Current price for {symbol}: {price}")
        else:
            print(f"Failed to get price for {symbol}")
            
    except Exception as e:
        print(f"Error in main: {str(e)}") 