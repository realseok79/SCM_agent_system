# api.py
import sqlite3
import os
import shutil
import tempfile
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
            (user.username, user.email, user.role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user.username}' is already taken."
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
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
    # 1. 지역명 표준화 작업 진행 (서울 -> 서울특별시, KR-11)
    try:
        standardized_name, region_code = standardize_region(region.region_name)
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
            (standardized_name, region_code, region.description)
        )
        conn.commit()
        region_id = cursor.lastrowid
        
        cursor.execute("SELECT id, region_name, region_code, description, created_at FROM regions WHERE id = ?", (region_id,))
        row = cursor.fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Region '{standardized_name}' or code '{region_code}' is already registered."
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
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
@app.post("/api/regions/upload", status_code=status.HTTP_200_OK)
def upload_region_inventory(file: UploadFile = File(...)):
    """
    Excel 또는 CSV 파일을 업로드하여 지역별 재고/수요 데이터를 파싱하고 DB에 라우팅(UPSERT)합니다.
    """
    # 1. 파일 임시 저장
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    try:
        from utils.data_parser import parse_and_route_file
        stats = parse_and_route_file(tmp_path)
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ── ML Agent Router ──
from agents.ml_agent import router as ml_router
app.include_router(ml_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
