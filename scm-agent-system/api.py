# api.py
import sqlite3
import os
import shutil
import tempfile
import json
import re
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

def sanitize_string(text: str) -> str:
    if not text:
        return text
    # Strip HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    # Strip dangerous characters like quotes, semicolons, etc.
    text = re.sub(r"['\";\-]+", "", text)
    return text.strip()


from db import get_db_connection, init_db
from models import (
    UserCreate, UserResponse,
    RegionCreate, RegionResponse,
    standardize_region
)

# 데이터베이스 테이블 초기화
init_db()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 백그라운드 스케줄러 라이프사이클 관리 ──
    from utils.scheduler import start_scheduler
    app.state.scheduler = start_scheduler()
    yield
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

app = FastAPI(
    title="SCM Region & Data Pipeline Core API",
    description="사용자 및 SCM 지역 관리, 엑셀/CSV 데이터 파이프라인 처리를 위한 코어 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    allowed_origins = ["http://localhost:8501", "http://127.0.0.1:8501"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health Check ──
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "green",
        "service": "SCM API Engine",
        "sqlite_journal_mode": "WAL"
    }

# ── User CRUD Endpoints ──

@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    from db import log_system_action
    s_username = sanitize_string(user.username)
    s_email = sanitize_string(user.email) if user.email else None
    s_role = sanitize_string(user.role)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
            (s_username, s_email, s_role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        res = dict(row)
        
        # Log audit action
        log_system_action(
            user_id="anonymous",
            ip_address="127.0.0.1",
            event_type="USER_CREATED",
            action_details=f"Created user {s_username} with role {s_role}",
            new_state=json.dumps(res),
            is_automated=0
        )
        return res
    except Exception as e:
        conn.rollback()
        err_msg = str(e)
        if "UNIQUE" in err_msg or "already taken" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{s_username}' is already taken."
            )
        raise HTTPException(status_code=500, detail=err_msg)
    finally:
        conn.close()

@app.get("/api/users", response_model=List[UserResponse])
def list_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ── Region CRUD Endpoints ──

@app.post("/api/regions", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
def create_region(region: RegionCreate):
    from db import log_system_action
    s_region_name = sanitize_string(region.region_name)
    s_description = sanitize_string(region.description) if region.description else None
    
    # 1. 지역명 표준화 작업 진행 (서울 -> 서울특별시, KR-11)
    try:
        standardized_name, region_code = standardize_region(s_region_name)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO regions (region_name, region_code, description) VALUES (?, ?, ?)",
            (standardized_name, region_code, s_description)
        )
        conn.commit()
        region_id = cursor.lastrowid
        
        cursor.execute("SELECT id, region_name, region_code, description, created_at FROM regions WHERE id = ?", (region_id,))
        row = cursor.fetchone()
        res = dict(row)
        
        # Log audit action
        log_system_action(
            user_id="anonymous",
            ip_address="127.0.0.1",
            event_type="REGION_CREATED",
            action_details=f"Created region {standardized_name} ({region_code})",
            new_state=json.dumps(res),
            is_automated=0
        )
        return res
    except Exception as e:
        conn.rollback()
        err_msg = str(e)
        if "UNIQUE" in err_msg or "already registered" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Region '{standardized_name}' or code '{region_code}' is already registered."
            )
        raise HTTPException(status_code=500, detail=err_msg)
    finally:
        conn.close()

@app.get("/api/regions", response_model=List[RegionResponse])
def list_regions():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, region_name, region_code, description, created_at FROM regions ORDER BY region_name ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/regions/{region_id}", response_model=RegionResponse)
def get_region(region_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, region_name, region_code, description, created_at FROM regions WHERE id = ?", (region_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Region not found.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/regions/{region_id}", status_code=status.HTTP_200_OK)
def delete_region(region_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 존재 여부 확인
        cursor.execute("SELECT id FROM regions WHERE id = ?", (region_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Region not found.")
            
        cursor.execute("DELETE FROM regions WHERE id = ?", (region_id,))
        conn.commit()
        return {"message": f"Region with ID {region_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ── Excel/CSV Ingestion Routing Endpoint ──
@app.post("/api/regions/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_region_inventory(file: UploadFile = File(...)):
    """
    Excel 또는 CSV 파일을 업로드하여 지역별 재고/수요 데이터를 파싱하고 DB에 라우팅(UPSERT)합니다.
    (Celery 비동기 태스크 큐 격리 수행)
    """
    filename = file.filename or ""
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in [".csv", ".xlsx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv and .xlsx files are allowed."
        )

    # 10MB 제한 검사 (Content-Length 및 청크 단위 읽기 결합)
    content_length = file.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size exceeds the 10MB limit."
                )
        except ValueError:
            pass

    max_size = 10 * 1024 * 1024
    size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in iter(lambda: file.file.read(8192), b""):
            size += len(chunk)
            if size > max_size:
                tmp.close()
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size exceeds the 10MB limit."
                )
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        from celery_tasks import process_upload_task
        task = process_upload_task.delay(tmp_path)
        
        # Eager Mode (동기) 일 때는 즉시 결과 리턴
        if task.ready():
            res = task.result
            if isinstance(res, Exception):
                raise res
            return res
            
        return {"status": "ACCEPTED", "task_id": task.id, "message": "File processing has been queued."}
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Eager Mode에서 성공 시 이미 celery task가 삭제했을 수 있지만,
        # ready()가 참일 때만 안전하게 삭제 시도
        if 'task' in locals() and task.ready():
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# ── ML Agent Router ──
from agents.ml_agent import router as ml_router
app.include_router(ml_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
