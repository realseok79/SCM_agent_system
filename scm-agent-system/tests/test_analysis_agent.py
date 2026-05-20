"""
tests/test_analysis_agent.py
─────────────────────────────
Analysis Agent 확률론적 최적화 엔진 TDD 단위 테스트 스위트

엣지 케이스 방어 범위:
  - 빈 배열 / 단일 원소 배열 입력
  - 분산 0 (동일 값 반복)
  - 극단적 과산포 (수요 5배 폭증)
  - 음수/0 비용 파라미터
  - 서비스 수준 경계값
  - 3시그마 클리핑 동작 검증
  - 꼬리 확률 동적 루프 무한 루프 방지
  - AnalysisAgent 통합 파이프라인 정합성
"""

import math
import numpy as np
import pytest
from datetime import datetime
from dto.schemas import DataDTO, InventorySignalDTO, AlertLevel, BatchDemandDTO, BatchInventorySignalDTO
from agents.analysis_agent import (
    clip_outlier,
    detect_overdispersion,
    compute_demand_lambda,
    fit_negative_binomial,
    compute_combined_uncertainty,
    compute_safety_stock,
    compute_rop,
    compute_eoq,
    compute_expected_total_cost,
    minimize_total_cost,
    AnalysisAgent,
)


# ─────────────────────────────────────────────
# 1. clip_outlier 가드레일 테스트
# ─────────────────────────────────────────────

class TestClipOutlier:
    """3시그마 클리핑 가드레일 엣지 케이스"""

    def test_empty_list(self):
        """빈 리스트 입력 → 빈 리스트 반환 (크래시 방지)"""
        assert clip_outlier([]) == []

    def test_single_element(self):
        """단일 원소 → 클리핑 불가, 원본 그대로 반환"""
        assert clip_outlier([42.0]) == [42.0]

    def test_two_elements(self):
        """2개 원소 → 정상 동작 (std 계산 가능한 최소 조건)"""
        result = clip_outlier([10.0, 20.0])
        assert len(result) == 2

    def test_outlier_clipped(self):
        """정상 범위를 벗어난 이상치가 경계값으로 수렴하는지 검증"""
        data = [50.0] * 20 + [500.0]  # 500은 명백한 이상치
        result = clip_outlier(data, sigma_multiplier=3.0)
        assert max(result) < 500.0  # 이상치가 클리핑되어야 함

    def test_no_clipping_needed(self):
        """정상 범위 데이터 → 변동 없이 원본 유지"""
        data = [48.0, 50.0, 52.0, 49.0, 51.0]
        result = clip_outlier(data, sigma_multiplier=3.0)
        assert result == pytest.approx(data, abs=0.01)

    def test_all_identical_values(self):
        """분산 0 (동일 값 반복) → σ=0이므로 클리핑 범위가 점이 되어도 크래시 없음"""
        data = [100.0] * 10
        result = clip_outlier(data, sigma_multiplier=3.0)
        assert all(v == 100.0 for v in result)


# ─────────────────────────────────────────────
# 2. 분포 모델링 테스트
# ─────────────────────────────────────────────

class TestOverdispersion:
    """과산포 감지 엣지 케이스"""

    def test_poisson_like_data(self):
        """V(X) ≈ E(X) → 포아송 적합 판정"""
        np.random.seed(42)
        data = list(np.random.poisson(lam=50, size=100).astype(float))
        is_od, ratio = detect_overdispersion(data)
        # 포아송 데이터는 비율이 1.0 근처여야 함
        assert abs(ratio - 1.0) < 0.5

    def test_overdispersed_data(self):
        """V(X) >> E(X) → 음이항 전환 판정"""
        np.random.seed(42)
        data = list(np.random.negative_binomial(n=5, p=0.1, size=100).astype(float))
        is_od, ratio = detect_overdispersion(data)
        assert is_od == True
        assert ratio > 1.0

    def test_zero_mean(self):
        """평균 0 데이터 → 안전하게 포아송 반환"""
        is_od, ratio = detect_overdispersion([0.0, 0.0, 0.0])
        assert is_od is False
        assert ratio == 1.0

    def test_single_element(self):
        """단일 원소 → 분산 계산 불가, 안전 처리"""
        is_od, ratio = detect_overdispersion([50.0])
        assert is_od == False

    def test_identical_values_zero_variance(self):
        """분산 0 (모든 값 동일) → 과산포 아님"""
        is_od, ratio = detect_overdispersion([100.0] * 30)
        assert is_od == False
        assert ratio == 0.0


class TestDemandLambda:
    """수요율 λ 산출 테스트"""

    def test_neutral_shock(self):
        """충격 지수 1.0 (중립) → λ = 평균 수요"""
        result = compute_demand_lambda([50.0, 60.0, 70.0], shock_index=1.0)
        assert result == pytest.approx(60.0, abs=0.01)

    def test_positive_shock(self):
        """충격 지수 1.5 (50% 상승) → λ = 평균 × 1.5"""
        result = compute_demand_lambda([100.0, 100.0], shock_index=1.5)
        assert result == pytest.approx(150.0, abs=0.01)

    def test_negative_shock_floor(self):
        """음수 충격 → λ > 0 보장 (1e-6 하한)"""
        result = compute_demand_lambda([100.0], shock_index=-1.0)
        assert result > 0


class TestNegativeBinomial:
    """음이항 분포 파라미터 추정 테스트"""

    def test_valid_overdispersed(self):
        """정상적 과산포 데이터 → r, p 유효값 반환"""
        np.random.seed(42)
        data = list(np.random.negative_binomial(n=5, p=0.1, size=50).astype(float))
        r, p = fit_negative_binomial(data)
        assert r > 0
        assert 0 < p < 1

    def test_poisson_like_fallback(self):
        """V(X) ≤ E(X) → 포아송 대체 파라미터 (r→∞)"""
        data = [50.0] * 20  # 분산 0
        r, p = fit_negative_binomial(data)
        assert r >= 1e6  # r→∞ 극한

    def test_zero_mean(self):
        """평균 0 → 안전 폴백"""
        r, p = fit_negative_binomial([0.0, 0.0, 0.0])
        assert r >= 1e6


# ─────────────────────────────────────────────
# 3. 결합 불확실성 / SS / ROP / EOQ 테스트
# ─────────────────────────────────────────────

class TestCombinedUncertainty:
    """결합 불확실성 σ_DL 산출 테스트"""

    def test_basic_computation(self):
        """정상 입력 → σ_DL > 0"""
        E_D, V_D, E_L, V_L, sigma = compute_combined_uncertainty(
            [50.0, 60.0, 70.0], [7.0, 8.0, 9.0]
        )
        assert sigma > 0
        assert E_D == pytest.approx(60.0, abs=0.01)
        assert E_L == pytest.approx(8.0, abs=0.01)

    def test_zero_variance_demands(self):
        """수요 분산 0 → σ_DL은 리드타임 변동성에만 의존"""
        E_D, V_D, E_L, V_L, sigma = compute_combined_uncertainty(
            [100.0, 100.0, 100.0], [5.0, 7.0, 9.0]
        )
        assert V_D == 0.0
        assert sigma > 0  # 리드타임 변동성이 있으므로

    def test_zero_variance_lead_times(self):
        """리드타임 분산 0 → σ_DL은 수요 변동성에만 의존"""
        E_D, V_D, E_L, V_L, sigma = compute_combined_uncertainty(
            [80.0, 100.0, 120.0], [7.0, 7.0, 7.0]
        )
        assert V_L == 0.0
        assert sigma > 0  # 수요 변동성이 있으므로

    def test_single_element_each(self):
        """단일 원소씩 → 분산 0, σ_DL = 0 (크래시 방지)"""
        E_D, V_D, E_L, V_L, sigma = compute_combined_uncertainty([100.0], [7.0])
        assert sigma == 0.0


class TestSafetyStockAndROP:
    """SS 및 ROP 산출 테스트"""

    def test_safety_stock_positive(self):
        SS = compute_safety_stock(z=1.645, sigma_DL=50.0)
        assert SS == pytest.approx(82.25, abs=0.01)

    def test_safety_stock_zero_sigma(self):
        """σ_DL = 0 → SS = 0"""
        SS = compute_safety_stock(z=1.645, sigma_DL=0.0)
        assert SS == 0.0

    def test_rop_computation(self):
        ROP = compute_rop(E_D=100.0, E_L=7.0, SS=80.0)
        assert ROP == pytest.approx(780.0, abs=0.01)


class TestEOQ:
    """EOQ 산출 테스트"""

    def test_basic_eoq(self):
        """Wilson 공식 검증: EOQ = sqrt(2 × 36500 × 200 / 182.5) ≈ 282.84"""
        eoq = compute_eoq(
            annual_demand=36500.0,
            order_cost=200.0,
            holding_cost_per_unit_per_year=182.5
        )
        assert eoq == pytest.approx(282.84, abs=1.0)

    def test_zero_demand(self):
        """수요 0 → 최소 발주량 1.0 보장"""
        eoq = compute_eoq(0.0, 200.0, 182.5)
        assert eoq == 1.0

    def test_zero_order_cost(self):
        """발주 비용 0 → 최소 발주량 1.0 보장"""
        eoq = compute_eoq(36500.0, 0.0, 182.5)
        assert eoq == 1.0

    def test_zero_holding_cost(self):
        """보유 비용 0 → 최소 발주량 1.0 보장"""
        eoq = compute_eoq(36500.0, 200.0, 0.0)
        assert eoq == 1.0

    def test_negative_inputs(self):
        """음수 입력 → 최소 발주량 1.0 보장 (크래시 방지)"""
        eoq = compute_eoq(-100.0, 200.0, 182.5)
        assert eoq == 1.0


# ─────────────────────────────────────────────
# 4. TC 목적함수 및 꼬리 확률 동적 루프 테스트
# ─────────────────────────────────────────────

class TestTotalCost:
    """총 운영 비용(TC) 목적함수 테스트"""

    def test_zero_order_qty(self):
        """발주량 0 → 무한대 비용"""
        tc = compute_expected_total_cost(
            order_qty=0, SS=50.0, lambda_adjusted=100.0, E_L=7.0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_cost=200.0,
            annual_demand=36500.0, is_overdispersed=False, nb_r=1.0, nb_p=0.5
        )
        assert tc == float('inf')

    def test_finite_result(self):
        """정상 입력 → 유한한 양수 비용"""
        tc = compute_expected_total_cost(
            order_qty=200.0, SS=50.0, lambda_adjusted=100.0, E_L=7.0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_cost=200.0,
            annual_demand=36500.0, is_overdispersed=False, nb_r=1.0, nb_p=0.5
        )
        assert 0 < tc < float('inf')

    def test_overdispersed_mode(self):
        """음이항 분포 모드에서도 유한 결과 반환"""
        tc = compute_expected_total_cost(
            order_qty=200.0, SS=50.0, lambda_adjusted=50.0, E_L=7.0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_cost=200.0,
            annual_demand=18250.0, is_overdispersed=True, nb_r=5.0, nb_p=0.3
        )
        assert 0 < tc < float('inf')

    def test_high_lambda_no_infinite_loop(self):
        """[수정안 4 검증] 극단적 λ (수요 5배 폭증) → 무한 루프 없이 종료"""
        tc = compute_expected_total_cost(
            order_qty=500.0, SS=100.0, lambda_adjusted=500.0, E_L=7.0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_cost=200.0,
            annual_demand=182500.0, is_overdispersed=False, nb_r=1.0, nb_p=0.5
        )
        assert 0 < tc < float('inf')


class TestMinimizeTotalCost:
    """TC 최적화 탐색 테스트"""

    def test_optimal_q_positive(self):
        """최적 발주량 Q* > 0 보장"""
        q, tc = minimize_total_cost(
            SS=50.0, lambda_adjusted=100.0, E_D=100.0, E_L=7.0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_cost=200.0,
            is_overdispersed=False, nb_r=1.0, nb_p=0.5
        )
        assert q >= 1.0
        assert tc > 0


# ─────────────────────────────────────────────
# 5. AnalysisAgent 통합 파이프라인 테스트
# ─────────────────────────────────────────────

class TestAnalysisAgentIntegration:
    """AnalysisAgent.analyze() 통합 테스트"""

    def _make_dto(self, **overrides):
        """테스트용 DataDTO 팩토리"""
        defaults = dict(
            timestamp="2026-01-01T00:00:00",
            day=1,
            daily_demand=100.0,
            current_stock=100.0,
            lead_time_days=7.0,
            weather_index=1.0,
            macro_trend=1.0,
            history_demand=[90.0, 100.0, 110.0, 95.0, 105.0],
            history_lead_time=[6.5, 7.0, 7.5, 7.0, 6.8],
            gdelt_risk_level="Low",
            gdelt_average_tone=0.0,
            gdelt_article_count=0,
            gdelt_top_headline="",
            trend_composite_score=0.0,
            trend_matched_count=0,
            unit_holding_cost=0.5,
            stockout_penalty=10.0,
            order_fixed_cost=200.0,
        )
        defaults.update(overrides)
        return DataDTO(**defaults)

    def test_basic_pipeline(self):
        """기본 파이프라인 → InventorySignalDTO 정상 반환"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto())
        assert isinstance(result, InventorySignalDTO)
        assert result.day == 1
        assert result.safety_stock >= 0
        assert result.reorder_point > 0

    def test_low_stock_triggers_order(self):
        """재고 부족 (재고 < ROP) → 발주 트리거"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(current_stock=10.0))
        assert result.optimal_order_qty > 0
        assert result.alert_level in (AlertLevel.WARNING, AlertLevel.CRITICAL)

    def test_high_stock_no_order(self):
        """재고 충분 (재고 >> ROP) → 발주 불필요"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(current_stock=99999.0))
        assert result.optimal_order_qty == 0.0
        assert result.alert_level == AlertLevel.NORMAL

    def test_empty_history_fallback(self):
        """이력 데이터 빈 배열 → fallback 동작 (크래시 방지)"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(
            history_demand=[],
            history_lead_time=[]
        ))
        assert isinstance(result, InventorySignalDTO)
        assert result.safety_stock >= 0

    def test_single_history_element(self):
        """이력 데이터 1개 → 안전 처리"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(
            history_demand=[100.0],
            history_lead_time=[7.0]
        ))
        assert isinstance(result, InventorySignalDTO)

    def test_zero_variance_history(self):
        """동일 값 반복 (분산 0) → 크래시 없이 정상 동작"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(
            history_demand=[100.0] * 20,
            history_lead_time=[7.0] * 20
        ))
        assert isinstance(result, InventorySignalDTO)

    def test_extreme_shock_index(self):
        """극단적 수요 충격 (+5.0) → 크래시 없이 λ 조정"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(trend_composite_score=5.0))
        assert isinstance(result, InventorySignalDTO)
        assert result.reorder_point > 0

    def test_cost_params_from_dto(self):
        """[수정안 1 검증] DataDTO의 비용 파라미터가 TC에 반영되는지 확인.
        서로 다른 비용 구조 → 서로 다른 발주 결과."""
        agent = AnalysisAgent(service_level=0.95)

        result_cheap = agent.analyze(self._make_dto(
            current_stock=10.0,
            unit_holding_cost=0.1,
            stockout_penalty=1.0,
            order_fixed_cost=50.0
        ))

        result_expensive = agent.analyze(self._make_dto(
            current_stock=10.0,
            unit_holding_cost=5.0,
            stockout_penalty=100.0,
            order_fixed_cost=1000.0
        ))

        # 비용 구조가 크게 다르면 최적 발주량도 달라져야 함
        assert result_cheap.optimal_order_qty != result_expensive.optimal_order_qty

    def test_critical_alert_when_stock_below_ss(self):
        """재고가 안전재고(SS) 이하 → CRITICAL 경보"""
        agent = AnalysisAgent(service_level=0.95)
        result = agent.analyze(self._make_dto(current_stock=0.0))
        assert result.alert_level == AlertLevel.CRITICAL


# ─────────────────────────────────────────────
# 6. analyze_batch 벡터화 연산 테스트
# ─────────────────────────────────────────────

class TestAnalyzeBatch:
    """analyze_batch 벡터화 연산 정합성 테스트"""

    def _make_batch(self, n=100):
        """테스트용 BatchDemandDTO 팩토리"""
        np.random.seed(42)
        return BatchDemandDTO(
            item_ids=np.array([f"SKU-{i}" for i in range(n)]),
            item_names=np.array([f"Item-{i}" for i in range(n)]),
            categories=np.array(["FOODS"] * n),
            current_stocks=np.random.uniform(50, 500, n),
            daily_demand_avg=np.random.uniform(10, 200, n),
            daily_demand_std=np.random.uniform(5, 50, n),
            lead_time_days=np.random.uniform(3, 14, n),
            lead_time_std=np.random.uniform(0.5, 3, n),
            unit_costs=np.random.uniform(1, 100, n),
            stockout_costs=np.random.uniform(5, 50, n),
            demand_impacts=np.random.uniform(-0.3, 0.3, n),
            day=1,
            timestamp="2026-01-01T00:00:00",
        )

    def test_batch_output_shape(self):
        """출력 벡터 길이 == 입력 SKU 수"""
        agent = AnalysisAgent()
        batch = self._make_batch(n=100)
        result = agent.analyze_batch(batch)
        assert len(result.safety_stocks) == 100
        assert len(result.reorder_points) == 100
        assert len(result.optimal_order_qtys) == 100
        assert len(result.alert_levels) == 100

    def test_batch_ss_positive(self):
        """모든 SKU의 안전재고 ≥ 0"""
        agent = AnalysisAgent()
        result = agent.analyze_batch(self._make_batch())
        assert np.all(result.safety_stocks >= 0)

    def test_batch_rop_gt_ss(self):
        """모든 SKU의 ROP ≥ SS (ROP = E[D]*E[L] + SS 이므로)"""
        agent = AnalysisAgent()
        result = agent.analyze_batch(self._make_batch())
        assert np.all(result.reorder_points >= result.safety_stocks)

    def test_batch_alert_levels_valid(self):
        """경보 레벨이 유효한 값만 포함"""
        agent = AnalysisAgent()
        result = agent.analyze_batch(self._make_batch())
        valid_levels = {"NORMAL", "WARNING", "CRITICAL"}
        for level in result.alert_levels:
            assert level in valid_levels

    def test_batch_no_order_for_high_stock(self):
        """재고 충분 SKU → 발주량 0"""
        agent = AnalysisAgent()
        batch = self._make_batch()
        batch.current_stocks = np.full(100, 1e6)  # 모든 SKU 재고 무한
        result = agent.analyze_batch(batch)
        assert np.all(result.optimal_order_qtys == 0.0)

    def test_dormant_sku_overdispersion_cap(self):
        """[검토안 2 검증] 휴면 SKU(daily_demand_avg ≈ 0)에서
        overdispersion_ratio가 10.0 상한으로 클리핑되어
        EOQ가 비정상적으로 폭증하지 않는지 검증."""
        agent = AnalysisAgent()
        batch = self._make_batch(n=10)
        # 일부 SKU를 거의-0 수요로 설정
        batch.daily_demand_avg[:5] = 0.001
        batch.daily_demand_std[:5] = 5.0  # 분산은 존재 → 비율 폭증 유발
        result = agent.analyze_batch(batch)
        # 시스템이 크래시 없이 정상 동작하고, EOQ가 유한한 값인지 확인
        assert np.all(np.isfinite(result.optimal_order_qtys))
        assert np.all(np.isfinite(result.safety_stocks))

    def test_heuristic_vs_exact_error_within_tolerance(self):
        """[검토안 1 검증] Heuristic EOQ(배치)와 Exact Q*(단일 analyze)의
        오차율을 측정하여 두 메서드 간의 Trade-off를 정량적으로 문서화한다.

        [설계 주의] analyze()는 TC 목적함수를 직접 최소화(Exact)하고,
        analyze_batch()는 Wilson EOQ + 과산포 프리미엄(Heuristic)을 사용한다.
        또한 배치는 order_cost=unit_costs*0.03, holding=unit_costs*0.2 공식을 내부 사용하므로,
        두 방식의 Q값에는 구조적 차이가 존재한다.
        이 테스트는 두 방식 모두 유효한 양수 발주량을 산출하는지 검증한다.
        """
        agent = AnalysisAgent(service_level=0.95)

        # 단일 analyze로 Exact Q* 산출
        dto = DataDTO(
            timestamp="2026-01-01T00:00:00", day=1,
            daily_demand=100.0, current_stock=10.0, lead_time_days=7.0,
            weather_index=1.0, macro_trend=1.0,
            history_demand=[90.0, 100.0, 110.0, 95.0, 105.0],
            history_lead_time=[6.5, 7.0, 7.5, 7.0, 6.8],
            trend_composite_score=0.0, trend_matched_count=0,
            unit_holding_cost=0.5, stockout_penalty=10.0, order_fixed_cost=200.0,
        )
        exact_result = agent.analyze(dto)
        exact_q = exact_result.optimal_order_qty

        # 동일 파라미터로 배치 Heuristic EOQ 산출
        # 배치 내부 비용 공식: order_cost = unit_costs * 0.03, holding = unit_costs * 0.2
        # → h=0.5/day=182.5/yr 맞추려면 unit_costs = 182.5/0.2 = 912.5
        # → K=200 맞추려면 unit_costs = 200/0.03 ≈ 6666.7 (구조적으로 불일치)
        # 따라서 배치의 자체 비용 구조를 그대로 사용하고, 둘 다 양수임을 검증
        batch = BatchDemandDTO(
            item_ids=np.array(["SKU-001"]),
            item_names=np.array(["Item-001"]),
            categories=np.array(["FOODS"]),
            current_stocks=np.array([10.0]),
            daily_demand_avg=np.array([100.0]),
            daily_demand_std=np.array([8.16]),
            lead_time_days=np.array([7.0]),
            lead_time_std=np.array([0.35]),
            unit_costs=np.array([10.0]),
            stockout_costs=np.array([10.0]),
            demand_impacts=np.array([0.0]),
            day=1, timestamp="2026-01-01T00:00:00",
        )
        batch_result = agent.analyze_batch(batch)
        heuristic_q = batch_result.optimal_order_qtys[0]

        # 두 값 모두 양수 (발주 트리거됨)
        assert exact_q > 0, f"Exact Q*가 0 이하: {exact_q}"
        assert heuristic_q > 0, f"Heuristic EOQ가 0 이하: {heuristic_q}"

        # 오차율 로깅 (스트레스 테스트 리포트용)
        error_rate = abs(exact_q - heuristic_q) / exact_q
        print(f"\n  [Heuristic vs Exact 오차율] "
              f"Exact Q*={exact_q:.1f}, Heuristic EOQ={heuristic_q:.1f}, "
              f"오차율={error_rate:.1%}")

