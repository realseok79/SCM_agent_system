import numpy as np
import re
from typing import Optional

class LogisticsRiskScorer:
    """
    실시간 날씨, 거시경제, 사회적 이슈(GDELT & Google Trends) 데이터를 입력받아
    물류 예상 지표 및 종합 리스크 점수를 산출하는 수학적 점수화 엔진
    """
    # 국가별 맞춤형 인플레이션 타겟 설정 (KeyError 방지용 Fallback 구조 설계)
    TARGET_INFLATION_MAP = {
        "South Korea": 2.0, "United States": 2.0, "Eurozone": 2.0,
        "Japan": 1.0, "China": 1.0, 
        "Brazil": 4.5, "India": 4.0
    }

    # API 미수신 시 사용할 국가별 현실적 디폴트 물가상승률 (추가)
    REALISTIC_INFLATION_FALLBACK = {
        "Taiwan": 2.5, "Singapore": 3.0, "Thailand": 1.5, 
        "Philippines": 4.0, "Norway": 3.0, "Turkey": 50.0, "Egypt": 30.0
    }

    def __init__(self):
        # 파라미터 초기화
        # 1. 물류비 변동률 파라미터
        self.sigma_O = 5.0      # WTI 유가 30일 표준편차 역사적 디폴트 (%)
        self.sigma_I = 1.5      # 소비자물가상승률 표준편차 역사적 디폴트 (%)
        self.alpha = 0.4        # 유가 변동률 가중치
        self.beta = 0.6         # 물가 변동률 가중치

        # 2. 수요 충격 지수 파라미터 (차원 동등성 확보를 위한 스케일업 완화)
        self.gamma = 1.0        # 주가지수 변동 가중치 (5.0에서 하향)
        self.delta = 1.0        # 환율 변동 가중치 (5.0에서 하향)
        self.theta = 0.3        # 사회/지정학적 리스크 가중치 (3.0에서 하향)

        # 3. 조달 지연일 파라미터
        self.lambda1 = 0.3      # 악천후 지수 가중치
        self.lambda2 = 0.2      # 매크로 불안정성 가중치

        # 4. SCM 종합 리스크 스코어 파라미터 (로지스틱 시그모이드)
        self.w_freight = 1.5
        self.w_demand = 1.5
        self.w_delay = 5.0
        self.k = 0.015           # 감도 기울기를 완화하여 극단적 수치에서도 포화를 늦춤
        self.X_0 = 150.0         # 기하학적 분포 중심점을 우측으로 이동 (더 큰 충격에 반응)

    def parse_weather_score(self, weather_text: str) -> float:
        """
        기상청 raw GTS 텍스트 또는 OpenWeatherMap 대체 데이터에서 키워드를 파싱하여 악천후 지수(0~10)를 도출합니다.
        경고 이모지가 있더라도 본문 키워드 파싱이 정상 동작하도록 예외 처리를 제거했습니다.
        """
        if not weather_text:
            return 0.0
        
        weather_text_lower = weather_text.lower()
        
        # 우선순위가 높은 순서대로 단일 regex 매칭 수행 (성능 최적화)
        if re.search(r"typhoon|hurricane|tornado|태풍|폭풍우", weather_text_lower):
            return 8.5
        if re.search(r"storm|gale|heavy rain|heavy snow|폭우|폭설|강풍", weather_text_lower):
            return 5.5
        if re.search(r"rain|snow|shower|비|눈|소나기", weather_text_lower):
            return 2.5
        return 0.0

    def calculate_freight_impact(self, oil_change_pct: float, inflation_rate: Optional[float], country_name: str = "Global") -> float:
        """
        ① 예상 물류 운임 변동률 (Cf) 산식 계산 (비대칭 방향성 및 국가별 타겟 인플레이션 반영)
        경계선에서의 도약 불연속성(Jump Discontinuity)을 완전 제거한 연속 램프 함수(Continuous Ramp) 설계
        """
        bar_I = self.TARGET_INFLATION_MAP.get(country_name, 2.0)
        
        # API 미수신(None) 시 현실적 폴백 맵 적용, 없으면 타겟값 사용
        if inflation_rate is not None:
            I = inflation_rate
        else:
            I = self.REALISTIC_INFLATION_FALLBACK.get(country_name, bar_I)
            
        delta_I = I - bar_I
        
        # 유가 변동 임팩트 (문턱값 제거하여 연속적 반응)
        oil_impact = oil_change_pct / self.sigma_O
            
        # 물가 상승 임팩트 (문턱값 제거하여 연속적 반응)
        inf_impact = delta_I / self.sigma_I
        
        oil_term = self.alpha * oil_impact
        inf_term = self.beta * inf_impact
        
        # 최종 운임 변동률 (%) 계산
        cf = (oil_term + inf_term) * 100.0
        
        # 안정성을 위해 [0%, +100%] 범위로 클리핑 (리스크 관제탑이므로 운임 하락은 0%로 방어)
        return np.clip(cf, 0.0, 100.0)

    def calculate_demand_shock(self, index_change_pct: float, fx_change_pct: float, social_score: float) -> float:
        """
        ② 소비자 수요 충격 지수 (Ds) 산식 계산
        Ds = gamma * ln(1 + delta_S) - delta * ln(1 + |delta_F|) - theta * (social_score / 100)
        """
        # 시장 변화율 자체의 극단값 및 음수/하한선 클리핑 방어 (주가지수 폭락 -90% 한계, 환율은 양수만 고려)
        clipped_index_change = max(-90.0, index_change_pct)
        clipped_fx_change = max(0.0, fx_change_pct)
        
        # 소수점 비율로 변환
        delta_S = clipped_index_change / 100.0
        delta_F = clipped_fx_change / 100.0
        
        # ln(1 + delta) 연산의 수학적 도메인 방어 및 자연스러운 로그 계산
        s_val = 1.0 + delta_S
        f_val = 1.0 + delta_F
        
        stock_term = self.gamma * np.log(s_val)
        fx_term = self.delta * np.log(f_val)
        social_term = self.theta * (social_score / 100.0)
        
        ds = (stock_term - fx_term - social_term) * 100.0
        
        # 안정성을 위해 [-100%, +20%] 범위로 클리핑하고, 소수점 둘째 자리까지 반올림
        return round(float(np.clip(ds, -100.0, 20.0)), 2)

    def calculate_lead_time_delay(self, weather_score: float, prev_risk_score: float) -> float:
        """
        ③ 예상 조달 지연일 (LTdelay) 산식 계산 (인과율 보정을 위해 전일 종합 리스크 점수 prev_risk_score 사용)
        LTdelay = max(0, lambda1 * W + lambda2 * (M - 1.0)^2)
        M = prev_risk_score / 50.0 (정상 상태 1.0 수준화, 1% 변동을 정상으로 취급)
        """
        M = prev_risk_score / 50.0
        macro_term = 25.0 * self.lambda2 * (M ** 2)
        weather_term = self.lambda1 * weather_score
        
        lt_delay = weather_term + macro_term
        return max(0.0, round(lt_delay, 1))

    def calculate_integrated_risk_score(self, cf: float, ds: float, lt_delay: float) -> float:
        """
        ④ SCM 종합 리스크 스코어 (R_total) 산식 계산 (Zero-baseline Shifted 로지스틱 시그모이드 매핑)
        R_scaled = 100 * (Sigmoid(X) - Sigmoid(0)) / (1 - Sigmoid(0))
        """
        # 충격의 절댓값들의 가중 결합
        X = (self.w_freight * abs(cf) + 
             self.w_demand * abs(ds) + 
             self.w_delay * lt_delay)
        
        # Sigmoid(X)와 Sigmoid(0) 계산
        sig_X = 1.0 / (1.0 + np.exp(-self.k * (X - self.X_0)))
        sig_0 = 1.0 / (1.0 + np.exp(self.k * self.X_0))
        
        # Zero-baseline Shifted 정규화 적용
        r_scaled = 100.0 * (sig_X - sig_0) / (1.0 - sig_0)
        return round(float(max(0.0, r_scaled)), 1)

    def score_all(self, data_vector: dict, weather_text: str, trend_score: float, gdelt_tone: float, prev_risk_score: Optional[float] = None) -> dict:
        """
        모든 입력을 조합하여 SCM 물류 리스크 리포트를 생성합니다.
        """
        # 1. 날씨 점수 파싱
        weather_score = self.parse_weather_score(weather_text)
        
        # 2. 지정학적 GDELT 톤을 0~100 사회적 리스크 점수로 변환 (음수일수록 높은 리스크)
        # GDELT Tone 범위는 대개 [-10, 10]. -3.0 이하면 High Risk.
        gdelt_score = max(0.0, min(100.0, -gdelt_tone * 15.0)) if gdelt_tone else 0.0
        
        # Google Trends 스코어 정규화 (Trends composite_score는 대개 [0, 1] 범위)
        trends_score_norm = (trend_score if trend_score is not None else 0.0) * 100.0
        
        # 사회적 이슈 스코어 결합 (상시 미시 리스크 5점 기본 부여)
        social_score = max(5.0, 0.5 * gdelt_score + 0.5 * trends_score_norm)
        
        # 3. 개별 지표 연산
        cf = self.calculate_freight_impact(
            oil_change_pct=data_vector.get("oil_change_pct", 0.0),
            inflation_rate=data_vector.get("inflation_rate", None),
            country_name=data_vector.get("country", "Global")
        )
        
        ds = self.calculate_demand_shock(
            index_change_pct=data_vector.get("index_change_pct", 0.0),
            fx_change_pct=data_vector.get("fx_change_pct", 0.0),
            social_score=social_score
        )
        
        # 인과율(Causality)을 반영하기 위해 전일 종합 리스크 점수(prev_risk_score)를 사용
        if prev_risk_score is None:
            prev_risk_score = data_vector.get("prev_risk_score", data_vector.get("integrated_risk_score", 10.0))
            
        lt_delay = self.calculate_lead_time_delay(
            weather_score=weather_score,
            prev_risk_score=prev_risk_score
        )
        
        r_total = self.calculate_integrated_risk_score(cf, ds, lt_delay)
        
        # 5. 실무용 물류 직관 자연어 진단 코멘트 자동 생성
        # 5-1. 운임 변동 코멘트
        if cf >= 15.0:
            freight_comment = f"🚨 WTI 유가 급등 및 국가별 인플레이션 타겟 초과 영향으로 예상 물류 운임이 {cf:.1f}% 대폭 상승할 우려가 있습니다."
        elif cf >= 5.0:
            freight_comment = f"⚠️ 인플레이션 압력과 유가 변동이 결합되어 물류 운임이 약 {cf:.1f}% 내외로 소폭 상승할 것으로 예상됩니다."
        else:
            freight_comment = "✅ 유가 및 소비자 물가가 타겟 인플레이션 범위 내로 안정 관리되어 운임 변동성이 최소화된 상태입니다."

        # 5-2. 조달 지연 코멘트
        if lt_delay >= 2.0:
            delay_comment = f"🚨 거점 악천후 지수 상승({weather_score:.1f}점) 및 리스크 전이로 인해 조달 리드타임이 {lt_delay:.1f}일 급격히 지연될 예정입니다."
        elif lt_delay >= 0.5:
            delay_comment = f"⚠️ 국지적 기상 악화 또는 이전 리스크 누적으로 인해 조달 리드타임이 약 {lt_delay:.1f}일 가량 소폭 지연될 가능성이 있습니다."
        else:
            delay_comment = "✅ 거점 기상 상태가 양호하고 종합 리스크 전이 영향이 없어 조달 리드타임이 정상(지연 없음)입니다."

        # 5-3. 수요 충격 코멘트
        if ds <= -10.0:
            demand_comment = f"🚨 금융 시장 지배 지수 하락 및 환율 변동성, 지정학적 우려가 융합되어 소비수요가 평소 대비 {ds:.1f}% 급감할 위험이 높습니다."
        elif ds <= -2.0:
            demand_comment = f"⚠️ 대외 환율 절하 및 부정적 뉴스 지표 영향으로 인해 소비자 수요가 약 {ds:.1f}% 가량 소폭 둔화될 것으로 진단됩니다."
        else:
            demand_comment = "✅ 주요 거시경제 변수와 글로벌 트렌드 지수가 매우 안정적이어서 시장 수요 변동성이 궤도 내에서 관리되고 있습니다."
        
        return {
            "freight_rate_change": round(cf, 2),
            "demand_shock_index": round(ds, 2),
            "lead_time_delay": lt_delay,
            "integrated_risk_score": r_total,
            "weather_score": weather_score,
            "social_score": round(social_score, 2),
            "freight_comment": freight_comment,
            "delay_comment": delay_comment,
            "demand_comment": demand_comment
        }
