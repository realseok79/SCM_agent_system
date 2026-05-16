"""
simulator/data_generator.py
---------------------------
Data Agent가 수집하고 정제할 가상 SCM 레거시 원시 환경 DB(JSON)를 생성합니다.
수요 절단 편향을 차단하기 위해 daily_demand를 기본 축으로 생성하며,
TimeSimulator의 스트레스 스케줄과 싱크를 맞춘 위기 데이터를 물리적으로 주입합니다.
Data Agent의 전처리 로직(결측치, 이상치 보정)을 테스트하기 위해 의도적인 노이즈를 포함합니다.
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import get_logger

load_dotenv()
logger = get_logger("DataGenerator")

SEED = 42
rng = np.random.default_rng(SEED)


class SCMDataGenerator:
    """
    가상 SCM 환경 데이터 제너레이터 (에이전트 파이프라인 독립 테스트용 환경 생성기)
    """

    def __init__(
        self,
        start_date: str = "2026-01-01",
        days: int = 100,  # 계획서 명세: 100일 압축 시뮬레이션
        base_demand_lambda: float = 120.0,
        holding_cost_per_unit: float = 2.0,
        stockout_cost_per_unit: float = 15.0
    ):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.days = days
        self.base_demand_lambda = base_demand_lambda
        self.holding_cost_per_unit = holding_cost_per_unit
        self.stockout_cost_per_unit = stockout_cost_per_unit

        # ── [동기화] time_engine.py의 스트레스 스케줄 명세와 완벽 일치 ──
        self.stress_schedule = [
            {"start": 30, "end": 35, "demand_mult": 5.0, "lt_mult": 1.0},
            {"start": 60, "end": 81, "demand_mult": 1.0, "lt_mult": 3.0},
            {"start": 85, "end": 90, "demand_mult": 3.0, "lt_mult": 2.5}
        ]

    def _get_active_multipliers(self, day_index: int) -> tuple[float, float]:
        """특정 일차에 할당된 시뮬레이터 위기 가중치 반환"""
        day = day_index + 1  # 1부터 시작하는 시뮬레이터 day 기점 동기화
        for event in self.stress_schedule:
            if event["start"] <= day <= event["end"]:
                return event["demand_mult"], event["lt_mult"]
        return 1.0, 1.0

    def _seasonal_weight(self, day_index: int) -> float:
        # 시뮬레이션 기간(100일) 내 선형 변동 주기를 부여하기 위해 분모 조정
        seasonal = 0.15 * np.sin(2 * np.pi * day_index / 50 - np.pi / 2)
        return round(1.0 + seasonal, 3)

    def _weekend_weight(self, date: datetime) -> float:
        return 1.3 if date.weekday() >= 5 else 1.0

    def generate(self) -> pd.DataFrame:
        records = []
        logger.info(f"SCM 원시 레거시 데이터 생성 개시 (총 기간: {self.days}일)")

        for i in range(self.days):
            current_date = self.start_date + timedelta(days=i)
            day_num = i + 1

            # 1. 기본 결정론적 가중치 연산
            s_weight = self._seasonal_weight(i)
            w_weight = self._weekend_weight(current_date)
            
            # 2. 타임 엔진 동기화 스트레스 가중치 연산
            stress_demand_mult, stress_lt_mult = self._get_active_multipliers(i)
            
            # 3. 최종 확률론적 수요 강도(λ) 및 리드타임 기댓값 계산
            effective_lambda = self.base_demand_lambda * s_weight * w_weight * stress_demand_mult
            daily_demand = int(rng.poisson(lam=effective_lambda))
            
            # 기본 리드타임 7일에 스트레스 가중치 적용
            base_lead_time = 7.0 * stress_lt_mult
            lead_time_days = round(max(2.0, rng.normal(loc=base_lead_time, scale=1.0)), 1)

            # 4. [핵심] Data Agent의 강건성(Robustness) 검증을 위한 인위적 결측치/이상치 주입
            # 3% 확률로 시스템 입력 누락 에러(NaN) 발생 처리
            if rng.random() < 0.03:
                daily_demand = None
            # 2% 확률로 비정상 센서 오작동성 거대 이상치(Outlier) 발생 처리
            elif rng.random() < 0.02:
                daily_demand = int(daily_demand * 4.5)

            records.append({
                "day": day_num,
                "date": current_date.strftime("%Y-%m-%d"),
                "daily_demand": daily_demand,  # 전처리 전 원시 수요 데이터 (결측치 포함)
                "lead_time_days": lead_time_days,
                "weather_index": round(rng.uniform(0.5, 1.8) if s_weight > 1.0 else rng.uniform(0.3, 1.2), 3),
                "macro_trend": round(1.0 + (i * 0.002) + rng.normal(0, 0.05), 3),
                "holding_cost_per_unit": self.holding_cost_per_unit,
                "stockout_cost_per_unit": self.stockout_cost_per_unit
            })

        df = pd.DataFrame(records)
        return df

    def save_json(self, df: pd.DataFrame, path: str = "outputs/scm_dummy_data.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # DataFrame을 JSON 직렬화가 가능한 형태로 변환 (NaN은 None으로 변환됨)
        records = df.replace({np.nan: None}).to_dict(orient="records")
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 가상 SCM 데이터 파티션 저장 완료 ➔ {path}")


if __name__ == "__main__":
    generator = SCMDataGenerator(start_date="2026-01-01", days=100)
    df = generator.generate()
    generator.save_json(df)