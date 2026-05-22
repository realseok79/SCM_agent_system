# analysis-microservice/excel_parser.py
import io
import re
import os
import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExcelParser")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDHJY3QI7y9p3FGhOdgs-Dn__lHu-308hw")

# Define Pydantic schema for structured Gemini output
class ColumnMapping(BaseModel):
    region_code: Optional[str] = Field(None, description="The raw column name from the Excel sheet that represents region_code (e.g. 지점명, 물류창고, 창고, 지역, 센터)")
    product_name: Optional[str] = Field(None, description="The raw column name from the Excel sheet that represents product_name (e.g. 상품명, 품목명, 제품명, 물품, 자재)")
    date: Optional[str] = Field(None, description="The raw column name from the Excel sheet that represents date (e.g. 날짜, 일자, 기준일, 입고일, 출고일)")
    quantity: Optional[str] = Field(None, description="The raw column name from the Excel sheet that represents quantity (e.g. 수량, 재고량, 입고수량, 현재고, 개수)")

class SheetMapping(BaseModel):
    sheet_name: str = Field(..., description="The name of the sheet in the Excel file")
    mapping: ColumnMapping = Field(..., description="The mapped columns for this specific sheet")

class MappingResponse(BaseModel):
    sheet_mappings: List[SheetMapping] = Field(..., description="Mappings for each sheet in the Excel file")
    explanation: str = Field(..., description="A short explanation of how the columns were mapped")

def clean_quantity(val) -> float:
    """Clean quantity string (e.g., '1,500개', '$300') and convert to float."""
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str:
        return 0.0
    
    # Remove everything except numbers, decimal points, and minus signs
    cleaned = re.sub(r'[^\d\.\-]', '', val_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def clean_date_value(val) -> str:
    """Robust conversion of Excel dates (serial numbers, timestamps, various formats) to YYYY-MM-DD."""
    if pd.isna(val) or val is None:
        return ""
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    
    val_str = str(val).strip()
    if not val_str:
        return ""
    
    # Check if numeric Excel serial date (e.g., 46162.0)
    try:
        if '.' in val_str:
            num = float(val_str)
        else:
            num = int(val_str)
        if 30000 < num < 60000:
            return pd.to_datetime(num, unit='D', origin='1899-12-30').strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    # Common format parsing
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%m/%d/%Y', '%Y.%m.%d', '%Y년 %m월 %d일'):
        try:
            return pd.to_datetime(val_str, format=fmt).strftime('%Y-%m-%d')
        except Exception:
            continue
            
    # Generic pandas parser fallback
    try:
        parsed = pd.to_datetime(val_str, errors='coerce')
        if not pd.isna(parsed):
            return parsed.strftime('%Y-%m-%d')
    except Exception:
        pass
        
    return val_str

def read_sheets_auto_header(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    """Helper to read all sheets and automatically find the densest row as the header."""
    excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
    sheet_names = excel_file.sheet_names
    sheets_data = {}
    
    for sheet_name in sheet_names:
        try:
            # Read first 50 rows to detect header safely
            preview_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, nrows=50, header=None)
            if preview_df.empty:
                continue
                
            # Density check: count non-nulls in each row
            non_null_counts = preview_df.notna().sum(axis=1)
            if non_null_counts.empty:
                continue
            header_idx = int(non_null_counts.idxmax())
            
            # Read full sheet from header row onwards
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, skiprows=header_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            # Drop completely empty columns
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            if not df.empty:
                sheets_data[sheet_name] = df
        except Exception as e:
            logger.error(f"Error auto-detecting header on sheet '{sheet_name}': {e}")
            continue
            
    return sheets_data

def analyze_excel_file(file_bytes: bytes) -> dict:
    """Phase 1: Detect sheets/headers, call Gemini to get semantic mappings, and return preview metadata."""
    logger.info("Starting Phase 1 Excel analysis...")
    sheets_data = read_sheets_auto_header(file_bytes)
    
    if not sheets_data:
        raise ValueError("Could not extract any valid tabular data from the Excel sheets.")
        
    gemini_metadata = []
    all_raw_columns = []
    
    for sheet_name, df in sheets_data.items():
        all_raw_columns.extend(df.columns)
        samples = df.head(3).to_dict(orient='records')
        gemini_metadata.append({
            "sheet_name": sheet_name,
            "columns": list(df.columns),
            "sample_rows": samples
        })
        
    logger.info("Calling Gemini 3.1 Flash-Lite for schema mapping...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
You are an expert SCM Data Integration Engineer.
We need to map columns from these uploaded Excel sheets to our standard 4-column SCM schema:
1. `region_code` (e.g., 물류창고, 지점명, 지점, 창고, 지역, 센터, Region Code)
2. `product_name` (e.g., 물품명, 상품명, 제품명, 품명, 자재, Product Name)
3. `date` (e.g., 날짜, 일자, 기준일, 입고일, 출고일, Date)
4. `quantity` (e.g., 수량, 입고수량, 출고수량, 현재고, 개수, Quantity)

Here are the sheets, their column names, and a few sample rows of data in JSON format:
{json.dumps(gemini_metadata, indent=2, ensure_ascii=False)}

Task:
Identify which sheet(s) contain our target columns.
For each sheet, map its raw columns to standard fields.
Only map a column if you are confident it holds that SCM field. Leave fields as null if they are not present on a sheet.
Return the result structured as a JSON object adhering to the schema.
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash", # As per guidelines, gemini-2.0-flash is stable and supported
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MappingResponse,
                temperature=0.1
            )
        )
        
        mapping_res = MappingResponse.model_validate_json(response.text)
        logger.info(f"Gemini Mapping Result: {mapping_res.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}. Falling back to default heuristics.")
        # Fallback manual heuristics
        mapping_res = MappingResponse(
            sheet_mappings=[
                SheetMapping(
                    sheet_name=name,
                    mapping=ColumnMapping(
                        region_code=next((c for c in df.columns if any(kw in c.lower() for kw in ['창고', '지역', '지점', '센터', 'region'])), None),
                        product_name=next((c for c in df.columns if any(kw in c.lower() for kw in ['상품', '제품', '품목', '물품', '자재', 'product'])), None),
                        date=next((c for c in df.columns if any(kw in c.lower() for kw in ['날짜', '일자', '일', 'date'])), None),
                        quantity=next((c for c in df.columns if any(kw in c.lower() for kw in ['수량', '개수', '재고', 'qty', 'quantity'])), None)
                    )
                ) for name, df in sheets_data.items()
            ],
            explanation="Fallback manual mapping due to LLM error."
        )

    # Flatten the mappings for UI presentation
    flat_mapping = {c: "" for c in all_raw_columns}
    for sm in mapping_res.sheet_mappings:
        for std, raw in sm.mapping.model_dump().items():
            if raw and raw in flat_mapping:
                flat_mapping[raw] = std
                
    # Create simple preview using Gemini mappings
    preview_df = clean_excel_data(file_bytes, flat_mapping)
    preview_rows = preview_df.head(15).values.tolist()
    
    # Calculate Quality & Drift Score
    mapped_std_cols = set(flat_mapping.values()) - {"", None}
    drift_score = float(1.0 - (len(mapped_std_cols) / 4.0))
    quality_score = 1.0 if not preview_df.empty else 0.0
    
    return {
        "status": "SUCCESS",
        "driftScore": drift_score,
        "qualityScore": quality_score,
        "mapping": flat_mapping,
        "columns": ["region_code", "product_name", "date", "quantity"],
        "previewRows": preview_rows,
        "explanation": mapping_res.explanation
    }

def clean_excel_data(file_bytes: bytes, user_mapping: Dict[str, str]) -> pd.DataFrame:
    """Helper to merge and clean the data based on raw-to-standard mapping dictionary."""
    sheets_data = read_sheets_auto_header(file_bytes)
    
    # Group standard mappings by sheet name
    df_list = []
    
    for sheet_name, df in sheets_data.items():
        rename_dict = {}
        cols_to_keep = []
        
        for raw_col, std_col in user_mapping.items():
            if std_col and std_col in ["region_code", "product_name", "date", "quantity"]:
                if raw_col in df.columns:
                    rename_dict[raw_col] = std_col
                    cols_to_keep.append(raw_col)
                    
        if not cols_to_keep:
            continue
            
        extracted_df = df[cols_to_keep].rename(columns=rename_dict)
        extracted_df = extracted_df.dropna(how='all')
        df_list.append(extracted_df)
        
    if not df_list:
        return pd.DataFrame(columns=["region_code", "product_name", "date", "quantity"])
        
    # Merge all extracted DataFrames
    final_df = df_list[0]
    for sec_df in df_list[1:]:
        common_cols = list(set(final_df.columns) & set(sec_df.columns))
        if common_cols:
            final_df = pd.merge(final_df, sec_df, on=common_cols, how='outer')
        else:
            final_df = pd.concat([final_df, sec_df], axis=1)
            
    # Add missing columns as empty
    for col in ['region_code', 'product_name', 'date', 'quantity']:
        if col not in final_df.columns:
            final_df[col] = ""
            
    # Standardize types & clean values
    final_df['region_code'] = final_df['region_code'].fillna("").astype(str).str.strip()
    final_df['product_name'] = final_df['product_name'].fillna("").astype(str).str.strip()
    final_df['quantity'] = final_df['quantity'].apply(clean_quantity)
    final_df['date'] = final_df['date'].apply(clean_date_value)
    
    # Filter out empty records
    final_df = final_df[(final_df['region_code'] != "") & (final_df['product_name'] != "")]
    
    return final_df.reset_index(drop=True)

def generate_cleaned_csv(file_bytes: bytes, user_mapping: Dict[str, str]) -> str:
    """Phase 2: Perform the final data merge and cleaning, returning standard CSV content."""
    logger.info("Executing Phase 2 Excel-to-CSV cleaning...")
    cleaned_df = clean_excel_data(file_bytes, user_mapping)
    
    csv_buffer = io.StringIO()
    cleaned_df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()
