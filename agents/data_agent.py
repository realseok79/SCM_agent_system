"""
agents/data_agent.py
--------------------
Data Agent: 가상 SCM DB와 Mock API 서버를 주기적으로 스캔하여
결측치/노이즈를 보정하고, Analysis Agent가 소비할 표준 DataDTO로 변환합니다.

[처리 파이프라인]
1. 가상 DB(JSON)에서 해당 일자 데이터 로드 (Sales가 아닌 Demand 추출)
2. Mock API 서버에서 외부 신호(날씨, 거시경제, 리드타임) 수집 (가상 시간 동기화)
3. 결측치 보정 (전일 이동평균으로 대체)
4. 노이즈 보정 (3σ 기준치로 이상치 클리핑)
5. 스트레스 이벤트 가중치 적용 (통계 오염 격리)
"""

import json
import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

class GlobalIssueTracker:
    def __init__(self):
        # GDELT DOC 2.0 API 엔드포인트 (API Key 불필요)
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def fetch_supply_chain_risk_tone(self, target_country="Taiwan", issue_keyword="strike OR delay OR block OR supply chain"):
        query = f'"{target_country}" AND ({issue_keyword})'
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": 50,
            "format": "json",
            "timespan": "3d"
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200 and len(response.text) > 0:
                data = response.json()
                if "articles" not in data or not data["articles"]:
                    return {"risk_level": "Low", "average_tone": 0.0, "article_count": 0, "top_headline": ""}

                df = pd.DataFrame(data["articles"])
                average_tone = df['tone'].mean()
                article_count = len(df)
                
                risk_level = "High" if average_tone < -3.0 else ("Medium" if average_tone < -1.0 else "Low")
                return {
                    "risk_level": risk_level,
                    "average_tone": round(average_tone, 2),
                    "article_count": article_count,
                    "top_headline": df.iloc[0]['title']
                }
            return {"risk_level": "Low", "average_tone": 0.0, "article_count": 0, "top_headline": ""}
        except Exception as e:
            return {"risk_level": "Low", "average_tone": 0.0, "article_count": 0, "top_headline": ""}


from dto.schemas import DataDTO
from utils.logger import get_logger

load_dotenv()
logger = get_logger("DataAgent")

MOCK_API_HOST = os.getenv("MOCK_API_HOST", "http://localhost:8080")
DATA_PATH = os.getenv("SCM_DATA_PATH", "outputs/scm_dummy_data.json")


class DataAgent:
    """
    SCM 데이터 수집 및 전처리 에이전트 (수학적 통계 오염 방지 적용)
    """

    def __init__(self):
        self._db: list[dict] = self._load_db()
        # 통계적 기준선 및 Analysis Agent 전달용 시계열 Buffer 초기화
        self._demand_history: list[float] = []
        self._lt_history: list[float] = []
        self._gdelt_tracker = GlobalIssueTracker()
        logger.info(f"DataAgent 초기화 완료 | DB 레코드: {len(self._db)}일치 | GDELT API 연동 준비")

    def _load_db(self) -> list[dict]:
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"SCM 더미 데이터 없음: {DATA_PATH}")
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def _fetch_external_signals(self, day: int) -> dict:
        """Mock API 서버에서 가상 시점(day)에 동기화된 외부 신호 수집"""
        defaults = {
            "weather_index": 1.0,
            "macro_trend": 1.0,
            "lead_time_days": 7.0,
            "stress_event": False
        }

        try:
            # 쿼리 파라미터로 타임 시뮬레이터의 현재 일차(day) 전달
            res = requests.get(f"{MOCK_API_HOST}/api/external-signals?day={day}", timeout=3)
            signals = res.json()

            lt_res = requests.get(f"{MOCK_API_HOST}/api/lead-time?day={day}", timeout=3)
            lt_data = lt_res.json()

            return {
                "weather_index": signals.get("weather_index", 1.0),
                "macro_trend": signals.get("macro_trend", 1.0),
                "lead_time_days": lt_data.get("lead_time_days", 7.0),
                "stress_event": signals.get("stress_event", False)
            }
        except Exception as e:
            logger.error(f"외부 신호 수집 오류: {e} → 기본값 보간 처리")
            return defaults

    def _fix_missing(self, value: float | None, field: str) -> float:
        if value is None or np.isnan(value):
            if len(self._demand_history) >= 1:
                fallback = float(np.mean(self._demand_history[-7:]))
                return fallback
            return 100.0
        return float(value)

    def _clip_outlier(self, value: float, field: str) -> float:
        """
        포아송 수요 분포의 근사적 3σ 클리핑
        """
        if len(self._demand_history) < 10:
            return value

        recent = self._demand_history[-30:]
        mean = np.mean(recent)
        std = np.std(recent)

        lower = max(0.0, mean - 3 * std) # 수요는 음수가 될 수 없음
        upper = mean + 3 * std

        if value < lower or value > upper:
            clipped = float(np.clip(value, lower, upper))
            logger.debug(f"노이즈 클리핑 [{field}]: {value:.1f} → {clipped:.1f}")
            return clipped
        return value

    def collect(self, day: int, current_date, stress_event, current_stock: float) -> DataDTO:
        """
        데이터 수집 및 정제 파이프라인 메인 (Analysis Agent로 표준 DTO 전달)
        """
        stress_event = stress_event or {"is_stress": False}
        idx = (day - 1) % len(self._db)
        raw = self._db[idx]

        # 1. 원시 데이터 추출 (Sales가 아닌 Demand 추출로 검열 방지)
        raw_demand = raw.get("daily_demand", raw.get("daily_sales")) 

        # 2. 결측치 및 통계적 노이즈 보정
        clean_demand = self._clip_outlier(self._fix_missing(raw_demand, "daily_demand"), "daily_demand")

        # 3. 외부 신호 수집
        signals = self._fetch_external_signals(day)
        base_lead_time = signals["lead_time_days"]

        # 4. 최종 확정된 전처리 데이터를 히스토리에 누적 (과거 창 생성)
        # 스트레스 이벤트 배율이 적용되기 전의 순수 정제 데이터(Baseline)만 히스토리에 쌓음
        self._demand_history.append(float(clean_demand))
        self._lt_history.append(float(base_lead_time))


        # 5. 스트레스 테스트 시나리오 가중치 연산
        final_demand = clean_demand
        final_lead_time = base_lead_time
        
        if stress_event.get("is_stress"):
            final_demand *= stress_event.get("demand_multiplier", 1.0)
            final_lead_time *= stress_event.get("lead_time_multiplier", 1.0)
            logger.warning(f"⚠️ [{day}일차] 스트레스 주입 완료: 수요 {final_demand:.0f} / 조달 {final_lead_time:.1f}일")

        # 6. GDELT 공급망 리스크 스캔 (스트레스 이벤트와 연동 또는 기본 국가 검색)
        gdelt_data = self._gdelt_tracker.fetch_supply_chain_risk_tone()

        # 7. 표준 DataDTO 객체를 생성하여 AnalysisAgent로 전달
        return DataDTO(
            timestamp=datetime.now().isoformat(),
            day=day,
            daily_demand=float(final_demand),
            current_stock=float(current_stock),  # 시뮬레이터에서 계산된 실시간 동적 재고 반영
            lead_time_days=float(final_lead_time),
            weather_index=float(signals["weather_index"]),
            macro_trend=float(signals["macro_trend"]),
            history_demand=list(self._demand_history),
            history_lead_time=list(self._lt_history),
            gdelt_risk_level=gdelt_data["risk_level"],
            gdelt_average_tone=gdelt_data["average_tone"],
            gdelt_article_count=gdelt_data["article_count"],
            gdelt_top_headline=gdelt_data.get("top_headline", "")
        )
