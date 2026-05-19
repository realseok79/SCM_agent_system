# utils/scheduler.py
import datetime
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from db import get_db_connection
from utils.weather_connector import get_weather_for_region, REGION_WEATHER_META
from utils.logger import get_logger

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

def start_scheduler():
    """
    백그라운드 스케줄러를 시작합니다.
    - 매일 오전 6시 정각에 일일 배치를 실행합니다.
    - 추가로 기동 즉시 최초 1회 갱신을 실행합니다.
    """
    scheduler = BackgroundScheduler()
    
    # 매일 06:00 AM 실행 크론 설정
    scheduler.add_job(
        daily_weather_batch,
        trigger='cron',
        hour=6,
        minute=0,
        id='daily_weather_sync_job',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("⏰ APScheduler 백그라운드 스케줄러가 성공적으로 가동되었습니다. (일일 배치: 매일 오전 6시)")
    
    # 최초 기동 시 비동기로 1회 강제 실행 (캐시 초기화)
    daily_weather_batch(force_refresh=False)
    
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
