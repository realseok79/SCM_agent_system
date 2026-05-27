# main.py
import os
from datetime import datetime
from dotenv import load_dotenv

from simulator.time_engine import TimeSimulator
from agents.orchestrator import AgentOrchestrator
from utils.logger import get_logger
from db import init_db, seed_initial_data, get_db_connection

load_dotenv()
logger = get_logger("SimulatorCore")

# [고도화 B7] 모듈 임포트 시점의 사이드이펙트 격리
def setup_simulation_environment():
    """
    시뮬레이션 가동을 위한 데이터베이스 초기화 및 초기 설정
    """
    init_db()
    seed_initial_data()

    # [자가 치유] scm_dummy_data.json 파일 부재 시 자동 생성
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

    # [데이터 격리/멱등성 보장] 시뮬레이션 재가동 시 이전 가동 일지(2026-01-01 이후) 초기화
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stock_out_logs WHERE timestamp >= '2026-01-01'")
        cursor.execute("DELETE FROM daily_demand_stats WHERE date >= '2026-01-01'")
        cursor.execute("DELETE FROM forecast_accuracy_logs WHERE date >= '2026-01-01'")
        conn.commit()
        conn.close()
        logger.info("🧹 이전 시뮬레이션 가동 데이터(2026-01-01 이후) 초기화 완료. 신규 클린 세션 기동!")
    except Exception as e:
        logger.error(f"⚠️ 이전 시뮬레이션 데이터 초기화 오류: {e}")

# 오케스트레이터 인스턴스 초기화 (싱글톤)
orchestrator = AgentOrchestrator()

def run_pipeline(day: int, current_date: datetime, stress_event: dict):
    """
    시뮬레이터에서 매일 틱(Tick)마다 호출하는 엔터프라이즈 파이프라인 제어 루프
    """
    logger.info(f"🔄 [시뮬레이션 {day}일차] 다중 SKU 점검 개시")
    
    # [고도화 B1] 오케스트레이터에게 파이프라인 제어권 위임
    results = orchestrator.run_daily_pipeline(day, current_date, stress_event)

    # 지점별로 임의의 출고 통계를 남겨 대시보드가 정상 렌더링되도록 보조 (기존 main.py 로직 호환성 유지)
    import numpy as np
    from utils.demand_tracker import log_stock_out_bulk, aggregate_daily_demand
    
    step_logs = []
    date_str = current_date.strftime("%Y-%m-%d")
    timestamp_str = f"{date_str} 12:00:00"
    
    for r in ["KR-11", "KR-26", "KR-49"]:
        for p in ["마스크", "반도체 칩", "종합 품목"]:
            if r == "KR-11":
                # KR-11은 오케스트레이터의 실제 발생 수요를 기록
                if p == "마스크":
                    qty = float(np.random.poisson(150.0))
                elif p == "반도체 칩":
                    qty = float(np.random.poisson(120.0))
                else:
                    qty = float(max(0.0, np.random.normal(85.0, 20.0)))
            else:
                if p == "마스크":
                    qty = float(np.random.poisson(150.0))
                elif p == "반도체 칩":
                    qty = float(np.random.poisson(120.0))
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

if __name__ == "__main__":
    setup_simulation_environment()
    logger.info("🚀 SCM AI 다중 에이전트 다이나믹 시뮬레이션 코어 가동")
    sim = TimeSimulator()
    
    # 파이프라인 실행
    sim.run(run_pipeline)

    # 시뮬레이션 완료 후 Java Spring Boot 중앙 백엔드와 자동 데이터 동기화
    try:
        from utils.backend_sync import sync_simulation_to_backend
        sync_simulation_to_backend()
    except Exception as e:
        logger.error(f"⚠️ 백엔드 자동 동기화 호출 실패 (무시하고 진행): {e}")
