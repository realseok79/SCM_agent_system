"""
simulator/m5_backtester.py
--------------------------
M5 데이터셋 전체 30,490개 SKU를 대상으로 Legacy 고정 SCM 정책과
AI Dynamic 최적화 SCM 정책의 100일간 백테스팅을 일괄 시뮬레이션하는 엔진.
대용량 NumPy 벡터 연산으로 구현되어 초고속 연산을 보장합니다.
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from simulator.m5_data_generator import M5DataGenerator
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent
from dto.schemas import BatchDemandDTO
from utils.logger import get_logger

logger = get_logger("M5Backtester")

def run_m5_backtest():
    logger.info("==================================================")
    logger.info("월마트 30,490개 SKU 전체 SCM 백테스팅 시뮬레이션 가동")
    logger.info("==================================================")
    
    # 1. 데이터 제너레이터 및 에이전트 초기화
    generator = M5DataGenerator()
    analysis_agent = AnalysisAgent()
    action_agent = ActionAgent()
    
    num_skus = generator.num_skus
    
    # 2. 초기 재고 설정 (각 SKU별 베이스라인 평균 수요의 15배로 합리적 세팅)
    legacy_stocks = generator.base_demand_avg * 15.0
    ai_stocks = generator.base_demand_avg * 15.0
    
    # 3. 조달 리드타임 큐 (배송 스케줄러) 초기화: { 입고일자(int): 입고수량벡터(np.ndarray) }
    legacy_arrivals = {}
    ai_arrivals = {}
    
    # 4. 일별 통계치 및 비용 누적 변수
    daily_stats = []
    
    cumulative_legacy_holding_cost = 0.0
    cumulative_legacy_stockout_cost = 0.0
    cumulative_ai_holding_cost = 0.0
    cumulative_ai_stockout_cost = 0.0
    
    # 품목별 누적 품절 발생 횟수 기록 (Top 10 Risk SKU 분석용)
    sku_legacy_stockout_counts = np.zeros(num_skus)
    sku_ai_stockout_counts = np.zeros(num_skus)
    
    start_date = datetime(2016, 5, 1)  # M5 평가 기간 가상 날짜 매핑
    
    logger.info("100일 루프 백테스팅 연산 개시...")
    
    for day in range(1, 101):
        # 당일 캘린더 날짜
        curr_date = (start_date + timedelta(days=day-1)).strftime("%Y-%m-%d")
        
        # M5 데이터 제너레이터로부터 당일 벡터 추출
        day_vector = generator.get_day_vector(day)
        actual_demand = day_vector["actual_demand"]
        sell_prices = day_vector["sell_prices"]
        lambda_new = day_vector["lambda_new"]
        signals = day_vector["external_signals"]
        
        # 당일 실제 리드타임 계산 (날씨 변동성에 따른 입고 지연율 적용)
        weather_shock = signals["weather_index"] - 1.0
        real_lead_time = int(round(7.0 * np.exp(0.5 * weather_shock)))
        real_lead_time = max(2, real_lead_time)  # 최소 리드타임 2일 보장
        
        # ──────────────────────────────────────────────────
        # A. Legacy SCM 시스템 시뮬레이션 (고정 ROP / SS / EOQ)
        # ──────────────────────────────────────────────────
        # 1. 당일 입고 처리
        legacy_stocks += legacy_arrivals.pop(day, np.zeros(num_skus))
        
        # 2. 당일 시장 수요 발생 및 재고 차감
        legacy_filled = np.minimum(legacy_stocks, actual_demand)
        legacy_stockout = actual_demand - legacy_filled
        legacy_stocks -= legacy_filled
        
        # 누적 품절 횟수 업데이트
        sku_legacy_stockout_counts[legacy_stockout > 0] += 1
        
        # 3. 고정 발주 실행 판단 (안전재고 SS: 4일 평균, ROP: 8일 평균, EOQ: 14일 평균)
        SS_legacy = 4.0 * generator.base_demand_avg
        ROP_legacy = 8.0 * generator.base_demand_avg
        EOQ_legacy = 14.0 * generator.base_demand_avg
        
        # 미도착 발주량(In-Transit) 계산
        legacy_in_transit = np.zeros(num_skus)
        for delivery_day, qty in legacy_arrivals.items():
            if delivery_day > day:
                legacy_in_transit += qty
                
        legacy_order_trigger = (legacy_stocks + legacy_in_transit) <= ROP_legacy
        legacy_order_qty = np.where(legacy_order_trigger, EOQ_legacy, 0.0)
        
        # 4. 리드타임 후 입고 예약 (Legacy는 항상 약정 7일 리드타임 고정 적용)
        legacy_delivery_day = day + 7
        legacy_arrivals[legacy_delivery_day] = legacy_arrivals.get(legacy_delivery_day, np.zeros(num_skus)) + legacy_order_qty
        
        # 5. 당일 Legacy 비용 연산 (유지비 = 재고 * 단가 * 0.05%, 품절패널티 = 품절량 * 단가 * 25%)
        legacy_holding = legacy_stocks * (sell_prices * 0.0005)
        legacy_stockout_p = legacy_stockout * (sell_prices * 0.25)
        
        cumulative_legacy_holding_cost += np.sum(legacy_holding)
        cumulative_legacy_stockout_cost += np.sum(legacy_stockout_p)
        
        # ──────────────────────────────────────────────────
        # B. AI Dynamic SCM 시스템 시뮬레이션 (동적 ROP / SS / EOQ & 이중 가드레일)
        # ──────────────────────────────────────────────────
        # 1. 당일 입고 처리
        ai_stocks += ai_arrivals.pop(day, np.zeros(num_skus))
        
        # 2. 당일 시장 수요 발생 및 재고 차감
        ai_filled = np.minimum(ai_stocks, actual_demand)
        ai_stockout = actual_demand - ai_filled
        ai_stocks -= ai_filled
        
        # 누적 품절 횟수 업데이트
        sku_ai_stockout_counts[ai_stockout > 0] += 1
        
        # 3. 에이전트 파이프라인 가동 (BatchDemandDTO 생성 - Inventory Position 반영!)
        # 미도착 발주량(In-Transit) 계산
        ai_in_transit = np.zeros(num_skus)
        for delivery_day, qty in ai_arrivals.items():
            if delivery_day > day:
                ai_in_transit += qty
                
        batch_demand = BatchDemandDTO(
            item_ids=generator.item_ids,
            item_names=generator.item_names,
            categories=generator.categories,
            current_stocks=ai_stocks + ai_in_transit,  # 재고 포지션 = 온핸드 + 미도착(In-Transit)
            daily_demand_avg=generator.base_demand_avg,
            daily_demand_std=generator.base_demand_std,
            lead_time_days=np.full(num_skus, 7.0),
            lead_time_std=np.full(num_skus, 1.5),
            unit_costs=sell_prices,
            stockout_costs=sell_prices * 1.5,
            demand_impacts=np.full(num_skus, signals["google_trends"] - 1.0),
            day=day,
            timestamp=datetime.now().isoformat(),
            mode="SIMULATION"
        )
        
        # Analysis Agent: 확률 최적화 연산
        ai_signals = analysis_agent.analyze_batch(batch_demand)
        
        # Action Agent: 이중 가드레일 필터링 및 승인 발주량 반환
        action_result = action_agent.execute_batch(ai_signals)
        approved_qty = action_result["approved_qty"]
        
        # 4. 동적 리드타임 반영 후 입고 예약 (실제 외부 기상 상황에 지연된 리드타임 적용)
        ai_delivery_day = day + real_lead_time
        ai_arrivals[ai_delivery_day] = ai_arrivals.get(ai_delivery_day, np.zeros(num_skus)) + approved_qty
        
        # 5. 당일 AI 비용 연산 (유지비 = 재고 * 단가 * 0.05%, 품절패널티 = 품절량 * 단가 * 25%)
        ai_holding = ai_stocks * (sell_prices * 0.0005)
        ai_stockout_p = ai_stockout * (sell_prices * 0.25)
        
        cumulative_ai_holding_cost += np.sum(ai_holding)
        cumulative_ai_stockout_cost += np.sum(ai_stockout_p)
        
        # ──────────────────────────────────────────────────
        # C. 데이터 집계 및 카테고리별 롤업(Rollup)
        # ──────────────────────────────────────────────────
        day_stats = {
            "day": day,
            "date": curr_date,
            "external_signals": signals,
            "legacy": {
                "holding_cost": float(np.sum(legacy_holding)),
                "stockout_cost": float(np.sum(legacy_stockout_p)),
                "total_cost": float(np.sum(legacy_holding) + np.sum(legacy_stockout_p)),
                "stock_level": float(np.mean(legacy_stocks)),
                "stockout_rate": float(np.mean(legacy_stockout > 0)) * 100.0
            },
            "ai": {
                "holding_cost": float(np.sum(ai_holding)),
                "stockout_cost": float(np.sum(ai_stockout_p)),
                "total_cost": float(np.sum(ai_holding) + np.sum(ai_stockout_p)),
                "stock_level": float(np.mean(ai_stocks)),
                "stockout_rate": float(np.mean(ai_stockout > 0)) * 100.0
            },
            "categories": {}
        }
        
        # 카테고리별 분할 집계
        for cat in np.unique(generator.categories):
            cat_mask = generator.categories == cat
            
            day_stats["categories"][cat] = {
                "legacy": {
                    "holding_cost": float(np.sum(legacy_holding[cat_mask])),
                    "stockout_cost": float(np.sum(legacy_stockout_p[cat_mask])),
                    "total_cost": float(np.sum(legacy_holding[cat_mask]) + np.sum(legacy_stockout_p[cat_mask])),
                    "stockout_rate": float(np.mean(legacy_stockout[cat_mask] > 0)) * 100.0
                },
                "ai": {
                    "holding_cost": float(np.sum(ai_holding[cat_mask])),
                    "stockout_cost": float(np.sum(ai_stockout_p[cat_mask])),
                    "total_cost": float(np.sum(ai_holding[cat_mask]) + np.sum(ai_stockout_p[cat_mask])),
                    "stockout_rate": float(np.mean(ai_stockout[cat_mask] > 0)) * 100.0
                }
            }
            
        daily_stats.append(day_stats)
        
        if day % 10 == 0 or day == 100:
            legacy_tc = cumulative_legacy_holding_cost + cumulative_legacy_stockout_cost
            ai_tc = cumulative_ai_holding_cost + cumulative_ai_stockout_cost
            savings_pct = (1.0 - ai_tc / legacy_tc) * 100.0 if legacy_tc > 0 else 0.0
            logger.info("[%3d/100일차] Legacy TC: ₩%.0f | AI TC: ₩%.0f | 절감률: %.1f%%",
                        day, legacy_tc, ai_tc, savings_pct)

    # 5. 리스크 상위 10개 SKU 분석 (Top 10 Risk SKU)
    # Legacy 하에서 가장 품절 횟수가 빈번한 아이템들을 추적하고 이들이 AI 도입 시 어떻게 개선되었는지 매핑
    top_10_indices = np.argsort(sku_legacy_stockout_counts)[-10:][::-1]
    
    top_10_skus = []
    for idx in top_10_indices:
        top_10_skus.append({
            "item_id": generator.item_ids[idx],
            "item_name": generator.item_names[idx],
            "category": generator.categories[idx],
            "store_id": generator.store_ids[idx],
            "legacy_stockout_days": int(sku_legacy_stockout_counts[idx]),
            "ai_stockout_days": int(sku_ai_stockout_counts[idx]),
            "improvement_pct": float((sku_legacy_stockout_counts[idx] - sku_ai_stockout_counts[idx]) / max(1, sku_legacy_stockout_counts[idx])) * 100.0
        })

    # 최종 결과 합본 파일 빌드
    results = {
        "summary": {
            "total_legacy_cost": cumulative_legacy_holding_cost + cumulative_legacy_stockout_cost,
            "total_ai_cost": cumulative_ai_holding_cost + cumulative_ai_stockout_cost,
            "savings": (cumulative_legacy_holding_cost + cumulative_legacy_stockout_cost) - (cumulative_ai_holding_cost + cumulative_ai_stockout_cost),
            "savings_pct": (1.0 - (cumulative_ai_holding_cost + cumulative_ai_stockout_cost) / (cumulative_legacy_holding_cost + cumulative_legacy_stockout_cost)) * 100.0,
            "average_legacy_stockout_rate": float(np.mean([d["legacy"]["stockout_rate"] for d in daily_stats])),
            "average_ai_stockout_rate": float(np.mean([d["ai"]["stockout_rate"] for d in daily_stats]))
        },
        "top_10_risk_skus": top_10_skus,
        "daily_stats": daily_stats
    }
    
    output_path = "outputs/m5_backtest_results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    logger.info("==================================================")
    logger.info("💾 SCM 백테스팅 결과 저장 완료 ➔ %s", output_path)
    logger.info("==================================================")

if __name__ == "__main__":
    run_m5_backtest()
