# utils/parser/header_detector.py
import pandas as pd
from typing import Tuple

COLUMN_ALIASES = {
    "region_code": ["지점", "지역", "지역명", "region", "regionname", "location", "branch", "region_code", "regioncode"],
    "product_name": ["상품명", "상품이름", "품목", "품목명", "product", "productname", "producttitle", "product_title", "item", "product_name"],
    "quantity": ["수량", "개수", "양", "quantity", "qty", "count", "amount"],
    "date": ["날짜", "일자", "기준일", "date", "datetime", "day"],
    "company_id": ["회사", "회사id", "company", "companyid", "company_id", "companyid"],
    "warehouse_code": ["창고", "창고코드", "warehouse", "warehousecode", "warehouse_code", "warehousecode"]
}

def clean_value(val) -> str:
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip().lower().replace(" ", "").replace("_", "").replace("-", "")

def detect_header_row(df: pd.DataFrame, max_scan_rows: int = 15) -> int:
    """
    Scans the first N rows of the DataFrame to find the true header row.
    Returns the integer index of the header row (0-based).
    If the original df.columns has a higher or equal match count, returns -1.
    """
    best_row_idx = 0
    max_matches = 0
    
    for i in range(min(len(df), max_scan_rows)):
        row_values = df.iloc[i].tolist()
        matches = 0
        matched_standards = set()
        
        for val in row_values:
            cleaned = clean_value(val)
            if not cleaned:
                continue
            for std_col, aliases in COLUMN_ALIASES.items():
                if cleaned in aliases and std_col not in matched_standards:
                    matches += 1
                    matched_standards.add(std_col)
                    break
        
        if matches > max_matches:
            max_matches = matches
            best_row_idx = i
            
    # Check original columns as well
    col_matches = 0
    matched_standards = set()
    for col in df.columns:
        cleaned = clean_value(col)
        for std_col, aliases in COLUMN_ALIASES.items():
            if cleaned in aliases and std_col not in matched_standards:
                col_matches += 1
                matched_standards.add(std_col)
                break
                
    if col_matches >= max_matches and col_matches > 0:
        return -1
        
    return best_row_idx

def extract_clean_df(df: pd.DataFrame, header_idx: int) -> pd.DataFrame:
    """
    Reconstructs DataFrame starting from the identified header row.
    If header_idx is -1, returns original df.
    """
    if header_idx == -1:
        return df.copy()
    
    # Extract header row values to use as new columns
    new_columns = df.iloc[header_idx].tolist()
    # Replace NaN or empty columns with index-based placeholders to prevent duplicate/empty issues
    clean_columns = []
    for i, col in enumerate(new_columns):
        if pd.isna(col) or str(col).strip() == "":
            clean_columns.append(f"UNNAMED_COL_{i}")
        else:
            clean_columns.append(str(col).strip())
            
    # Slice dataframe from after the header row
    sliced_df = df.iloc[header_idx + 1:].copy()
    sliced_df.columns = clean_columns
    sliced_df.reset_index(drop=True, inplace=True)
    return sliced_df
