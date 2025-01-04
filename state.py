from datetime import datetime
from typing import Dict, Optional
from config import Config, StrategyState

class State:
    """
    Manages the complete state of the trading strategy.
    """
    
    def __init__(self):
        # Основные параметры
        self.entry_price: float = 0.0
        self.current_price: float = 0.0
        self.deposit: float = 0.0
        
        # Границы
        self.upper: float = 0.0
        self.lower: float = 0.0
        self.buffer: float = 0.0
        
        # Балансы
        self.initial_eth: float = 0.0
        self.current_eth: float = 0.0
        self.current_usd: float = 0.0
        
        # Хеджи
        self.hedges: Dict[str, Dict[str, float]] = {}
        self.prev_hedges: Dict[str, Dict[str, float]] = {}  # Для отслеживания изменений
        self.hedge_levels: Dict[str, float] = {}
        
        # Хедж уровни и размеры
        self.hedge_sizes: Dict[str, float] = {'h1': 0, 'h2': 0, 'h3': 0}
        self.hedge_states: Dict[str, bool] = {'h1': False, 'h2': False, 'h3': False}
        self.hedge_entries: Dict[str, float] = {'h1': 0, 'h2': 0, 'h3': 0}
        self.hedge_entry_times: Dict[str, Optional[datetime]] = {
            'h1': None, 'h2': None, 'h3': None
        }
        
        # Объемы для комиссий
        self.total_spot_volume: float = 0
        self.total_futures_volume: float = 0
        
        # Статус стратегии
        self.status: StrategyState = StrategyState.INITIALIZING
        
    def update_price(self, price: float) -> None:
        """Updates the current price"""
        self.current_price = price
        
    def update_balances(self, eth_balance: float, usdt_balance: float) -> None:
        """
        Обновляет балансы в состоянии.
        
        Args:
            eth_balance: Баланс ETH
            usdt_balance: Баланс USDT
        """
        self.current_eth = eth_balance
        self.current_usd = usdt_balance
        
    def get_total_position_value(self) -> float:
        """Calculates total position value in USD"""
        return self.current_eth * self.current_price + self.current_usd
    
    def get_total_hedge_value(self) -> float:
        """Calculates total hedge position value"""
        return sum(
            self.hedge_sizes[k] * self.current_price 
            for k, active in self.hedge_states.items() 
            if active
        )
    
    def get_active_hedges(self) -> Dict[str, float]:
        """Returns dictionary of active hedge positions"""
        return {
            k: self.hedge_sizes[k] 
            for k, active in self.hedge_states.items() 
            if active
        }
    
    def to_dict(self) -> Dict:
        """Converts state to dictionary for persistence"""
        return {
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "deposit": self.deposit,
            "upper": self.upper,
            "lower": self.lower,
            "buffer": self.buffer,
            "initial_eth": self.initial_eth,
            "current_eth": self.current_eth,
            "current_usd": self.current_usd,
            "hedge_levels": self.hedge_levels,
            "hedge_sizes": self.hedge_sizes,
            "hedge_states": self.hedge_states,
            "hedge_entries": self.hedge_entries,
            "hedge_entry_times": {
                k: v.isoformat() if v else None 
                for k, v in self.hedge_entry_times.items()
            },
            "total_spot_volume": self.total_spot_volume,
            "total_futures_volume": self.total_futures_volume,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'State':
        """Creates State instance from dictionary"""
        state = cls()
        state.entry_price = data["entry_price"]
        state.current_price = data["current_price"]
        state.deposit = data["deposit"]
        state.upper = data["upper"]
        state.lower = data["lower"]
        state.buffer = data["buffer"]
        state.initial_eth = data["initial_eth"]
        state.current_eth = data["current_eth"]
        state.current_usd = data["current_usd"]
        state.hedge_levels = data["hedge_levels"]
        state.hedge_sizes = data["hedge_sizes"]
        state.hedge_states = data["hedge_states"]
        state.hedge_entries = data["hedge_entries"]
        state.hedge_entry_times = {
            k: datetime.fromisoformat(v) if v else None 
            for k, v in data["hedge_entry_times"].items()
        }
        state.total_spot_volume = data["total_spot_volume"]
        state.total_futures_volume = data["total_futures_volume"]
        state.status = StrategyState(data["status"])
        return state 