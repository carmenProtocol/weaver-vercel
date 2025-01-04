import time
from typing import Optional, Dict
from datetime import datetime
from data_fetcher import create_okx_exchange, get_current_price, get_balance
from scanner import scan_market
from strategy import (
    initialize_strategy,
    manage_hedges,
    buy_on_lower,
    rebalance_at_entry,
    calculate_hedge_sizes,
    exit_all_positions
)
from executor import Executor
from analyzer import calculate_pnl
from state import State
from config import Config, TradingPairConfig
import asyncio

# Trading parameters
SYMBOL = TradingPairConfig.TRADING_PAIR
SLEEP_TIME = 10  # Sleep time in seconds between iterations
STATUS_INTERVAL = 3600  # Status update interval in seconds

async def print_strategy_info(state: State, pnl: Dict[str, float], message: str, initial_price: float, logger=None) -> None:
    """
    Выводит подробную информацию о состоянии стратегии.
    
    Args:
        state: Текущее состояние стратегии
        pnl: Словарь с метриками P&L
        message: Сообщение о текущем действии стратегии
        initial_price: Начальная цена
        logger: Логгер для записи в Supabase
    """
    print(f"\n=== {message} ===")
    print(f"Текущая цена: ${state.current_price:.2f}")
    print(f"Изменение цены: {((state.current_price - initial_price) / initial_price * 100):.2f}%")
    print(f"ETH баланс: {state.current_eth:.6f} ETH (${state.current_eth * state.current_price:.2f})")
    print(f"USDT баланс: ${state.current_usd:.2f}")
    print(f"P&L: ${pnl['total']:.2f} ({pnl['percentage']:.2f}%)")
    
    if logger:
        await logger.update_state(state)
        await logger.log_pnl(pnl)
    
    if state.hedges:
        print("\nАктивные хеджи:")
        for hedge_num, hedge in state.hedges.items():
            print(f"Хедж {hedge_num}: {hedge['size']:.4f} контрактов по ${hedge['price']:.2f}")
        
        if logger:
            await logger.log_hedges(state.hedges)
    
    print("=" * 50 + "\n")

async def main_loop(state: State, current_price: float, executor: Executor, initial_price: float, logger=None) -> State:
    """
    Основной цикл торговой стратегии.
    """
    state.current_price = current_price
    last_action = None
    action_type = None

    # Управление хеджами
    if state.current_price < state.entry_price:
        manage_hedges(state)
        if state.hedges != state.prev_hedges:
            last_action = "Обновление хедж-позиций"
            action_type = "hedge"
            state.prev_hedges = state.hedges.copy()

    # Покупка при снижении
    if state.current_price <= state.buffer:
        buy_on_lower(state)
        last_action = "Покупка при снижении цены"
        action_type = "buy"

    # Ребалансировка при возврате к entry
    if state.buffer < state.current_price <= state.entry_price * 1.01:
        rebalance_at_entry(state)
        if state.current_price > state.entry_price:
            last_action = "Ребалансировка при возврате к точке входа"
            action_type = "rebalance"

    # Если была торговая операция, выводим информацию
    if last_action:
        pnl = calculate_pnl(state, initial_price)
        await print_strategy_info(state, pnl, last_action, initial_price, logger)
        
        if logger:
            await logger.write(last_action, log_type='trade', action=action_type)

    return state

async def main(logger=None):
    """
    Основная функция торгового бота.
    """
    try:
        print("\n=== Инициализация торговой стратегии ===")
        if logger:
            await logger.write("Инициализация торговой стратегии", log_type='info', action='init')
        
        # Создаем подключение к бирже
        exchange = create_okx_exchange()
        print("Проверка подключения к бирже...")
        await exchange.load_markets()
        print("Подключение успешно!")
        
        if logger:
            await logger.write("Подключение к бирже успешно", log_type='info', action='connect')
        
        # Создаем исполнителя
        executor = Executor(exchange)
        
        # Получаем начальные данные
        current_price = await get_current_price(exchange, SYMBOL)
        if not current_price:
            raise Exception("Не удалось получить текущую цену")
        
        usdt_balance, eth_balance = await get_balance(exchange)
        initial_deposit = usdt_balance + (eth_balance * current_price)
        
        # Инициализируем состояние
        state = initialize_strategy(current_price, initial_deposit)
        state.update_balances(eth_balance, usdt_balance)
        
        print(f"\nНачальные параметры:")
        print(f"Цена ETH: ${current_price:.2f}")
        print(f"Общий депозит: ${initial_deposit:.2f}")
        print(f"USDT баланс: ${usdt_balance:.2f}")
        print(f"ETH баланс: {eth_balance:.6f} (${eth_balance * current_price:.2f})")
        
        # Выполняем начальную покупку ETH
        if eth_balance < state.initial_eth:
            eth_to_buy = state.initial_eth - eth_balance
            print(f"\n=== Выполняем начальную покупку {eth_to_buy:.6f} ETH ===")
            await executor.buy_eth(current_price, eth_to_buy)
            
            # Обновляем балансы после покупки
            usdt_balance, eth_balance = await get_balance(exchange)
            state.update_balances(eth_balance, usdt_balance)
            
            print(f"Новый ETH баланс: {eth_balance:.6f} ETH (${eth_balance * current_price:.2f})")
            print(f"Новый USDT баланс: ${usdt_balance:.2f}")
        
        print("=== Стратегия инициализирована ===\n")
        
        # Основной торговый цикл
        last_status_time = time.time()
        initial_price = current_price
        
        while True:
            try:
                current_time = time.time()
                
                # Получаем текущие данные рынка
                current_price = await scan_market(SYMBOL)
                if not current_price:
                    error_msg = "Предупреждение: Не удалось получить текущую цену, пропускаем итерацию"
                    print(error_msg)
                    if logger:
                        await logger.write(error_msg, log_type='warning', action='market_scan')
                    continue
                
                # Получаем текущие балансы только если прошел интервал или была торговля
                if current_time - last_status_time >= STATUS_INTERVAL:
                    usdt_balance, eth_balance = await get_balance(exchange)
                    state.update_balances(eth_balance, usdt_balance)
                    pnl = calculate_pnl(state, initial_price)
                    await print_strategy_info(state, pnl, "Периодический статус", initial_price, logger)
                    last_status_time = current_time
                
                # Выполняем основной цикл
                state = await main_loop(state, current_price, executor, initial_price, logger)
                
                # Пауза перед следующей итерацией
                await asyncio.sleep(SLEEP_TIME)
                
            except Exception as e:
                error_msg = f"Ошибка в торговом цикле: {str(e)}"
                print(error_msg)
                if logger:
                    await logger.write(error_msg, log_type='error', action='trading_loop', is_error=True)
                await asyncio.sleep(SLEEP_TIME)
                continue
    
    except Exception as e:
        error_msg = f"Критическая ошибка: {str(e)}"
        print(error_msg)
        if logger:
            await logger.write(error_msg, log_type='error', action='critical', is_error=True)
        return

if __name__ == "__main__":
    asyncio.run(main()) 