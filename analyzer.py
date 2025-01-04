from typing import Dict
from datetime import datetime
from config import Config
from state import State
from executor import Executor

def calculate_funding_cost(state: State) -> float:
    """
    Рассчитывает общую стоимость финансирования для всех активных хедж-позиций.
    
    Args:
        state: Текущее состояние стратегии
    
    Returns:
        float: Общая стоимость финансирования
    """
    total_funding_cost = 0
    current_time = datetime.now()
    
    for hedge_num in range(1, 4):
        hedge_key = f'h{hedge_num}'
        if state.hedge_states[hedge_key]:
            position_value = state.hedge_sizes[hedge_key] * state.current_price
            entry_time = state.hedge_entry_times[hedge_key]
            if entry_time:
                hours_passed = (current_time - entry_time).total_seconds() / 3600
                funding_periods = hours_passed / Config.HOURS_PER_FUNDING
                
                funding_cost = (
                    position_value * 
                    Config.FUNDING_RATE * 
                    funding_periods
                )
                total_funding_cost += funding_cost
    
    return total_funding_cost

def calculate_pnl(state: State, initial_price: float) -> Dict[str, float]:
    """
    Рассчитывает P&L (прибыль/убыток) для текущего состояния стратегии.
    
    Args:
        state: Текущее состояние стратегии
        initial_price: Начальная цена
    
    Returns:
        Dict[str, float]: Словарь с метриками P&L
    """
    # Текущая стоимость позиций
    current_value = state.current_eth * state.current_price + state.current_usd
    
    # Начальная стоимость
    initial_value = state.deposit
    
    # Расчет общего P&L
    total_pnl = current_value - initial_value
    
    # Расчет процентного P&L
    pnl_percentage = (total_pnl / initial_value) * 100 if initial_value > 0 else 0
    
    return {
        'total': total_pnl,
        'percentage': pnl_percentage
    }

if __name__ == "__main__":
    # Пример использования
    try:
        # Создаем тестовое состояние
        state = State()
        state.deposit = 1000
        state.current_price = 3607.85
        
        # Рассчитываем начальные позиции
        spot_allocation = state.deposit * Config.SPOT_ALLOCATION  # 75% = $750
        initial_eth_value = spot_allocation * 0.5  # 50% = $375
        state.initial_eth = initial_eth_value / state.current_price  # ≈ 0.104 ETH
        state.current_eth = state.initial_eth
        state.current_usd = spot_allocation * 0.5  # Оставшиеся $375
        
        # Обновляем объем для комиссий
        state.total_spot_volume = initial_eth_value  # Объем первой покупки ETH
        
        # Рассчитываем и выводим P&L
        pnl = calculate_pnl(state)
        print("\nP&L Breakdown:")
        print(f"Initial ETH: {state.initial_eth:.6f} ETH")
        print(f"ETH Value: ${state.current_eth * state.current_price:.2f}")
        print(f"USDT Balance: ${state.current_usd:.2f}")
        print(f"Total Value: ${(state.current_eth * state.current_price + state.current_usd):.2f}")
        print(f"Total P&L: ${pnl['total']}")
        print(f"Percentage P&L: {pnl['percentage']}%")
            
    except Exception as e:
        print(f"Error in main: {str(e)}") 