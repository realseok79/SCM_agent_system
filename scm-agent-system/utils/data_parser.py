# utils/data_parser.py
import os
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional

from db import get_db_connection, DB_PATH
from models import standardize_region

# 컬럼 퍼지 매칭 키워드 정의 (소문자 공백 제거 상태로 매칭)
COLUMN_ALIASES = {
    "region": ["지점", "지역", "지역명", "region", "regionname", "location", "branch"],
    "product": ["상품명", "상품이름", "품목", "품목명", "product", "productname", "producttitle", "product_title", "item"],
    "quantity": ["수량", "개수", "양", "quantity", "qty", "count", "amount"],
    "date": ["날짜", "일자", "기준일", "date", "datetime", "day"]
}

def find_column_mapping(columns: list) -> dict:
    """
    파일의 컬럼명 목록에서 SCM 표준 컬럼(region, product, quantity, date)에 매핑되는 인덱스/명칭을 반환합니다.
    """
    mapping = {}
    for col in columns:
        cleaned_col = str(col).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        for standard_key, aliases in COLUMN_ALIASES.items():
            if cleaned_col in aliases:
                mapping[standard_key] = col
                break
    return mapping

def parse_and_route_file(file_path: str) -> dict:
    """
    CSV 또는 Excel 파일을 로드하여 데이터를 파싱하고,
    지역 표준코드로 매핑하여 region_inventory 테이블에 UPSERT 처리합니다.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
    # 확장자 파악 및 로드
    _, ext = os.path.splitext(file_path.lower())
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    elif ext in [".csv"]:
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")
        
    columns = list(df.columns)
    mapping = find_column_mapping(columns)
    
    # 필수 컬럼(지점, 상품, 수량) 존재 확인
    for req in ["region", "product", "quantity"]:
        if req not in mapping:
            raise ValueError(f"필수 컬럼이 누락되었습니다: '{req}'에 매핑할 수 있는 헤더를 찾을 수 없습니다. (현재 헤더: {columns})")
            
    success_count = 0
    error_count = 0
    errors = []
    
    # DB 커넥션 획득 (WAL 모드 적용)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        for idx, row in df.iterrows():
            try:
                # 1. 지역 추출 및 표준화
                raw_region = row[mapping["region"]]
                standardized_name, region_code = standardize_region(raw_region)
                
                # 2. 상품명 및 수량 추출
                product_name = str(row[mapping["product"]]).strip()
                if not product_name or product_name.lower() == "nan":
                    raise ValueError(f"행 {idx+1}: 상품명이 비어있습니다.")
                    
                quantity_val = row[mapping["quantity"]]
                if pd.isna(quantity_val):
                    raise ValueError(f"행 {idx+1}: 수량이 누락되었습니다(NaN).")
                quantity = float(quantity_val)
                if quantity < 0:
                    raise ValueError(f"행 {idx+1}: 수량은 음수일 수 없습니다 ({quantity}).")
                
                # 3. 날짜 추출 및 보정
                if "date" in mapping:
                    raw_date = row[mapping["date"]]
                    if pd.isna(raw_date) or not str(raw_date).strip() or str(raw_date).lower() == "nan":
                        date_str = today_str
                    else:
                        # 날짜 파싱 시도 (다양한 포맷 대응)
                        if isinstance(raw_date, (datetime, pd.Timestamp)):
                            date_str = raw_date.strftime("%Y-%m-%d")
                        else:
                            try:
                                parsed_date = pd.to_datetime(str(raw_date).strip())
                                date_str = parsed_date.strftime("%Y-%m-%d")
                            except Exception:
                                date_str = today_str
                else:
                    date_str = today_str
                
                # 4. SQLite UPSERT 수행 (Conflict 시 수량 업데이트)
                cursor.execute("""
                    INSERT INTO region_inventory (region_code, product_name, date, quantity, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(region_code, product_name, date) DO UPDATE SET
                        quantity = excluded.quantity,
                        updated_at = CURRENT_TIMESTAMP
                """, (region_code, product_name, date_str, quantity))
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"행 {idx+1} 처리 실패 (값: {row.to_dict()}): {str(e)}")
                
        # 배치 원자성 확보를 위해 최종 커밋
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()
        
    # 에러 메시지는 최대 10개까지만 노출하고 나머지는 생략(Et Cetera)
    displayed_errors = errors
    if len(errors) > 10:
        displayed_errors = errors[:10] + [f"...외 {len(errors) - 10}개의 에러가 더 발생했습니다. (Et Cetera)"]
        
    return {
        "success_count": success_count,
        "error_count": error_count,
        "errors": displayed_errors
    }
