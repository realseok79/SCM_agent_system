# dto/schemas.py
from dataclasses import dataclass
from enum import Enum

class AlertLevel(Enum):
    """
    [도입] 에이전트 간 비즈니스 신호 정합성을 위한 엄격한 Enum 클래스
    스트링 오타로 인한 가드레일 무력화 방지
    """
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


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
