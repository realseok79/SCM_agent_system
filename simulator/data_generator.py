"""
simulator/data_generator.py
---------------------------
1년치 가상 SCM 역사적 더미 데이터를 생성하는 스크립트.
물류 조달 기간(Lead Time) 지연 시뮬레이션 및 품절 손실(Stockout Loss) 분리 적재 알고리즘 적용.

[생성 데이터 항목]
- daily_demand   : 가중치가 적용된 실제 발생 총 수요 (Analysis Agent 학습용 핵심)
- daily_sales    : 실제 유효 판매량 (재고 제약 반영)
- stockout_units : 품절로 인해 놓친 미충족 수요량
- stock_level    : 당일 마감 재고
- incoming_stock : 당일 실제 입고 완료된 물량
"""

import numpy as np
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가 (직접 실행 시 모듈 참조 에러 방지)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

load_dotenv()
logger = get_logger("DataGenerator")

SEED = 42
rng = np.random.default_rng(SEED)


class SCMDataGenerator:
    """
    가상 SCM 데이터 제너레이터 (리드타임 딜레이 큐 및 SCM KPI 단가 탑재)
    """

    def __init__(
        self,
        start_date: str = "2024-01-01",
        days: int = 365,
        initial_stock: int = 1500,
        base_demand_lambda: float = 100.0,
        holding_cost_per_unit: float = 2.0,     # 개당 하루 재고 유지 비용
        stockout_cost_per_unit: float = 15.0    # 개당 품절 기회비용 패널티
    ):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.days = days
        self.initial_stock = initial_stock
        self.base_demand_lambda = base_demand_lambda
        
        # 비용 변수 세팅 (계획서 상의 총비용 TC 최적화 기반 마련)
        self.holding_cost_per_unit = holding_cost_per_unit
        self.stockout_cost_per_unit = stockout_cost_per_unit

        # 조달 기간(Lead Time) 처리를 위한 동적 입고 스케줄 큐
        # { 입고될_day_index: incoming_quantity }
        self.incoming_schedule = {}

        logger.info("=" * 55)
        logger.info("SCM 고도화 더미 데이터 생성기 가동")
        logger.info(f"  기본 일 수요 분포 : Poisson(λ={base_demand_lambda})")
        logger.info(f"  재고 유지/품절 단가: Holding=${holding_cost_per_unit} | Stockout=${stockout_cost_per_unit}")
        logger.info("=" * 55)

    def _seasonal_weight(self, day_index: int) -> float:
        """sin 함수 주기성을 활용한 계절성 트렌드 산출"""
        seasonal = 0.2 * np.sin(2 * np.pi * day_index / 365 - np.pi / 2)
        return round(1.0 + seasonal, 3)

    def _weekend_weight(self, date: datetime) -> float:
        return 1.4 if date.weekday() >= 5 else 1.0

    def _growth_weight(self, day_index: int) -> float:
        annual_growth = 0.10
        daily_growth = annual_growth / 365
        return round(1.0 + daily_growth * day_index, 4)

    def _process_procurement(self, current_day: int, current_stock: float):
        """
        [수정] 리드타임 딜레이 가상 스케줄링 로직
        재고가 안전재고 이하면 고정 발주(EOQ)를 수행하되, 리드타임 뒤에 입고되도록 스케줄링 큐에 등록합니다.
        """
        safety_stock = self.base_demand_lambda * 7
        eoq = int(self.base_demand_lambda * 14)

        # 이미 발주 넣어서 오고 있는 물량(On-Order)이 없는지 검증하는 방어 코드 추가 가능
        if current_stock <= safety_stock:
            # 계획서 상의 정규분포 기반 리드타임 산출 (최소 3일 보장)
            lead_time = max(3, int(rng.normal(loc=7.0, scale=1.5)))
            arrival_day = current_day + lead_time
            
            # 입고 스케줄 큐에 누적 누적 적재
            self.incoming_schedule[arrival_day] = self.incoming_schedule.get(arrival_day, 0) + eoq
            logger.debug(f"  [발주 가동] Day {current_day} → {eoq}개 신규 발주 (리드타임: {lead_time}일, Day {arrival_day} 입고 예정)")

    def generate(self) -> pd.DataFrame:
        """365일치 SCM 시나리오 데이터 파이프라인 가동"""
        logger.info(f"정밀 {self.days}일치 시뮬레이션 역사 데이터 적재 시작...")

        records = []
        stock_level = float(self.initial_stock)

        for i in range(self.days):
            current_date = self.start_date + timedelta(days=i)

            # 1. 당일 아침 입고 처리 (스케줄러 큐 확인)
            incoming_today = self.incoming_schedule.pop(i, 0)
            stock_level += incoming_today

            # 2. 시장 수요(Effective Demand) 생성
            s_weight = self._seasonal_weight(i)
            w_weight = self._weekend_weight(current_date)
            g_weight = self._growth_weight(i)
            
            effective_lambda = self.base_demand_lambda * s_weight * w_weight * g_weight
            daily_demand = int(rng.poisson(lam=effective_lambda))

            # 3. [핵심] 재고 제약 기반 실제 판매량(Sales) 및 품절량(Stockout) 분리 연산
            if stock_level >= daily_demand:
                daily_sales = daily_demand
                stockout_units = 0
                stock_level -= daily_demand
            else:
                daily_sales = int(stock_level)
                stockout_units = daily_demand - daily_sales
                stock_level = 0.0  # 전량 품절
                logger.warning(f"🚨 [품절 경보] Day {i} ({current_date.date()}) | 수요: {daily_demand}개, 판매: {daily_sales}개 (미충족: {stockout_units}개)")

            # 4. 물류 발주 심사 및 딜레이 스케줄링 가동
            self._process_procurement(i, stock_level)

            # 5. 당일 마감 기준 재고 비용 연산
            holding_cost = stock_level * self.holding_cost_per_unit
            stockout_penalty = stockout_units * self.stockout_cost_per_unit
            total_daily_cost = holding_cost + stockout_penalty

            records.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_index": i,
                "day_of_week": current_date.weekday(),
                "is_weekend": current_date.weekday() >= 5,
                "month": current_date.month,
                "seasonal_weight": s_weight,
                "weekend_weight": w_weight,
                "growth_weight": g_weight,
                "daily_demand": daily_demand,       # 분석 에이전트가 학습해야 할 진짜 찐 수요 데이터
                "daily_sales": daily_sales,         # 회계/매출 지표
                "stockout_units": stockout_units,   # 품절 패널티 추적용
                "incoming_stock": incoming_today,   # 아침에 입고된 수량
                "stock_level": round(stock_level, 0),
                "holding_cost": holding_cost,
                "stockout_penalty": stockout_penalty,
                "total_cost": total_daily_cost
            })

        df = pd.DataFrame(records)
        logger.info(f"데이터 정밀 적재 완료: {len(df)}행")
        self._print_stats(df)
        return df

    def _print_stats(self, df: pd.DataFrame):
        logger.info("=" * 55)
        logger.info("🏆 리팩토링 데이터 통계 요약")
        logger.info(f"  총 누적 수요량  : {df['daily_demand'].sum():,} 개")
        logger.info(f"  총 실제 판매량  : {df['daily_sales'].sum():,} 개")
        logger.info(f"  총 품절 발생 일수: {(df['stockout_units'] > 0).sum()} 일")
        logger.info(f"  총 미충족 수량  : {df['stockout_units'].sum():,} 개 (품절률: {(df['stockout_units'].sum()/df['daily_demand'].sum())*100:.2f}%)")
        logger.info(f"  운영 총비용(TC) : ${df['total_cost'].sum():,.2f}")
        logger.info("=" * 55)

    def save_csv(self, df: pd.DataFrame, path: str = "outputs/scm_dummy_data.csv"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV 아카이브 완료: {path}")

    def save_json(self, df: pd.DataFrame, path: str = "outputs/scm_dummy_data.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        records = df.to_dict(orient="records")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    generator = SCMDataGenerator(
        start_date="2024-01-01",
        days=365,
        initial_stock=1500,
        base_demand_lambda=100.0
    )

    df = generator.generate()
    generator.save_csv(df)
    generator.save_json(df)

    print("\n[리팩토링 샘플 데이터 (첫 5행)]")
    print(df[["date", "daily_demand", "daily_sales", "stockout_units", "incoming_stock", "stock_level"]].head().to_string(index=False))
