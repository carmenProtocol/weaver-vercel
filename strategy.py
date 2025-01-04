from datetime import datetime
from typing import Dict, Optional
from config import Config
from state import State

def initialize_strategy(current_price: float, deposit: float) -> State:
    """
    Инициализирует торговую стратегию с начальными параметрами.
    
    Args:
        current_price: Текущая цена торговой пары
        deposit: Начальный депозит в USDT
    
    Returns:
        State: Инициализированное состояние стратегии
    """
    state = State()
    
    # Основные параметры
    state.entry_price = current_price
    state.current_price = current_price
    state.deposit = deposit
    
    # Расчет границ
    state.upper = current_price * Config.UPPER_BOUND_MULT  # +6%
    state.lower = current_price * Config.LOWER_BOUND_MULT  # -6%
    state.buffer = current_price * Config.BUFFER_MULT      # -8%
    
    # Расчет начальных позиций
    spot_allocation = deposit * Config.SPOT_ALLOCATION     # 75% на спот
    state.initial_eth = (spot_allocation * 0.5) / current_price  # Половина на ETH
    state.current_eth = state.initial_eth
    state.current_usd = spot_allocation * 0.5              # Половина в USDT
    
    # Расчет уровней хеджа
    state.hedge_levels = {
        'h1': current_price * 0.98,  # -2%
        'h2': current_price * 0.96,  # -4%
        'h3': current_price * 0.94   # -6%
    }
    
    return state

def calculate_hedge_sizes(state: State) -> None:
    """
    Рассчитывает размеры хедж-позиций на основе текущего состояния.
    
    Args:
        state: Текущее состояние стратегии
    """
    max_loss = state.current_eth * (state.current_price - state.buffer)
    
    state.hedge_sizes = {
        'h1': max_loss * 0.2 / (state.hedge_levels['h1'] - state.buffer),
        'h2': max_loss * 0.3 / (state.hedge_levels['h2'] - state.buffer),
        'h3': max_loss * 0.5 / (state.hedge_levels['h3'] - state.buffer)
    }
    
    # Валидация плеча
    validate_leverage(state)

def validate_leverage(state: State) -> bool:
    """
    Проверяет, не превышает ли требуемое плечо максимально допустимое.
    
    Args:
        state: Текущее состояние стратегии
    
    Returns:
        bool: True если плечо в пределах нормы, иначе ValueError
    """
    total_position_value = sum(
        size * state.hedge_levels[f'h{i}']
        for i, size in enumerate(state.hedge_sizes.values(), 1)
    )
    
    hedge_allocation = state.deposit * Config.HEDGE_ALLOCATION
    required_leverage = total_position_value / hedge_allocation
    
    if required_leverage > Config.MAX_LEVERAGE:
        raise ValueError(f"Required leverage ({required_leverage:.2f}x) exceeds maximum allowed")
    
    return True

def manage_hedges(state: State) -> None:
    """
    Управляет открытием хедж-позиций на основе текущей цены.
    
    Args:
        state: Текущее состояние стратегии
    """
    for i in range(1, 4):
        hedge_key = f'h{i}'
        if (state.current_price <= state.hedge_levels[hedge_key] 
            and not state.hedge_states[hedge_key]):
            open_hedge(state, i)

def open_hedge(state: State, hedge_num: int) -> None:
    """
    Открывает новую хедж-позицию.
    
    Args:
        state: Текущее состояние стратегии
        hedge_num: Номер хедж-позиции (1-3)
    """
    hedge_key = f'h{hedge_num}'
    
    # Открытие позиции
    state.hedge_states[hedge_key] = True
    state.hedge_entries[hedge_key] = state.current_price
    state.hedge_entry_times[hedge_key] = datetime.now()
    
    # Обновление объема для комиссий
    position_value = state.hedge_sizes[hedge_key] * state.current_price
    state.total_futures_volume += position_value

def close_hedge(state: State, hedge_num: int) -> float:
    """
    Закрывает хедж-позицию и возвращает P&L.
    
    Args:
        state: Текущее состояние стратегии
        hedge_num: Номер хедж-позиции (1-3)
    
    Returns:
        float: P&L от закрытия позиции
    """
    hedge_key = f'h{hedge_num}'
    if state.hedge_states[hedge_key]:
        # Расчет P&L
        size = state.hedge_sizes[hedge_key]
        entry_price = state.hedge_entries[hedge_key]
        pnl = size * (entry_price - state.current_price)
        
        # Закрытие позиции
        state.hedge_states[hedge_key] = False
        state.hedge_sizes[hedge_key] = 0
        state.hedge_entries[hedge_key] = 0
        state.hedge_entry_times[hedge_key] = None
        
        return pnl
    return 0

def buy_on_lower(state: State) -> None:
    """
    Покупает ETH при достижении нижней границы.
    
    Args:
        state: Текущее состояние стратегии
    """
    eth_to_buy = state.current_usd / state.current_price
    
    # Обновление позиций
    state.current_eth += eth_to_buy
    state.current_usd = 0
    
    # Обновление объема для комиссий
    state.total_spot_volume += eth_to_buy * state.current_price
    
    # Пересчет размеров хеджа
    calculate_hedge_sizes(state)

def rebalance_at_entry(state: State) -> None:
    """
    Ребалансирует позиции при возврате к точке входа.
    
    Args:
        state: Текущее состояние стратегии
    """
    eth_to_sell = state.current_eth * 0.5
    sale_proceeds = eth_to_sell * state.current_price
    
    # Обновление позиций
    state.current_eth -= eth_to_sell
    state.current_usd += sale_proceeds
    
    # Обновление объема для комиссий
    state.total_spot_volume += sale_proceeds
    
    # Закрытие лишних хеджей
    close_hedge(state, 3)
    close_hedge(state, 2)
    
    # Пересчет размера первого хеджа
    calculate_hedge_sizes(state)

def exit_all_positions(state: State) -> float:
    """
    Закрывает все позиции и возвращает общий P&L.
    
    Args:
        state: Текущее состояние стратегии
    
    Returns:
        float: Общий P&L от закрытия всех позиций
    """
    # Закрытие всех хеджей
    total_pnl = 0
    for i in range(1, 4):
        total_pnl += close_hedge(state, i)
    
    # Продажа всего ETH
    eth_value = state.current_eth * state.current_price
    total_pnl += eth_value + state.current_usd - state.deposit
    
    return total_pnl 

def calculate_delta_spot(state: State, initial_price: float) -> float:
    """
    Рассчитывает дельту спот позиции в USD.
    
    Args:
        state: Текущее состояние стратегии
        initial_price: Начальная цена входа
    
    Returns:
        float: Дельта спот позиции в USD
    """
    current_spot_value = state.current_eth * state.current_price
    initial_spot_value = state.initial_eth * initial_price
    return current_spot_value - initial_spot_value

def calculate_delta_hedge(state: State) -> float:
    """
    Рассчитывает дельту хедж позиций в USD.
    
    Args:
        state: Текущее состояние стратегии
    
    Returns:
        float: Дельта хедж позиций в USD
    """
    total_hedge_pnl = 0.0
    for hedge_num in range(1, 4):
        hedge_key = f'h{hedge_num}'
        if state.hedge_states[hedge_key]:
            size = state.hedge_sizes[hedge_key]
            entry_price = state.hedge_entries[hedge_key]
            hedge_pnl = size * (entry_price - state.current_price)
            total_hedge_pnl += hedge_pnl
    return total_hedge_pnl 