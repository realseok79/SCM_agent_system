# scm-agent-system/utils/backend_sync.py
import os
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("BackendSynchronizer")

# Spring Boot 중앙 서버 URL 및 설정
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
COMPANY_ID = os.getenv("COMPANY_ID", "COMPANY_SIGMA")

def sync_simulation_to_backend():
    """
    로컬 SQLite DB(sigma_enterprise.db)의 시뮬레이션 최종 재고 데이터를 
    Java Spring Boot 백엔드의 Dynamic Excel Ingestion Engine(SAEIE) API를 통해 동기화합니다.
    """
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/sigma_enterprise.db"))
    if not os.path.exists(db_path):
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/sigma_enterprise.db"))
        
    if not os.path.exists(db_path):
        logger.warning(f"⚠️ [동기화 실패] 로컬 SQLite DB가 존재하지 않습니다: {db_path}")
        return False

    # 1. Spring Boot 백엔드가 구동 중인지 확인 (Health Check)
    try:
        res = requests.get(f"{BACKEND_URL}/api/regions", timeout=2)
        if res.status_code != 200:
            logger.info("ℹ️ [백엔드 오프라인] Spring Boot 서버가 응답하지 않아 로컬 SQLite 단독 모드로 유지합니다.")
            return False
    except Exception:
        logger.info("ℹ️ [백엔드 오프라인] Spring Boot 서버가 꺼져 있어 로컬 SQLite 단독 모드로 유지합니다.")
        return False

    logger.info("🔌 [백엔드 감지] Spring Boot 중앙 백엔드 서버가 활성화되어 있습니다. 데이터 동기화를 개시합니다.")

    try:
        # 2. SQLite에서 최신 시뮬레이션 재고 데이터 추출
        conn = sqlite3.connect(db_path)
        query = """
            SELECT region_code, product_name, date, quantity 
            FROM region_inventory
            ORDER BY date ASC, region_code ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            logger.warning("⚠️ [동기화 취소] 동기화할 재고 데이터가 비어 있습니다.")
            return False

        # 3. Spring Boot Dynamic Ingestion 엔진이 이해할 수 있는 컬럼 헤더로 매핑
        # 한국어/영어 매핑 헤더 구조 지원
        df_export = df.rename(columns={
            "region_code": "지점코드",
            "product_name": "상품명",
            "date": "날짜",
            "quantity": "수량"
        })

        # 임시 CSV 파일 저장
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../outputs"))
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, "simulation_sync_payload.csv")
        df_export.to_csv(temp_file_path, index=False, encoding="utf-8-sig")

        logger.info(f"📦 동기화 페이로드 CSV 파일 생성 완료: {temp_file_path} (총 {len(df_export)}건)")

        # 4. Spring Boot Ingestion API(/api/regions/upload) 호출하여 파일 전송
        with open(temp_file_path, "rb") as f:
            files = {"file": ("simulation_sync_payload.csv", f, "text/csv")}
            data = {"company_id": COMPANY_ID}
            
            logger.info(f"🚀 Spring Boot Dynamic Ingestion API 호출 중... (URL: {BACKEND_URL}/api/regions/upload)")
            response = requests.post(
                f"{BACKEND_URL}/api/regions/upload",
                data=data,
                files=files,
                timeout=15
            )

        if response.status_code == 200:
            res_data = response.json()
            logger.info("=============================================================")
            logger.info("✅ [동기화 성공] Spring Boot PostgreSQL 데이터베이스 동기화 완료!")
            logger.info(f"   ➔ 배치 ID: {res_data.get('batch_id', 'N/A')}")
            logger.info(f"   ➔ 처리 상태: {res_data.get('status', 'SUCCESS')}")
            logger.info(f"   ➔ 정합성 검증 결과: {res_data.get('validation_summary', 'N/A')}")
            logger.info("=============================================================")
            
            # 임시 파일 삭제
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return True
        else:
            logger.error(f"❌ [동기화 실패] 백엔드 서버 에러 발생 (HTTP {response.status_code}): {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ [동기화 오류] 백엔드 동기화 중 예상치 못한 에러 발생: {e}")
        return False
