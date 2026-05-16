import numpy as np
from datetime import datetime
from dto.schemas import DataDTO, InventorySignalDTO, AlertLevel

class AnalysisAgent:
    def __init__(self):
        print("AnalysisAgent initialized")

    def analyze(self, data: DataDTO) -> InventorySignalDTO:
        """
        확률론적 재고 최적화 함수
        DataAgent로부터 전달받은 히스토리 데이터를 기반으로 통계적 기댓값 산출
        """
        # 1. 수요 및 리드타임 통계 분석
        # 첫날부터 데이터가 쌓이므로 np.mean/std 연산이 가능함
        avg_demand = np.mean(data.history_demand) if data.history_demand else data.daily_demand
        std_demand = np.std(data.history_demand) if len(data.history_demand) > 1 else 10.0
        
        avg_lt = np.mean(data.history_lead_time) if data.history_lead_time else data.lead_time_days
        std_lt = np.std(data.history_lead_time) if len(data.history_lead_time) > 1 else 1.0

        # 2. 안전 재고(Safety Stock) 계산 (서비스 레벨 95% -> Z=1.65)
        # SS = Z * sqrt(avg_lt * std_demand^2 + avg_demand^2 * std_lt^2)
        z_score = 1.65
        safety_stock = z_score * np.sqrt(avg_lt * (std_demand**2) + (avg_demand**2) * (std_lt**2))

        # 3. 재주문점(Reorder Point) 계산
        # ROP = (Average Daily Demand * Average Lead Time) + Safety Stock
        reorder_point = (avg_demand * avg_lt) + safety_stock

        # 4. 최적 발주량 결정 (EOQ 또는 부족분 보충)
        optimal_order_qty = 0.0
        alert_level = AlertLevel.NORMAL
        
        if data.current_stock <= reorder_point:
            # 부족분만큼 발주 (간이 로직)
            optimal_order_qty = max(0.0, reorder_point * 1.5 - data.current_stock)
            alert_level = AlertLevel.WARNING if data.current_stock > safety_stock else AlertLevel.CRITICAL

        return InventorySignalDTO(
            timestamp=datetime.now().isoformat(),
            day=data.day,
            safety_stock=round(float(safety_stock), 1),
            reorder_point=round(float(reorder_point), 1),
            optimal_order_qty=round(float(optimal_order_qty), 1),
            confidence_level=0.95,
            alert_level=alert_level
        )
