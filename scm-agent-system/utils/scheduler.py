# utils/scheduler.py
import datetime
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from db import get_db_connection
from utils.weather_connector import get_weather_for_region, REGION_WEATHER_META
from utils.logger import get_logger
from utils.state_manager import load_lkv
from utils.scoring_engine import LogisticsRiskScorer
from agents.llm_diagnoser import generate_action_plan
from utils.connectors.iot_simulator import IoTSensorSimulator
from agents.enterprise_data_agent import TeamSigmaDataAgent

logger = get_logger("SCM_Scheduler")

def daily_weather_batch(force_refresh: bool = False):
    """
    모든 등록된 지역의 외부 기상 데이터를 자동으로 수집하여 내부 DB 캐시에 업데이트하는 배치 작업.
    """
    logger.info("🔄 [일일 배치 시작] 지역별 외부 환경 데이터 수집 및 캐시 갱신 시작...")
    
    # 1. DB에서 활성화된 지역 목록 조회
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT region_name, region_code FROM regions")
        regions = cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ 지역 목록 조회 실패: {e}")
        conn.close()
        return
        
    if not regions:
        logger.warning("⚠️ 등록된 지역이 없습니다. 배치를 스킵합니다.")
        conn.close()
        return
        
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 2. 각 지역별 날씨 동기화
    success_count = 0
    fail_count = 0
    
    for r in regions:
        r_name = r["region_name"]
        r_code = r["region_code"]
        logger.info(f"Processing weather for {r_name} ({r_code})...")
        
        try:
            # force_refresh=True인 경우 기존 오늘 캐시가 있더라도 무시하고 다시 API 호출하기 위해
            # 배치를 돌리기 전에 해당 지역의 오늘 날짜 캐시를 지우고 호출하도록 처리할 수 있습니다.
            if force_refresh:
                conn.execute(
                    "DELETE FROM weather_cache WHERE region_code = ? AND date = ?", 
                    (r_code, today_str)
                )
                conn.commit()
                
            weather = get_weather_for_region(r_code, today_str)
            logger.info(f"  ✅ {r_name} 날씨 업데이트 성공: Temp {weather['temp']}°C, Desc: {weather['weather_desc']}")
            success_count += 1
        except Exception as e:
            logger.error(f"  ❌ {r_name} 날씨 업데이트 실패: {e}")
            fail_count += 1
            
    conn.close()
    logger.info(f"🏁 [일일 배치 종료] 성공: {success_count}건, 실패: {fail_count}건 (기준일: {today_str})")

def daily_llm_insight_batch():
    """
    각 등록된 지점의 리스크 값을 계산하고, LLM Diagnoser를 통해 한 줄 처방(Action Plan)을 생성하여 DB에 캐싱하는 배치 작업.
    """
    logger.info("🤖 [AI 처방 배치 시작] SCM AI 처방 및 캐시 갱신 시작...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT region_name, region_code FROM regions")
        regions = cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ 지역 목록 조회 실패: {e}")
        conn.close()
        return
        
    if not regions:
        logger.warning("⚠️ 등록된 지역이 없습니다. AI 처방 배치를 스킵합니다.")
        conn.close()
        return
        
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    lkv_state = load_lkv()
    
    success_count = 0
    fail_count = 0
    
    # IoT 및 Spire 에이전트 초기화
    iot_sim = IoTSensorSimulator()
    enterprise_agent = TeamSigmaDataAgent()
    
    for r in regions:
        r_name = r["region_name"]
        r_code = r["region_code"]
        logger.info(f"Processing AI Action Plan for {r_name} ({r_code})...")
        
        # 국가 매핑
        code_upper = str(r_code).upper()
        if code_upper.startswith("KR-"):
            country = "South Korea"
        elif code_upper.startswith("US-"):
            country = "United States"
        elif code_upper.startswith("CN-"):
            country = "China"
        elif code_upper.startswith("JP-"):
            country = "Japan"
        elif code_upper.startswith("GB-"):
            country = "United Kingdom"
        else:
            country = "South Korea"
            
        country_data = lkv_state.get(country, {})
        raw_weather = country_data.get("weather", "[Fallback] 대체 기상 정보")
        data_vector = country_data.get("macro", {"oil_change_pct": 0.0, "inflation_rate": 2.0, "index_change_pct": 0.0, "fx_change_pct": 0.0})
        gdelt_info = country_data.get("gdelt", {"average_tone": 0.0, "risk_level": "Low", "top_headline": "Fallback Mode"})
        trend_info = country_data.get("trends", {"composite_score": 0.0, "matched_count": 0})
        
        # IoT 창고 건강 점수 산출
        iot_res = iot_sim.get_warehouse_health_score(r_code)
        iot_health = iot_res["warehouse_health_score"]
        
        # Spire Maritime 항만 혼잡도 점수 산출
        port_congestion = enterprise_agent.calculate_port_congestion_score()
        
        try:
            # 1. 리스크 스코어 계산
            scorer = LogisticsRiskScorer()
            scm_metrics = scorer.score_all(
                data_vector=data_vector,
                weather_text=raw_weather,
                trend_score=trend_info.get("composite_score", 0.0),
                gdelt_tone=gdelt_info.get("average_tone", 0.0),
                iot_health_score=iot_health,
                port_congestion_score=port_congestion
            )
            
            lt_delay = scm_metrics["lead_time_delay"]
            ds = scm_metrics["demand_shock_index"]
            action_code = scm_metrics["decision_action_code"]
            base_message = scm_metrics["decision_message"]
            r_total = scm_metrics["integrated_risk_score"]
            r_level = "HIGH" if r_total >= 60.0 else "LOW"
            r_desc = scm_metrics["delay_comment"]
            
            # 2. LLM 처방 텍스트 생성
            action_plan_msg = generate_action_plan(
                region_name=r_name,
                product_name="종합 품목",
                delay_days=lt_delay,
                demand_shock=ds,
                action_code=action_code,
                base_message=base_message
            )
            
            # 3. DB에 UPSERT 적재 (새로 추가한 risk_score, risk_level, description 포함)
            cursor.execute("""
                INSERT INTO regional_insights (region_code, date, action_plan_msg, risk_score, risk_level, description, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(region_code, date) DO UPDATE SET
                    action_plan_msg = excluded.action_plan_msg,
                    risk_score = excluded.risk_score,
                    risk_level = excluded.risk_level,
                    description = excluded.description,
                    updated_at = CURRENT_TIMESTAMP
            """, (r_code, today_str, action_plan_msg, r_total, r_level, r_desc))
            conn.commit()
            
            logger.info(f"  ✅ {r_name} SCM AI 처방 및 리스크 지표 업데이트 완료")
            success_count += 1
        except Exception as e:
            logger.error(f"  ❌ {r_name} SCM AI 처방 및 리스크 지표 업데이트 실패: {e}")
            fail_count += 1
            
    conn.close()
    logger.info(f"🏁 [AI 처방 배치 종료] 성공: {success_count}건, 실패: {fail_count}건 (기준일: {today_str})")

def start_scheduler():
    """
    백그라운드 스케줄러를 시작합니다.
    - 매일 오전 6시 정각에 일일 배치를 실행합니다.
    - 추가로 기동 즉시 최초 1회 갱신을 실행합니다.
    """
    scheduler = BackgroundScheduler()
    
    # 매일 06:00 AM 실행 크론 설정 (기상 데이터 동기화)
    scheduler.add_job(
        daily_weather_batch,
        trigger='cron',
        hour=6,
        minute=0,
        id='daily_weather_sync_job',
        replace_existing=True
    )
    
    # 매일 06:05 AM 실행 크론 설정 (AI 처방 갱신)
    scheduler.add_job(
        daily_llm_insight_batch,
        trigger='cron',
        hour=6,
        minute=5,
        id='daily_llm_insight_job',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("⏰ APScheduler 백그라운드 스케줄러가 성공적으로 가동되었습니다. (일일 배치: 매일 오전 6시)")
    
    # 최초 기동 시 비동기로 1회 강제 실행 (캐시 초기화)
    daily_weather_batch(force_refresh=False)
    daily_llm_insight_batch()
    
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting SCM Batch Scheduler stand-alone...")
    scheduler = start_scheduler()
    
    # 프로세스 유지
    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete.")
