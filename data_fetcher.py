import os
import ccxt
from dotenv import load_dotenv
from typing import Tuple, Optional

# Загружаем переменные окружения
load_dotenv()

def create_okx_exchange() -> ccxt.okx:
    """
    Создает подключение к бирже OKX с настройками из .env файла.
    
    Returns:
        ccxt.okx: Инстанс биржи OKX
    """
    api_key = os.getenv('OKX_API_KEY')
    api_secret = os.getenv('OKX_SECRET_KEY')
    password = os.getenv('OKX_PASSWORD')
    testnet = os.getenv('TESTNET', 'true').lower() == 'true'
    
    if not all([api_key, api_secret, password]):
        raise ValueError("Missing API credentials in .env file")
    
    print(f"API Key: {api_key}")
    print(f"Secret Key: {api_secret}")
    print(f"Password: {password}")
    print(f"Testnet: {testnet}")
    
    exchange = ccxt.okx({
        'apiKey': api_key,
        'secret': api_secret,
        'password': password,
        'enableRateLimit': True
    })
    
    if testnet:
        exchange.set_sandbox_mode(True)
    
    return exchange

def get_current_price(exchange: ccxt.okx, symbol: str) -> Optional[float]:
    """
    Получает текущую цену торговой пары.
    
    Args:
        exchange: Инстанс биржи OKX
        symbol: Торговая пара (например, 'ETH/USDT')
    
    Returns:
        Optional[float]: Текущая цена или None в случае ошибки
    """
    try:
        ticker = exchange.fetch_ticker(symbol)
        return float(ticker['last'])
    except Exception as e:
        print(f"Error fetching price: {str(e)}")
        return None

def get_balance(exchange: ccxt.okx) -> Tuple[float, float]:
    """
    Получает текущие балансы USDT и ETH.
    
    Args:
        exchange: Инстанс биржи OKX
    
    Returns:
        Tuple[float, float]: (USDT баланс, ETH баланс)
    """
    try:
        balance = exchange.fetch_balance()
        
        # Получаем только доступные (не в ордерах) балансы
        usdt_balance = float(balance.get('USDT', {}).get('free', 0))
        eth_balance = float(balance.get('ETH', {}).get('free', 0))
        
        print(f"Fetched balances - USDT: ${usdt_balance:.2f}, ETH: {eth_balance:.6f}")
        return usdt_balance, eth_balance
        
    except Exception as e:
        print(f"Error fetching balance: {str(e)}")
        return 0.0, 0.0

if __name__ == "__main__":
    try:
        # Создаем подключение к бирже
        exchange = create_okx_exchange()
        
        # Проверяем подключение
        print("\nTesting exchange connection...")
        exchange.load_markets()
        print("Connection successful!")
        
        # Получаем текущую цену ETH
        symbol = 'ETH/USDT'
        price = get_current_price(exchange, symbol)
        print(f"\nCurrent {symbol} price: ${price:.2f}")
        
        # Получаем балансы
        usdt_balance, eth_balance = get_balance(exchange)
        print(f"USDT balance: ${usdt_balance:.2f}")
        print(f"ETH balance: {eth_balance:.6f} (${eth_balance * price:.2f})")
        
    except Exception as e:
        print(f"Error in main: {str(e)}") 