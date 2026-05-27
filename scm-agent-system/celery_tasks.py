# celery_tasks.py
import os
import logging
from celery import Celery

logger = logging.getLogger("SCM_Celery")

# Redis 브로커 URL (기본값: 로컬호스트)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 앱 설정
app = Celery("scm_tasks", broker=REDIS_URL, backend=REDIS_URL)

# 로컬 노트북 환경에서 Redis가 동작하지 않을 경우 동기식 로컬 실행(Eager Mode)으로 자동 폴백
try:
    import redis
    client = redis.from_url(REDIS_URL)
    client.ping()
    app.conf.update(task_always_eager=False)
    logger.info("📡 Celery Broker (Redis) connected. Running in ASYNC mode.")
except Exception:
    app.conf.update(task_always_eager=True)
    logger.warning("⚠️ Redis server not available. Celery running in EAGER (SYNC) mode fallback.")

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)

@app.task(name="tasks.process_upload")
def process_upload_task(file_path):
    """
    엑셀/CSV 데이터 파이프라인 처리를 비동기로 수행하는 태스크
    """
    logger.info(f"🚀 [Celery Task] Starting file parsing: {file_path}")
    from utils.data_parser import parse_and_route_file
    try:
        stats = parse_and_route_file(file_path)
        logger.info(f"✅ [Celery Task] Parsing completed: {stats}")
        # 임시 파일 삭제
        if os.path.exists(file_path):
            os.remove(file_path)
        return stats
    except Exception as e:
        logger.error(f"❌ [Celery Task] Parsing failed: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e

@app.task(name="tasks.train_model")
def train_model_task(train_request_dict):
    """
    TFT 글로벌 모델 미세조정(Fine-Tuning)을 비동기로 수행하는 태스크 (비실행 모드 가드레일 적용)
    """
    logger.info(f"🚀 [Celery Task] Starting model fine-tuning for item: {train_request_dict.get('item_id')}")
    # ML/DL 비실행 모드 적용
    from agents.ml_agent import train_model, TrainModelRequest
    req = TrainModelRequest(**train_request_dict)
    res = train_model(req)
    logger.info(f"✅ [Celery Task] Model training completed: {res.trained_model_version}")
    return res.model_dump()
