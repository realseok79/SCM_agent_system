# scm-agent-system/scratch/test_excel_ingestion_pipeline.py
import io
import json
import requests
import pandas as pd

def create_sample_excel():
    """Create a sample multi-sheet unstructured Excel workbook with some metadata rows at the top."""
    # Write Excel with openpyxl to memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Region & Product (with some metadata clutter at the top)
        df1_meta = pd.DataFrame([
            ["SIGMA SCM INGESTION SHEET", ""],
            ["Report generated on: 2026-05-22", ""],
            ["", ""],
            ["물류창고", "품목명"],
            ["창고-서울", "DRAM 16G"],
            ["창고-부산", "NAND Flash"]
        ])
        df1_meta.to_excel(writer, sheet_name="물류_품목 정보", index=False, header=False)
        
        # Sheet 2: Date & Quantity (with some metadata clutter at the top)
        df2_meta = pd.DataFrame([
            ["CONFIDENTIAL - INTERNAL ONLY", ""],
            ["", ""],
            ["일자", "재고수량"],
            ["2026-05-22", "1,500 개"],
            ["2026-05-23", "2,300 개"]
        ])
        df2_meta.to_excel(writer, sheet_name="일자_수량 정보", index=False, header=False)
        
    return output.getvalue()

def run_pipeline_test():
    print("🚀 Starting SCM LLM-Powered Excel Parsing Pipeline End-to-End Test...")
    
    # 1. Generate multi-sheet sample Excel file bytes
    excel_bytes = create_sample_excel()
    print("✅ Created sample multi-sheet Excel file bytes (with metadata clutter).")
    
    # 2. Call Phase 1: /analyze/excel/llm
    print("⚡ Calling FastAPI /analyze/excel/llm endpoint...")
    files = {"file": ("test_unstructured.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    
    try:
        res = requests.post("http://localhost:8090/analyze/excel/llm", files=files, timeout=30)
    except Exception as e:
        print(f"❌ Failed to connect to FastAPI microservice: {e}")
        return False
        
    if res.status_code != 200:
        print(f"❌ Phase 1 Analysis failed with status {res.status_code}: {res.text}")
        return False
        
    analysis_res = res.json()
    print("✅ Phase 1 Analysis Response received successfully!")
    print(f"   Drift Score: {analysis_res.get('driftScore')}")
    print(f"   Quality Score: {analysis_res.get('qualityScore')}")
    print("   AI Mapped Columns:")
    print(json.dumps(analysis_res.get("mapping"), indent=4, ensure_ascii=False))
    print("   AI Explanation:")
    print(f"   {analysis_res.get('explanation')}")
    
    # Verify the mappings
    mapping = analysis_res.get("mapping", {})
    assert "물류창고" in mapping, "물류창고 should be in the mapped columns"
    assert "품목명" in mapping, "품목명 should be in the mapped columns"
    assert "일자" in mapping, "일자 should be in the mapped columns"
    assert "재고수량" in mapping, "재고수량 should be in the mapped columns"
    
    print("✅ Gemini successfully mapped all Korean terms to standard SCM schemas!")
    
    # 3. Call Phase 2: /clean/excel using the AI mapping
    print("⚡ Calling FastAPI /clean/excel endpoint to merge and clean sheets...")
    clean_files = {"file": ("test_unstructured.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    clean_data = {"user_mapping": json.dumps(mapping)}
    
    res_clean = requests.post("http://localhost:8090/clean/excel", files=clean_files, data=clean_data, timeout=20)
    
    if res_clean.status_code != 200:
        print(f"❌ Phase 2 Cleaning failed with status {res_clean.status_code}: {res_clean.text}")
        return False
        
    clean_res = res_clean.json()
    print("✅ Phase 2 Cleaning Response received successfully!")
    
    cleaned_csv = clean_res.get("cleaned_csv", "")
    print("🔍 Cleaned, Unified, Standard-conforming CSV Output:")
    print("-" * 50)
    print(cleaned_csv)
    print("-" * 50)
    
    # Read CSV to DataFrame and perform assertions
    df = pd.read_csv(io.StringIO(cleaned_csv))
    print(f"   Processed {len(df)} rows.")
    
    assert list(df.columns) == ["region_code", "product_name", "date", "quantity"], "CSV columns must be standard"
    assert df.loc[0, "region_code"] == "창고-서울", "서울 region code should be parsed"
    assert df.loc[0, "product_name"] == "DRAM 16G", "DRAM product name should be parsed"
    assert df.loc[0, "date"] == "2026-05-22", "Date should be formatted as YYYY-MM-DD"
    assert df.loc[0, "quantity"] == 1500.0, "Quantity should be clean float (1500.0)"
    
    assert df.loc[1, "region_code"] == "창고-부산", "부산 region code should be parsed"
    assert df.loc[1, "product_name"] == "NAND Flash", "NAND product name should be parsed"
    assert df.loc[1, "date"] == "2026-05-23", "Date should be formatted as YYYY-MM-DD"
    assert df.loc[1, "quantity"] == 2300.0, "Quantity should be clean float (2300.0)"
    
    print("🎉 All assertions passed perfectly! The AI-Powered Excel Ingestion Pipeline is 100% Correct!")
    return True

if __name__ == "__main__":
    run_pipeline_test()
