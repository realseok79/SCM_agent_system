from dataclasses import dataclass

@dataclass
class DataDTO:
    """Data Agent → Analysis Agent"""
    timestamp: str
    day: int
    daily_demand: float
    current_stock: float
    lead_time_days: float
    weather_index: float
    macro_trend: float

@dataclass
class InventorySignalDTO:
    """Analysis Agent → Action Agent"""
    timestamp: str
    day: int
    safety_stock: float
    reorder_point: float
    optimal_order_qty: float
    confidence_level: float
    alert_level: str   # "NORMAL" | "WARNING" | "CRITICAL"
