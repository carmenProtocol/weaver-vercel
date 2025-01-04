from typing import Dict
from dataclasses import dataclass
from enum import Enum

class Config:
    # Комиссии
    SPOT_COMMISSION = 0.001  # 0.1% для спота
    FUTURES_COMMISSION = 0.0004  # 0.04% для фьючерсов
    
    # Финансирование
    FUNDING_RATE = 0.0001  # 0.01% за 8 часов
    HOURS_PER_FUNDING = 8
    
    # Риск-менеджмент
    MAX_LEVERAGE = 10
    
    # Границы
    UPPER_BOUND_MULT = 1.06  # +6%
    LOWER_BOUND_MULT = 0.94  # -6%
    BUFFER_MULT = 0.92      # -8%
    
    # Распределение депозита
    SPOT_ALLOCATION = 0.75   # 75% на спот
    HEDGE_ALLOCATION = 0.25  # 25% на хедж

# Strategy states для отслеживания состояния
class StrategyState(Enum):
    INITIALIZING = "initializing"
    SCANNING = "scanning"
    WAITING = "waiting"
    ENTERING_POSITION = "entering_position"
    IN_POSITION = "in_position"
    EXITING_POSITION = "exiting_position"
    HEDGING = "hedging"
    REBALANCING = "rebalancing"
    STOPPED = "stopped"
    ERROR = "error"

# Exchange configuration
class ExchangeConfig:
    API_KEY: str = ""
    API_SECRET: str = ""
    API_PASSWORD: str = ""
    EXCHANGE_ID: str = "okx"
    TESTNET: bool = True

# Trading pair configuration
class TradingPairConfig:
    BASE_CURRENCY: str = "ETH"
    QUOTE_CURRENCY: str = "USDT"
    TRADING_PAIR: str = f"{BASE_CURRENCY}/{QUOTE_CURRENCY}"
    CONTRACT_SIZE: float = 1.0 