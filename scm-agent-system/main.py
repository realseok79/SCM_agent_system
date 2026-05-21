# main.py
import os
from datetime import datetime
from dotenv import load_dotenv

from simulator.time_engine import TimeSimulator
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent
from utils.logger import get_logger

from db import init_db, seed_initial_data, get_db_connection

load_dotenv()
logger = get_logger("SimulatorCore")

# Clone 직후에도 안전하게 DB 초기화 및 시드 데이터 적재
init_db()
seed_initial_data()

# ── [자가 치유] scm_dummy_data.json 파일 부재 시 자동 생성 ──
from agents.config import PATHS
dummy_path = PATHS["SCM_DATA"]
if not os.path.exists(dummy_path):
    logger.info(f"⚠️ 가상 SCM 더미 데이터({dummy_path})가 존재하지 않아 자동 생성을 개시합니다.")
    try:
        from simulator.data_generator import SCMDataGenerator
        generator = SCMDataGenerator(start_date="2026-01-01", days=100)
        df = generator.generate()
        generator.save_json(df, path=dummy_path)
        logger.info("✅ 가상 SCM 더미 데이터 자동 생성 및 저장 완료!")
    except Exception as e:
        logger.error(f"❌ 더미 데이터 자동 생성 실패: {e}")

# ── [데이터 격리/멱등성 보장] 시뮬레이션 재가동 시 이전 가동 일지(2026-01-01 이후) 초기화 ──
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_out_logs WHERE timestamp >= '2026-01-01'")
    cursor.execute("DELETE FROM daily_demand_stats WHERE date >= '2026-01-01'")
    conn.commit()
    conn.close()
    logger.info("🧹 이전 시뮬레이션 가동 데이터(2026-01-01 이후) 초기화 완료. 신규 클린 세션 기동!")
except Exception as e:
    logger.error(f"⚠️ 이전 시뮬레이션 데이터 초기화 오류: {e}")

# 에이전트 인스턴스 싱글톤 유지 (상태/히스토리 보존)
data_agent = DataAgent()
analysis_agent = AnalysisAgent()
action_agent = ActionAgent()


# ── [고도화] 가상 창고 물리 엔진 상태 변수 선언 ──────────────────────
current_stock = 1500.0  # 초기 재고 상태 (안전 자산 수준에서 시작)

# 리드타임 딜레이 큐 체계 체택: { 입고예정일(day): 입고수량(qty) }
arrival_queue: dict[int, float] = {}


def run_pipeline(day: int, current_date: datetime, stress_event: dict):
    """
    시뮬레이터에서 매일 틱(Tick)마다 호출하는 엔터프라이즈 파이프라인 제어 루프
    """
    global current_stock, arrival_queue

    logger.info(f"🔄 [시뮬레이션 {day}일차] 창고 재고 점검 개시 | 현재 고 가용 재고: {current_stock:.0f}개")

    # [피드백 루프 Step 1] 공급망 리드타임 지연 경과에 따른 실제 조달 물품 창고 입고 처리
    today_arrival = arrival_queue.pop(day, 0.0)
    if today_arrival > 0:
        current_stock += today_arrival
        logger.info(f"📦 [공급망 조달 완료] {day}일차 입고 스케줄에 따라 {today_arrival:.0f}개가 가상 창고에 하역되었습니다. (현재 재고: {current_stock:.0f}개)")

    # 1. 데이터 수집 및 정제 (과거 누적 히스토리 및 보정된 동적 재고 상태 동시 주입)
    raw = data_agent.collect(day, current_date, stress_event, current_stock)
    
    # [피드백 루프 Step 2] 당일 시장 실제 수요 발생에 따른 재고 실시간 차감 연산
    actual_demand = raw.daily_demand
    if current_stock >= actual_demand:
        current_stock -= actual_demand
        stockout_units = 0.0
    else:
        stockout_units = actual_demand - current_stock
        current_stock = 0.0  # 품절 발생
        logger.error(f"🚨 [CRITICAL STOCKOUT] 창고 재고 완전 고갈! 미충족 수요 패널티 발생: -{stockout_units:.0f}개")

    # ── [고도화] 배치 트랜잭션 큐잉 및 Bulk Insert 적재 ──
    import numpy as np
    from utils.demand_tracker import log_stock_out_bulk, aggregate_daily_demand
    
    step_logs = []
    date_str = current_date.strftime("%Y-%m-%d")
    timestamp_str = f"{date_str} 12:00:00"
    
    for r in ["KR-11", "KR-26", "KR-49"]:
        for p in ["마스크", "반도체 칩", "종합 품목"]:
            if r == "KR-11" and p == "반도체 칩":
                qty = actual_demand
            else:
                if p == "마스크":
                    qty = float(np.random.poisson(150.0))
                elif p == "반도체 칩":
                    vmr = 7.0
                    p_param = 1.0 / vmr
                    r_param = 30.0 * p_param / (1.0 - p_param)
                    qty = float(np.random.negative_binomial(r_param, p_param))
                else:
                    qty = float(max(0.0, np.random.normal(85.0, 20.0)))
                
                if stress_event.get("is_stress"):
                    qty *= stress_event.get("demand_multiplier", 1.0)
                
                if current_date.weekday() in [5, 6]:
                    qty *= 0.4
                    
                qty = round(qty, 1)
            
            if qty > 0:
                step_logs.append({
                    "region_code": r,
                    "product_name": p,
                    "outbound_qty": qty,
                    "transaction_type": "정상출고",
                    "timestamp": timestamp_str
                })
                
    log_stock_out_bulk(step_logs)
    aggregate_daily_demand(date_str)

    # 2. 확률론적 수요 분석 및 안전재고/ROP/최적발주량(EOQ기반) 수학적 연산 (정우 파트)
    signal = analysis_agent.analyze(raw)
    
    # 3. 이중 가드레일 비즈니스 제약조건 검증 및 발주 실행 (진석 파트)
    result = action_agent.execute(signal)

    # [피드백 루프 Step 3] 발주가 정상 승인된 경우, 마법 배송이 아닌 실제 예측된 '리드타임' 후에 입고되도록 큐에 동적 예약
    if result.get("action") == "ORDER_EXECUTED":
        approved_qty = result.get("approved_qty", 0.0)
        
        if approved_qty > 0:
            # 정우와 API가 도출해 낸 그 시점의 리드타임을 정수형 날짜 틱으로 변환
            predicted_lead_time = int(round(raw.lead_time_days))
            arrival_day = day + predicted_lead_time
            
            # 미래의 입고일자에 수량 누적
            arrival_queue[arrival_day] = arrival_queue.get(arrival_day, 0.0) + approved_qty
            logger.info(f"🛒 [발주 실행 완료] {approved_qty:.0f}개 승인 승인 완료 ➔ 예측 리드타임({predicted_lead_time}일) 적용으로 인해 [{arrival_day}일차]에 창고 입고 예정.")


if __name__ == "__main__":
    # ── [데이터 오염 방지] 시뮬레이션 가동 직전 기존 로그 파일 포맷(Initialize) ──
    def initialize_simulation_files():
        """이전 시뮬레이션의 유령 데이터를 깨끗이 제거하여 대시보드 정합성 확보"""
        import json as _json

        from agents.config import PATHS
        history_file = PATHS["ORDER_HISTORY"]
        if os.path.exists(history_file):
            with open(history_file, "w", encoding="utf-8") as f:
                _json.dump([], f)
            logger.info(f"🧹 [초기화] 발주 이력 파일 포맷 완료: {history_file}")

        # 2. 과거 비상 보고서(emergency_report_day*.json) 전부 삭제
        output_dir = "outputs"
        if os.path.exists(output_dir):
            removed = 0
            for filename in os.listdir(output_dir):
                if filename.startswith("emergency_report_day") and filename.endswith(".json"):
                    os.remove(os.path.join(output_dir, filename))
                    removed += 1
            if removed > 0:
                logger.info(f"🧹 [초기화] 이전 비상 리포트 {removed}건 삭제 완료")

    initialize_simulation_files()
    logger.info("🚀 SCM AI 다중 에이전트 다이나믹 시뮬레이션 코어 가동")
    sim = TimeSimulator()
    
    # 파이프라인 실행
    sim.run(run_pipeline)

    # ── [동기화] 시뮬레이션 완료 후 Java Spring Boot 중앙 백엔드와 자동 데이터 동기화 ──
    try:
        from utils.backend_sync import sync_simulation_to_backend
        sync_simulation_to_backend()
    except Exception as e:
        logger.error(f"⚠️ 백엔드 자동 동기화 호출 실패 (무시하고 진행): {e}")
