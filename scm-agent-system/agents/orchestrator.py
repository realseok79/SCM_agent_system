# agents/orchestrator.py
import os
import math
import numpy as np
from datetime import datetime
from utils.logger import get_logger
from dto.schemas import AlertLevel, InventorySignalDTO, StressEvent
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent
from db import get_db_connection

logger = get_logger("AgentOrchestrator")

class AgentOrchestrator:
    """
    [고도화 B1] 에이전트 오케스트레이터
    에이전트 간의 절차적 결합을 느슨하게 하고, 다중 SKU 시뮬레이션 파이프라인과
    SCM 핵심 SLA KPI(Fill Rate, Inventory Turnover) 연산 및 추적을 총괄합니다.
    """
    def __init__(self):
        self.skus = ["반도체 칩", "마스크", "종합 품목"]
        self.data_agents = {sku: DataAgent() for sku in self.skus}
        self.analysis_agent = AnalysisAgent()
        self.action_agent = ActionAgent()

        # 각 SKU별 가상 창고 재고 및 입고 큐 관리
        self.current_stocks = {
            "반도체 칩": 1500.0,
            "마스크": 1000.0,
            "종합 품목": 2000.0
        }
        self.arrival_queues = {sku: {} for sku in self.skus}

        # SLA KPI 누적 트래킹용 변수
        self.cumulative_demand = {sku: 0.0 for sku in self.skus}
        self.cumulative_fulfilled = {sku: 0.0 for sku in self.skus}
        self.stock_history = {sku: [] for sku in self.skus}
        
        logger.info("AgentOrchestrator 초기화 완료 (대상 SKU: 반도체 칩, 마스크, 종합 품목)")

    def run_daily_pipeline(self, day: int, current_date: datetime, stress_event: dict) -> dict:
        """
        매일 각 SKU별 SCM 파이프라인을 순회 및 조율 실행합니다.
        """
        date_str = current_date.strftime("%Y-%m-%d")
        timestamp_str = f"{date_str} 12:00:00"
        daily_results = {}

        for sku in self.skus:
            # 1. 입고 처리
            today_arrival = self.arrival_queues[sku].pop(day, 0.0)
            if today_arrival > 0:
                self.current_stocks[sku] += today_arrival
                logger.info(f"📦 [{sku} 입고] {day}일차 입고 스케줄에 따라 {today_arrival:.0f}개 하역 (현재 재고: {self.current_stocks[sku]:.0f}개)")

            # 2. 데이터 수집 및 전처리
            raw_data = self.data_agents[sku].collect(
                day=day,
                current_date=current_date,
                stress_event=stress_event,
                current_stock=self.current_stocks[sku],
                product_name=sku
            )

            # 3. 수요 발생 및 재고 차감 (품절 처리)
            actual_demand = raw_data.daily_demand
            self.cumulative_demand[sku] += actual_demand
            
            if self.current_stocks[sku] >= actual_demand:
                fulfilled = actual_demand
                self.current_stocks[sku] -= actual_demand
                stockout_units = 0.0
            else:
                fulfilled = self.current_stocks[sku]
                stockout_units = actual_demand - self.current_stocks[sku]
                self.current_stocks[sku] = 0.0
                logger.error(f"🚨 [CRITICAL STOCKOUT] {sku} 재고 고갈! 미충족 수요: -{stockout_units:.0f}개")
            
            self.cumulative_fulfilled[sku] += fulfilled
            self.stock_history[sku].append(self.current_stocks[sku])

            # 4. [고도화 A6] 수요 예측 엔진 고도화 - 지수 가중 이동평균(EWMA) 예측 적용
            history_demand = raw_data.history_demand
            if history_demand:
                span = 7.0
                alpha = 2.0 / (span + 1.0)
                ewma = history_demand[0]
                for d in history_demand[1:]:
                    ewma = alpha * d + (1 - alpha) * ewma
                predicted_demand = ewma
            else:
                predicted_demand = actual_demand * 0.95

            # MAPE 연산 및 로깅
            actual_val = max(actual_demand, 1.0)
            mape = abs(actual_val - predicted_demand) / actual_val
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO forecast_accuracy_logs (date, product_name, predicted_demand, actual_demand, mape)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (date_str, sku, round(predicted_demand, 1), round(actual_demand, 1), round(mape, 4))
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to write forecast accuracy log for {sku}: {e}")

            # 5. 확률론적 ROP/안전재고 분석
            signal = self.analysis_agent.analyze(raw_data)
            
            # 6. 가드레일 및 발주 실행
            result = self.action_agent.execute(signal)
            daily_results[sku] = result

            # 7. 발주 승인 시 리드타임 후 입고 스케줄 예약
            if result.get("action") == "ORDER_EXECUTED":
                approved_qty = result.get("approved_qty", 0.0)
                if approved_qty > 0:
                    predicted_lead_time = int(round(raw_data.lead_time_days))
                    arrival_day = day + predicted_lead_time
                    self.arrival_queues[sku][arrival_day] = self.arrival_queues[sku].get(arrival_day, 0.0) + approved_qty
                    logger.info(f"🛒 [발주 완료] {sku} {approved_qty:.0f}개 발주 ➔ {arrival_day}일차 입고 예정")

            # 8. [고도화 A4, A5] SCM 핵심 SLA KPI 연산 및 DB 기록
            # Fill Rate % = 누적 충족수량 / 누적 수요수량 * 100
            if self.cumulative_demand[sku] > 0:
                fill_rate = (self.cumulative_fulfilled[sku] / self.cumulative_demand[sku]) * 100.0
            else:
                fill_rate = 100.0

            # Inventory Turnover Ratio = 연간 환산 수요 / 평균 재고량
            avg_stock = np.mean(self.stock_history[sku]) if self.stock_history[sku] else 0.0
            if avg_stock > 0:
                annualized_demand = (self.cumulative_demand[sku] / day) * 365.0
                turnover = annualized_demand / avg_stock
            else:
                turnover = 0.0

            # DB daily_demand_stats 테이블에 KPI 업데이트 (혹은 누적 저장)
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                # 지점 KR-11 기준으로 KPI 데이터 축적 (메인 관제 지점)
                cursor.execute(
                    """
                    INSERT INTO daily_demand_stats (region_code, product_name, date, daily_outbound_total, moving_avg_30d)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(region_code, product_name, date) DO UPDATE SET
                        daily_outbound_total = excluded.daily_outbound_total
                    """,
                    ("KR-11", sku, date_str, actual_demand, fill_rate) # moving_avg_30d 대신 fill_rate 임시 기록용 (또는 별도 구조)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to save SLA KPIs for {sku}: {e}")

            logger.info(f"📊 [{sku} KPI Summary] Fill Rate: {fill_rate:.1f}% | Turnover Ratio: {turnover:.2f} (Avg Stock: {avg_stock:.1f})")

        return daily_results
