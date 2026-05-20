"""
agents/data_agent.py
--------------------
Data Agent: 가상 SCM DB와 Mock API 서버를 주기적으로 스캔하여
결측치/노이즈를 보정하고, Analysis Agent가 소비할 표준 DataDTO로 변환합니다.
추가로 GDELT 기상 리스크 분석 지표 및 구글 트렌드 연동 기능을 내재화하였습니다.
"""

import json
import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from pytrends.request import TrendReq

from dto.schemas import DataDTO, DemandDTO, RiskCategory, AlertLevel, OperationMode
from pydantic import BaseModel, Field
from utils.logger import get_logger

class UnstructuredParseOutput(BaseModel):
    item_name: str = Field(description="추출된 품목명 또는 제품명 (예: 반도체 칩, 마스크, 의류 등)")
    quantity: float = Field(description="추출된 발주 수량")
    category: str = Field(description="리스크 카테고리. 다음 중 하나여야 함: LOGISTICS_AND_TRADE, WEATHER_AND_CLIMATE, TECH_AND_SEMICONDUCTOR, FINANCES_AND_MACRO, UNCLASSIFIED")

from agents.config import PATHS, NETWORK
from agents.data_config import build_weight_map, get_demand_impact_score

logger = get_logger("DataAgent")
MOCK_API_HOST = NETWORK["MOCK_API_HOST"]
DATA_PATH = PATHS["SCM_DATA"]


class GlobalIssueTracker:
    def __init__(self):
        # GDELT DOC 2.0 API 엔드포인트 (API Key 불필요)
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def fetch_supply_chain_risk_tone(self, target_country="Taiwan", issue_keyword="strike OR delay OR block OR supply chain OR protest OR union OR trucker OR shutdown"):
        query = f'"{target_country}" AND ({issue_keyword})'
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": 50,
            "format": "json",
            "timespan": "3d"
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=1.5)
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


class DataAgent:
    """
    SCM 데이터 수집 및 전처리 에이전트 (수학적 통계 오염 방지 적용)
    """

    def __init__(self):
        self._db: list[dict] = self._load_db()
        # 통계적 기준선 및 Analysis Agent 전달용 시계열 Buffer 초기화
        self._demand_history: list[float] = []
        self._lt_history: list[float] = []
        self.last_processed_day: int = -1  # [추가] 중복 누적 방지용 일자 추적 필드
        self._gdelt_tracker = GlobalIssueTracker()
        
        # Pytrends 설정 및 키워드 가중치 로드
        try:
            self._pytrends = TrendReq(hl='ko', tz=540)
        except Exception as e:
            logger.warning(f"Pytrends 초기화 실패 (폴백 시뮬레이션 준비): {e}")
            self._pytrends = None
        self._weight_map = build_weight_map()

        logger.info(f"DataAgent 초기화 완료 | DB 레코드: {len(self._db)}일치 | GDELT 및 Google Trends 연동 준비")

    def _load_db(self) -> list[dict]:
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"SCM 더미 데이터 없음: {DATA_PATH}")
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def _fetch_trend_signal(self) -> dict:
        """
        data_config.py의 키워드 매트릭스를 기반으로
        Google Trends에서 급상승 키워드를 수집하고
        get_demand_impact_score()로 가중 충격 지수를 반환합니다.
        API 429 에러 등 실패 시 시뮬레이션 폴백 제공.
        """
        sample_keywords = ["물류 파업", "마스크", "금리 인상", "반도체 공급 부족", "유가 폭등"]
        try:
            if self._pytrends is None:
                raise ValueError("pytrends is not initialized")
            self._pytrends.build_payload(sample_keywords, timeframe='today 1-m', geo='KR')
            df = self._pytrends.interest_over_time()
            if df.empty:
                return {"composite_score": 0.0, "matched_count": 0}
            
            trending = [kw for kw in sample_keywords if df[kw].tail(7).mean() > 50]
            return get_demand_impact_score(trending, self._weight_map)
        except Exception as e:
            logger.debug(f"Google Trends 수집 폴백 작동: {e}")
            return {"composite_score": 0.0, "matched_count": 0}

    def _fetch_external_signals(self, day: int) -> dict:
        """Mock API 서버에서 가상 시점(day)에 동기화된 외부 신호 수집"""
        defaults = {
            "weather_index": 1.0,
            "macro_trend": 1.0,
            "lead_time_days": 7.0,
            "stress_event": False
        }

        try:
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

    def _fix_missing(self, value: Optional[float], field: str) -> float:
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

        lower = max(0.0, mean - 3 * std)
        upper = mean + 3 * std

        if value < lower or value > upper:
            clipped = float(np.clip(value, lower, upper))
            logger.debug(f"노이즈 클리핑 [{field}]: {value:.1f} → {clipped:.1f}")
            return clipped
        return value

    def collect(self, day: int, current_date, stress_event, current_stock: float) -> DataDTO:
        """
        데이터 수집 및 전처리 파이프라인 메인 (Analysis Agent로 표준 DTO 전달)
        """
        stress_event = stress_event or {"is_stress": False}
        idx = (day - 1) % len(self._db)
        raw = self._db[idx]

        # 1. 원시 데이터 추출 (Demand 추출로 검열 방지)
        raw_demand = raw.get("daily_demand", raw.get("daily_sales")) 

        # 2. 결측치 및 통계적 노이즈 보정
        clean_demand = self._clip_outlier(self._fix_missing(raw_demand, "daily_demand"), "daily_demand")

        # 3. 외부 신호 수집
        signals = self._fetch_external_signals(day)
        base_lead_time = signals["lead_time_days"]

        # 4. 최종 확정된 전처리 데이터를 히스토리에 누적 (과거 창 생성 - 중복 방지 가드레일 적용)
        if day > getattr(self, "last_processed_day", -1):
            self._demand_history.append(float(clean_demand))
            self._lt_history.append(float(base_lead_time))
            self.last_processed_day = day

        # 5. 스트레스 테스트 시나리오 가중치 연산
        final_demand = clean_demand
        final_lead_time = base_lead_time
        
        if stress_event.get("is_stress"):
            final_demand *= stress_event.get("demand_multiplier", 1.0)
            final_lead_time *= stress_event.get("lead_time_multiplier", 1.0)
            logger.warning(f"⚠️ [{day}일차] 스트레스 주입 완료: 수요 {final_demand:.0f} / 조달 {final_lead_time:.1f}일")

        # 6. GDELT 공급망 리스크 스캔
        gdelt_data = self._gdelt_tracker.fetch_supply_chain_risk_tone()

        # 7. Google Trends 수요 리스크 스캔
        trend_signal = self._fetch_trend_signal()

        # [신규] 표준 DemandDTO 전처리 포맷팅 동작 확인 및 검증
        try:
            demand_dto = self.preprocess_to_demand_dto(
                day=day,
                current_stock=current_stock,
                clean_demand=final_demand,
                final_lead_time=final_lead_time,
                trend_composite_score=trend_signal["composite_score"],
                raw_record=raw
            )
            logger.info(f"✨ [Preprocess] 표준 DemandDTO 변환 성공 (Item: {demand_dto.item_name}) | "
                        f"실효수요: {demand_dto.effective_demand:.1f} | ROP: {demand_dto.reorder_point:.1f} | EOQ: {demand_dto.eoq:.1f}")
        except Exception as e:
            logger.error(f"❌ 표준 DemandDTO 전처리 변환 실패: {e}")

        # 8. 비용 파라미터 동적 파싱 (TC 목적함수용, SKU별 상이)
        holding_cost_per_unit = float(raw.get("holding_cost_per_unit", 0.5))
        stockout_cost_per_unit = float(raw.get("stockout_cost_per_unit", 10.0))
        order_fixed_cost = float(raw.get("order_fixed_cost", 200.0))

        # 9. 표준 DataDTO 객체를 생성하여 AnalysisAgent로 전달 (하위 호환성 유지)
        return DataDTO(
            timestamp=datetime.now().isoformat(),
            day=day,
            daily_demand=float(final_demand),
            current_stock=float(current_stock),
            lead_time_days=float(final_lead_time),
            weather_index=float(signals["weather_index"]),
            macro_trend=float(signals["macro_trend"]),
            history_demand=list(self._demand_history),
            history_lead_time=list(self._lt_history),
            gdelt_risk_level=gdelt_data["risk_level"],
            gdelt_average_tone=gdelt_data["average_tone"],
            gdelt_article_count=gdelt_data["article_count"],
            gdelt_top_headline=gdelt_data.get("top_headline", ""),
            trend_composite_score=trend_signal["composite_score"],
            trend_matched_count=trend_signal["matched_count"],
            unit_holding_cost=holding_cost_per_unit,
            stockout_penalty=stockout_cost_per_unit,
            order_fixed_cost=order_fixed_cost
        )

    def preprocess_to_demand_dto(
        self,
        day: int,
        current_stock: float,
        clean_demand: float,
        final_lead_time: float,
        trend_composite_score: float,
        raw_record: dict
    ) -> DemandDTO:
        """
        [전처리 파트] 가져온 날것의 데이터를 표준 DemandDTO로 포맷팅합니다.
        보완책 1, 2, 3이 내재된 확률론적 재고/수요 최적화 파라미터가 자동으로 계산되는 마스터 DTO입니다.
        """
        # 1. 수요 평균 및 표준편차 산출 (안정적인 통계 산출을 위해 최소 2일 이상의 데이터가 있을 때 계산)
        avg_demand = float(np.mean(self._demand_history)) if self._demand_history else clean_demand
        std_demand = float(np.std(self._demand_history)) if len(self._demand_history) > 1 else (clean_demand * 0.25)
        
        # 2. 리드타임 표준편차 산출
        std_lt = float(np.std(self._lt_history)) if len(self._lt_history) > 1 else 1.5
        
        # 3. 비용 정보 파싱
        holding_cost_per_unit = float(raw_record.get("holding_cost_per_unit", 2.0))
        stockout_cost = float(raw_record.get("stockout_cost_per_unit", 15.0))
        holding_cost_rate = 0.2
        # holding_cost = unit_cost * holding_cost_rate => unit_cost = holding_cost / holding_cost_rate
        unit_cost = holding_cost_per_unit / holding_cost_rate if holding_cost_rate > 0 else 10.0

        # 4. 리스크 카테고리 동적 매핑
        risk_cat = RiskCategory.UNCLASSIFIED
        if abs(raw_record.get("weather_index", 1.0) - 1.0) > 0.5:
            risk_cat = RiskCategory.WEATHER_AND_CLIMATE
        elif abs(raw_record.get("macro_trend", 1.0) - 1.0) > 0.5:
            risk_cat = RiskCategory.MACRO_ECONOMY
        else:
            risk_cat = RiskCategory.LOGISTICS_AND_TRADE

        # 5. 표준 DemandDTO 생성 (원시 레코드에서 SKU 정보를 동적으로 추출하되 안전하게 폴백 설정)
        return DemandDTO(
            item_id=str(raw_record.get("item_id", "ITEM-SCM-001")),
            item_name=str(raw_record.get("item_name", "가상 SCM 반도체 부품")),
            current_stock=float(current_stock),
            daily_demand_avg=round(avg_demand, 2),
            daily_demand_std=round(std_demand, 2),
            lead_time_days=round(final_lead_time, 2),
            lead_time_std=round(std_lt, 2),
            unit_cost=round(unit_cost, 2),
            holding_cost_rate=holding_cost_rate,
            stockout_cost=stockout_cost,
            risk_category=risk_cat,
            service_level=0.95,
            demand_impact=float(trend_composite_score),
            mode=OperationMode.SIMULATION,
            timestamp=datetime.now().isoformat(),
            source_file=DATA_PATH
        )

    def collect_demand_dto(self, day: int, current_date, stress_event, current_stock: float) -> DemandDTO:
        """
        날것의 수집 및 보정 데이터를 바탕으로 전처리하여 표준 DemandDTO를 직접 반환하는 엔트리포인트
        """
        stress_event = stress_event or {"is_stress": False}
        idx = (day - 1) % len(self._db)
        raw = self._db[idx]

        # 1. 원시 데이터 추출
        raw_demand = raw.get("daily_demand", raw.get("daily_sales")) 

        # 2. 결측치 및 통계적 노이즈 보정
        clean_demand = self._clip_outlier(self._fix_missing(raw_demand, "daily_demand"), "daily_demand")

        # 3. 외부 신호 수집
        signals = self._fetch_external_signals(day)
        base_lead_time = signals["lead_time_days"]

        # 4. 최종 확정된 전처리 데이터를 히스토리에 누적 (과거 창 생성 - 중복 방지 가드레일 적용)
        if day > getattr(self, "last_processed_day", -1):
            self._demand_history.append(float(clean_demand))
            self._lt_history.append(float(base_lead_time))
            self.last_processed_day = day

        # 5. 스트레스 테스트 시나리오 가중치 연산
        final_demand = clean_demand
        final_lead_time = base_lead_time
        
        if stress_event.get("is_stress"):
            final_demand *= stress_event.get("demand_multiplier", 1.0)
            final_lead_time *= stress_event.get("lead_time_multiplier", 1.0)
            logger.warning(f"⚠️ [{day}일차] 스트레스 주입 완료: 수요 {final_demand:.0f} / 조달 {final_lead_time:.1f}일")

        # 6. Google Trends 수요 리스크 스캔
        trend_signal = self._fetch_trend_signal()
        trend_composite_score = trend_signal["composite_score"]

        # 7. DemandDTO로 포맷팅 및 반환
        return self.preprocess_to_demand_dto(
            day=day,
            current_stock=current_stock,
            clean_demand=final_demand,
            final_lead_time=final_lead_time,
            trend_composite_score=trend_composite_score,
            raw_record=raw
        )

    def parse_unstructured_input(self, text: str = None, file_df = None) -> dict:
        """
        [Phase 2 요구사항] 비정형 텍스트나 사용자 엑셀 파일을 전달받아
        정형화된 품목명, 수량, 리스크 카테고리를 추출하는 엔드포인트.
        (실제 서비스 시 OpenAI Structured Outputs 또는 경량 LLM API 연동부)
        """
        from dto.schemas import RiskCategory

        # 1. 파일 업로드 형식(DataFrame) 처리인 경우
        if file_df is not None:
            try:
                # 엑셀의 첫 행이나 특정 컬럼에서 데이터를 파싱하는 규칙 기반 폴백
                item_name = str(file_df.iloc[0].get("품목명", file_df.iloc[0].get("item_name", "가상 SCM 반도체 부품")))
                quantity = float(file_df.iloc[0].get("수량", file_df.iloc[0].get("quantity", 100.0)))
                return {"item_name": item_name, "quantity": quantity, "category": RiskCategory.TECH_AND_SEMICONDUCTOR}
            except Exception:
                return {"item_name": "엑셀 업로드 부품", "quantity": 150.0, "category": RiskCategory.LOGISTICS_AND_TRADE}

        # 2. 자연어 텍스트 메모장 파싱인 경우
        if text:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, timeout=5.0)
                    
                    completion = client.beta.chat.completions.parse(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a precise SCM unstructured text parser."},
                            {"role": "user", "content": f"Parse the following text into SCM request details:\n{text}"}
                        ],
                        response_format=UnstructuredParseOutput,
                    )
                    parsed = completion.choices[0].message.parsed
                    if parsed:
                        cat_str = parsed.category
                        try:
                            # Map string to RiskCategory value if matched
                            if cat_str in RiskCategory.ALL:
                                category_val = cat_str
                            else:
                                category_val = RiskCategory.UNCLASSIFIED
                        except Exception:
                            category_val = RiskCategory.UNCLASSIFIED
                            
                        return {
                            "item_name": parsed.item_name,
                            "quantity": parsed.quantity,
                            "category": category_val
                        }
                except Exception as e:
                    logger.warning(f"⚠️ OpenAI Structured Output 파싱 실패 ({e}) - 정규식 폴백 작동")

            # [서킷 브레이커 Fallback] 정규식 및 텍스트 쪼가리 맥락 파악 규칙 기반 파싱
            import re
            cleaned = text.replace(" ", "")
            
            # 수량 추출 정규식 (예: 250개, 250ea, 250 개 등)
            qty_match = re.search(r'(\d+)(개|ea|톤|box|가지)', text.lower())
            quantity = float(qty_match.group(1)) if qty_match else 100.0
            
            # 품목명 유추
            item_name = "가상 SCM 반度體 부품"
            category = RiskCategory.LOGISTICS_AND_TRADE
            
            if "반도체" in text or "칩" in text or "반도체" in cleaned:
                item_name = "고성능 반도체 칩(MCU)"
                category = RiskCategory.TECH_AND_SEMICONDUCTOR
            elif "마스크" in text or "의료" in text:
                item_name = "보건용 마스크"
                category = RiskCategory.WEATHER_AND_CLIMATE
                
            return {
                "item_name": item_name,
                "quantity": quantity,
                "category": category
            }
            
        return {"item_name": "미분류 아이템", "quantity": 0.0, "category": RiskCategory.UNCLASSIFIED}
