from typing import List
from dataclasses import dataclass

@dataclass
class OptimizationConfig:
    """Configuration data class for optimization parameters."""
    freqtrade_path: str
    exchange: str
    pair_data_exchange: str
    timeframe: str
    timerange: str
    pairs: List[str]
    hyperfunction: str
    epochs: int = 200
    timeout: int = 3600  # 1 hour timeout per optimization