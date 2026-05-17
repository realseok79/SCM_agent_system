# dto/schemas.py
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────────────────
# 리스크 카테고리 상수 (data_config.py 카테고리와 1:1 대응)
# ──────────────────────────────────────────────────────────
class RiskCategory:
    HEALTH_AND_BIOTECH       = "HEALTH_AND_BIOTECH"
    LOGISTICS_AND_TRADE      = "LOGISTICS_AND_TRADE"
    WEATHER_AND_CLIMATE      = "WEATHER_AND_CLIMATE"
    MACRO_ECONOMY            = "MACRO_ECONOMY"
    TECH_AND_SEMICONDUCTOR   = "TECH_AND_SEMICONDUCTOR"
    ENERGY_AND_RAW_MATERIALS = "ENERGY_AND_RAW_MATERIALS"
    LABOR_AND_WORKFORCE      = "LABOR_AND_WORKFORCE"
    REGULATORY_AND_POLICY    = "REGULATORY_AND_POLICY"
    CONSUMER_SENTIMENT       = "CONSUMER_SENTIMENT"
    UNCLASSIFIED             = "UNCLASSIFIED"

    ALL = [
        HEALTH_AND_BIOTECH, LOGISTICS_AND_TRADE, WEATHER_AND_CLIMATE,
        MACRO_ECONOMY, TECH_AND_SEMICONDUCTOR, ENERGY_AND_RAW_MATERIALS,
        LABOR_AND_WORKFORCE, REGULATORY_AND_POLICY, CONSUMER_SENTIMENT,
    ]


# ──────────────────────────────────────────────────────────
# 경보 레벨 상수 (Action Agent와 공유)
# ──────────────────────────────────────────────────────────
class AlertLevel(str, Enum):
    """
    [도입] 에이전트 간 비즈니스 신호 정합성을 위한 엄격한 Enum 클래스
    스트링 오타로 인한 가드레일 무력화 방지
    """
    NORMAL   = "NORMAL"    # 재고 > ROP: 발주 불필요
    WARNING  = "WARNING"   # 재고 ≤ ROP: 발주 실행
    CRITICAL = "CRITICAL"  # 재고 ≤ SS : 긴급 발주


# ──────────────────────────────────────────────────────────
# 운영 모드 상수 (LIVE_MODE 스위치)
# ──────────────────────────────────────────────────────────
class OperationMode:
    SIMULATION = "SIMULATION"  # 100일 시뮬레이션 루프
    LIVE       = "LIVE"        # 실시간 단발성 ROP 계산


# ──────────────────────────────────────────────────────────
# 핵심 DTO: 물품별 표준 마스터 데이터
# ──────────────────────────────────────────────────────────
@dataclass
class DemandDTO:
    """
    날것의 입력(엑셀/CSV/텍스트)이 파싱되어 저장될 표준 마스터 구조.
    """

    # ── 필수 식별 정보 ─────────────────────────────────────
    item_id          : str
    item_name        : str

    # ── 재고·수요 정보 ─────────────────────────────────────
    current_stock    : float = 0.0
    daily_demand_avg : float = 0.0
    daily_demand_std : float = 0.0

    # ── 조달 정보 ──────────────────────────────────────────
    lead_time_days   : float = 7.0
    lead_time_std    : float = 1.5

    # ── 비용 구조 ──────────────────────────────────────────
    unit_cost        : float = 0.0
    holding_cost_rate: float = 0.2     # 연간 20% 유지 비용
    stockout_cost    : float = 0.0

    # ── 리스크 분류 ────────────────────────────────────────
    risk_category    : str   = RiskCategory.UNCLASSIFIED

    # ── 확률 파라미터 ──────────────────────────────────────
    service_level    : float = 0.95    # 목표 서비스 수준 95%

    # ── 외부 신호 ──────────────────────────────────────────
    demand_impact    : float = 0.0     # Google Trends 충격 지수

    # ── 시스템 메타 ────────────────────────────────────────
    mode             : str   = OperationMode.SIMULATION
    timestamp        : str   = field(default_factory=lambda: datetime.now().isoformat())
    source_file      : str   = "unknown"

    # ──────────────────────────────────────────────────────
    # 파생 연산 프로퍼티 (Analysis Agent가 직접 사용)
    # ──────────────────────────────────────────────────────
    @property
    def effective_demand(self) -> float:
        """
        외부 충격 지수를 반영한 실효 수요.
        [보완책 3 반영] 극단적 충격(-1.0 이하) 시에도 베이스라인 수요의 최소 10%를 보장하여
        시스템이 완전히 마비(수요 0)되는 것을 방지합니다.
        """
        bounded_impact = max(self.demand_impact, -0.90)
        return round(self.daily_demand_avg * (1 + bounded_impact), 2)

    @property
    def safety_stock(self) -> float:
        """
        확률론적 안전재고 계산
        SS = Z × sqrt(LT × σ_d² + d² × σ_LT²)
        
        [보완책 1 반영] 수요 표준편차(daily_demand_std)가 누락되거나 너무 낮은 경우,
        평균 수요의 25%를 최소 변동성 하한선(Floor)으로 동적 적용합니다.
        """
        z = self._z_score(self.service_level)
        
        # 수요 표준편차 방어선 구축 (평균 수요의 25% 하한선)
        min_demand_std = self.daily_demand_avg * 0.25
        effective_demand_std = max(self.daily_demand_std, min_demand_std)
        
        ss = z * math.sqrt(
            self.lead_time_days * (effective_demand_std ** 2)
            + (self.effective_demand ** 2) * (self.lead_time_std ** 2)
        )
        return round(ss, 2)

    @property
    def reorder_point(self) -> float:
        """동적 발주점: ROP = 평균 수요 × 리드타임 + 안전재고"""
        return round(self.effective_demand * self.lead_time_days + self.safety_stock, 2)

    @property
    def alert_level(self) -> str:
        """현재 재고 기준 경보 수준 자동 판정"""
        if self.current_stock <= self.safety_stock:
            return AlertLevel.CRITICAL
        elif self.current_stock <= self.reorder_point:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    @property
    def eoq(self) -> float:
        """
        경제적 주문량 (EOQ)
        EOQ = sqrt(2 × D × S / H)
        
        [보완책 3 반영] 연간 수요 산출 시 effective_demand 대신 고정된 베이스라인인 
        daily_demand_avg를 기준으로 삼아 외부 신호 충격에 의한 발주 규모 왜곡을 막아줍니다.
        """
        annual_demand = self.daily_demand_avg * 365
        order_cost    = self.unit_cost * 0.03
        holding_cost  = self.unit_cost * self.holding_cost_rate
        
        if holding_cost == 0 or annual_demand == 0:
            return round(self.daily_demand_avg * 14, 2)  # 기본: 2주치 베이스라인 수요
        return round(math.sqrt(2 * annual_demand * order_cost / holding_cost), 2)

    @staticmethod
    def _z_score(service_level: float) -> float:
        """
        서비스 수준 → Z값 변환
        [보완책 2 반영] 슬라이더 조작 등으로 소수점 아래가 불규칙하게 들어와도
        예측 가능하고 정밀한 연산이 가능하도록 선형 보간(Linear Interpolation)을 적용합니다.
        """
        # 정적 참조 테이블 (오름차순 정렬 상태 유지)
        table = [
            (0.90, 1.282), (0.91, 1.341), (0.92, 1.405), (0.93, 1.476),
            (0.94, 1.555), (0.95, 1.645), (0.96, 1.751), (0.97, 1.881),
            (0.98, 2.054), (0.99, 2.326), (0.999, 3.090)
        ]
        
        # 하한 및 상한 가드레일
        if service_level <= table[0][0]:
            return table[0][1]
        if service_level >= table[-1][0]:
            return table[-1][1]
            
        # 선형 보간 수행
        for i in range(len(table) - 1):
            x0, y0 = table[i]
            x1, y1 = table[i+1]
            if x0 <= service_level <= x1:
                # 보간 공식: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
                z_interpolated = y0 + (service_level - x0) * (y1 - y0) / (x1 - x0)
                return round(z_interpolated, 3)
                
        return 1.645 # Fallback (기본 95%)

    def to_dict(self) -> dict:
        """직렬화 (JSON 저장, 로그 출력용)"""
        return {
            "item_id"          : self.item_id,
            "item_name"        : self.item_name,
            "current_stock"    : self.current_stock,
            "daily_demand_avg" : self.daily_demand_avg,
            "daily_demand_std" : self.daily_demand_std,
            "lead_time_days"   : self.lead_time_days,
            "lead_time_std"    : self.lead_time_std,
            "unit_cost"        : self.unit_cost,
            "holding_cost_rate": self.holding_cost_rate,
            "stockout_cost"    : self.stockout_cost,
            "risk_category"    : self.risk_category,
            "service_level"    : self.service_level,
            "demand_impact"    : self.demand_impact,
            "mode"             : self.mode,
            "timestamp"        : self.timestamp,
            "source_file"      : self.source_file,
            # 파생값
            "effective_demand" : self.effective_demand,
            "safety_stock"     : self.safety_stock,
            "reorder_point"    : self.reorder_point,
            "alert_level"      : self.alert_level,
            "eoq"              : self.eoq,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DemandDTO":
        """딕셔너리에서 복원 (엑셀/CSV 파싱 결과 → DTO 변환)"""
        return cls(
            item_id           = str(data.get("item_id", "UNKNOWN")),
            item_name         = str(data.get("item_name", "미지정 물품")),
            current_stock     = float(data.get("current_stock", 0.0)),
            daily_demand_avg  = float(data.get("daily_demand_avg", 0.0)),
            daily_demand_std  = float(data.get("daily_demand_std", 0.0)),
            lead_time_days    = float(data.get("lead_time_days", 7.0)),
            lead_time_std     = float(data.get("lead_time_std", 1.5)),
            unit_cost         = float(data.get("unit_cost", 0.0)),
            holding_cost_rate = float(data.get("holding_cost_rate", 0.2)),
            stockout_cost     = float(data.get("stockout_cost", 0.0)),
            risk_category     = data.get("risk_category", RiskCategory.UNCLASSIFIED),
            service_level     = float(data.get("service_level", 0.95)),
            demand_impact     = float(data.get("demand_impact", 0.0)),
            mode              = data.get("mode", OperationMode.SIMULATION),
            source_file       = data.get("source_file", "unknown"),
        )


@dataclass
class DataDTO:
    """
    Data Agent → Analysis Agent 
    과거 시계열 윈도우와 현재 가상 창고 상태를 통째로 전달하는 표준 데이터 격리 인터페이스
    """
    timestamp: str
    day: int
    daily_demand: float      # 당일 실제 발생한 수요 (스트레스 반영됨)
    current_stock: float     # 가상 시뮬레이터 창고의 실시간 재고 상태
    lead_time_days: float    # 당일 공급망 조달 기간 (스트레스 반영됨)
    weather_index: float     # 외부 변수: 날씨 지수
    macro_trend: float       # 외부 변수: 거시경제 인덱스
    
    # ── [확장] 정우의 확률론적 분포(평균, 표준편차) 연산을 위한 누적 데이터 윈도우 ──
    history_demand: list[float]     # 스트레스 오염이 격리된 순수 과거 수요 이력 배열
    history_lead_time: list[float]  # 스트레스 오염이 격리된 순수 과거 리드타임 이력 배열
    
    # ── [확장] GDELT DOC 2.0 API 공급망/지정학적 리스크 감성 분석 지표 ──
    gdelt_risk_level: str = "Low"
    gdelt_average_tone: float = 0.0
    gdelt_article_count: int = 0
    gdelt_top_headline: str = ""

    # ── [확장] Google Trends 수요 위험 지수 (data_config.py 키워드 매트릭스 연동) ──
    trend_composite_score: float = 0.0
    trend_matched_count: int = 0


@dataclass
class InventorySignalDTO:
    """
    Analysis Agent → Action Agent
    정우의 통계 엔진이 도출한 최적 발주 파라미터와 제어 시그널 인터페이스
    """
    timestamp: str
    day: int
    safety_stock: float        # [추가] 정우가 포아송/정규분포로 구한 '수학적 안전재고량'
    reorder_point: float       # [추가] 당일 가동되는 '동적 발주점 (ROP)' 기준선
    optimal_order_qty: float   # 경제적 발주량(EOQ) 기반 최적 제안 발주 수량
    confidence_level: float    # 통계적 신뢰 수준 (예: 0.95 -> 95%)
    alert_level: AlertLevel    # 엄격한 데이터 타입을 적용한 위기 경보 시그널
