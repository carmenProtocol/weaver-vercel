import ccxt
import time
from typing import Dict, Optional
from datetime import datetime
from data_fetcher import create_okx_exchange
from config import Config, TradingPairConfig

class Executor:
    """
    Выполняет торговые операции на бирже OKX.
    """
    
    def __init__(self):
        """Инициализирует экземпляр Executor с подключением к OKX."""
        self.exchange = create_okx_exchange()
        self.symbol = TradingPairConfig.TRADING_PAIR
        self.total_commission = 0.0
        
    def _create_market_order(self, side: str, amount: float) -> Dict:
        """
        Создает рыночный ордер с указанными параметрами.
        
        Args:
            side: Сторона ордера ('buy' или 'sell')
            amount: Объем в базовой валюте
            
        Returns:
            Dict: Ответ от биржи с информацией об ордере
        """
        try:
            # Проверяем подключение к бирже
            if not self.exchange:
                raise ValueError("No exchange connection")
                
            # Получаем текущую цену
            current_price = self.exchange.fetch_ticker(self.symbol)['last']
            
            # Проверяем баланс перед созданием ордера
            if side == 'buy':
                quote_balance = self.exchange.fetch_balance()['USDT']['free']
                required_amount = amount * current_price
                if quote_balance < required_amount:
                    raise ValueError(f"Insufficient USDT balance. Required: {required_amount}, Available: {quote_balance}")
            else:  # sell
                base_balance = self.exchange.fetch_balance()['ETH']['free']
                if base_balance < amount:
                    raise ValueError(f"Insufficient ETH balance. Required: {amount}, Available: {base_balance}")
            
            # Создаем ордер
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=amount,
                params={'tdMode': 'cash'}  # Используем спотовый режим
            )
            
            print(f"Creating {side} order: {amount:.6f} {self.symbol} at ~${current_price:.2f}")
            
            # Ждем исполнения ордера
            while True:
                order_status = self.exchange.fetch_order(order['id'], self.symbol)
                if order_status['status'] == 'closed':
                    break
                time.sleep(0.5)
            
            # Получаем комиссию из исполненного ордера
            if 'fee' in order_status and order_status['fee'] is not None:
                fee_cost = float(order_status['fee']['cost'])
                self.total_commission += fee_cost
                print(f"Order executed. Fee: ${fee_cost:.4f}")
                print(f"Total commission so far: ${self.total_commission:.4f}")
            
            # Выводим информацию об исполненном ордере
            executed_price = float(order_status['average'])
            executed_amount = float(order_status['filled'])
            executed_value = executed_price * executed_amount
            print(f"Order filled: {executed_amount:.6f} {self.symbol} @ ${executed_price:.2f} (Total: ${executed_value:.2f})")
            
            return order_status
            
        except Exception as e:
            print(f"Error creating {side} order: {str(e)}")
            raise
    
    def buy_eth(self, price: float, amount: float) -> Dict:
        """
        Создает рыночный ордер на покупку ETH.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Объем ETH для покупки
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Buying {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('buy', amount)
    
    def sell_eth(self, price: float, amount: float) -> Dict:
        """
        Создает рыночный ордер на продажу ETH.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Объем ETH для продажи
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Selling {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('sell', amount)
    
    def open_hedge(self, price: float, amount: float) -> Dict:
        """
        Открывает хедж-позицию через рыночный ордер на продажу.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Объем ETH для хеджирования
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Opening hedge position: Selling {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('sell', amount)
    
    def close_hedge(self, price: float, amount: float) -> Dict:
        """
        Закрывает хедж-позицию через рыночный ордер на покупку.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Объем ETH для закрытия хеджа
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Closing hedge position: Buying {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('buy', amount)
    
    def close_all_hedges(self, price: float, amount: float) -> Dict:
        """
        Закрывает все хедж-позиции одним рыночным ордером.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Общий объем ETH для закрытия всех хеджей
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Closing all hedge positions: Buying {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('buy', amount)
    
    def sell_all_eth(self, price: float, amount: float) -> Dict:
        """
        Продает весь имеющийся ETH одним рыночным ордером.
        
        Args:
            price: Текущая рыночная цена (для логирования)
            amount: Весь доступный объем ETH
            
        Returns:
            Dict: Информация об исполненном ордере
        """
        print(f"Selling all ETH: {amount} ETH at market price (currently {price:.2f})")
        return self._create_market_order('sell', amount)
    
    def get_total_commission(self) -> float:
        """Возвращает общую сумму комиссий."""
        return self.total_commission

if __name__ == "__main__":
    # Пример использования
    try:
        # Создаем экземпляр исполнителя
        executor = Executor()
        
        # Тестовые значения
        current_price = 2000.0  # Пример цены ETH
        trade_amount = 0.1     # Пример объема сделки
        
        # Тестируем покупку и продажу
        buy_order = executor.buy_eth(current_price, trade_amount)
        print(f"Buy order created: {buy_order}\n")
        
        sell_order = executor.sell_eth(current_price, trade_amount)
        print(f"Sell order created: {sell_order}\n")
        
        # Тестируем операции с хеджами
        hedge_order = executor.open_hedge(current_price, trade_amount)
        print(f"Hedge order created: {hedge_order}\n")
        
        close_hedge_order = executor.close_hedge(current_price, trade_amount)
        print(f"Close hedge order created: {close_hedge_order}")
        
    except Exception as e:
        print(f"Error in main: {str(e)}") 