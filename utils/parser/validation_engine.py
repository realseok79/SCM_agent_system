# utils/parser/validation_engine.py
import json
import pandas as pd
from datetime import datetime
from models import standardize_region
from utils.parser.exceptions import ValidationPayloadTooLargeError

def parse_date(val) -> datetime:
    """Parse date from cell value into datetime object"""
    if isinstance(val, (datetime, pd.Timestamp)):
        # Normalize timestamp to naive datetime
        if hasattr(val, 'to_pydatetime'):
            return val.to_pydatetime().replace(tzinfo=None)
        return val.replace(tzinfo=None)
        
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(val_str).to_pydatetime().replace(tzinfo=None)
    except Exception:
        raise ValueError(f"Invalid date format: {val_str}")

def validate_rows(
    df: pd.DataFrame,
    mapping: dict,  # raw_header -> SCM_standard_column
    company_id: str
) -> tuple[list[dict], bool, bool, bool]:
    """
    Validates all rows in the clean DataFrame based on column mappings.
    Returns:
        - payload_list: list of row dicts containing standard fields, raw values, row index, and validation errors.
        - has_critical: bool indicating if any CRITICAL severity error was found.
        - has_error: bool indicating if any ERROR severity error was found.
        - has_warning: bool indicating if any WARNING was found.
    """
    MAX_VALIDATION_PAYLOAD_BYTES = 2097152  # 2MB
    
    # Invert mapping to find standard SCM columns -> original raw headers
    inv_mapping = {}
    for raw_h, std_c in mapping.items():
        if std_c:
            inv_mapping[std_c] = raw_h
            
    required_cols = ["region_code", "product_name", "date", "quantity"]
    payload_list = []
    
    has_critical = False
    has_error = False
    has_warning = False
    
    now_naive = datetime.utcnow()
    
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_errors = []
        
        standardized_values = {
            "region_code": None,
            "product_name": None,
            "date": None,
            "quantity": None,
            "company_id": company_id,
            "warehouse_code": None
        }
        
        # Check required SCM standard columns existence in mapping
        for req in required_cols:
            if req not in inv_mapping:
                row_errors.append({
                    "severity": "CRITICAL",
                    "message": f"Required column '{req}' is missing in header mapping.",
                    "column": req
                })
                has_critical = True
                
        if not has_critical:
            # 1. region_code
            raw_h = inv_mapping.get("region_code")
            raw_val = row_dict.get(raw_h)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                row_errors.append({
                    "severity": "CRITICAL",
                    "message": "Required column 'region_code' is null or empty.",
                    "column": "region_code"
                })
                has_critical = True
            else:
                try:
                    _, std_region_code = standardize_region(str(raw_val).strip())
                    standardized_values["region_code"] = std_region_code
                except ValueError as e:
                    row_errors.append({
                        "severity": "CRITICAL",
                        "message": str(e),
                        "column": "region_code"
                    })
                    has_critical = True
                    
            # 2. product_name
            raw_h = inv_mapping.get("product_name")
            raw_val = row_dict.get(raw_h)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                row_errors.append({
                    "severity": "CRITICAL",
                    "message": "Required column 'product_name' is null or empty.",
                    "column": "product_name"
                })
                has_critical = True
            else:
                prod_str = str(raw_val).strip()
                if prod_str.lower() == "nan" or not prod_str:
                    row_errors.append({
                        "severity": "CRITICAL",
                        "message": "Product name is empty or invalid.",
                        "column": "product_name"
                    })
                    has_critical = True
                else:
                    standardized_values["product_name"] = prod_str
                    
            # 3. date
            raw_h = inv_mapping.get("date")
            raw_val = row_dict.get(raw_h)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                row_errors.append({
                    "severity": "CRITICAL",
                    "message": "Required column 'date' is null or empty.",
                    "column": "date"
                })
                has_critical = True
            else:
                try:
                    date_obj = parse_date(raw_val)
                    diff_years = (date_obj - now_naive).days / 365.25
                    
                    if diff_years > 1.0:
                        row_errors.append({
                            "severity": "ERROR",
                            "message": "Date is more than 1 year in the future.",
                            "column": "date"
                        })
                        has_error = True
                    elif diff_years < -5.0:
                        row_errors.append({
                            "severity": "WARNING",
                            "message": "Date is older than 5 years.",
                            "column": "date"
                        })
                        has_warning = True
                        
                    standardized_values["date"] = date_obj.strftime("%Y-%m-%d")
                except Exception as e:
                    row_errors.append({
                        "severity": "CRITICAL",
                        "message": f"Failed to parse date: {e}",
                        "column": "date"
                    })
                    has_critical = True
                    
            # 4. quantity
            raw_h = inv_mapping.get("quantity")
            raw_val = row_dict.get(raw_h)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                row_errors.append({
                    "severity": "CRITICAL",
                    "message": "Required column 'quantity' is null or empty.",
                    "column": "quantity"
                })
                has_critical = True
            else:
                try:
                    qty = float(raw_val)
                    # Check fractional quantity warning
                    if abs(qty - round(qty)) > 1e-9:
                        row_errors.append({
                            "severity": "WARNING",
                            "message": f"Fractional quantity {qty} rounded to nearest integer {round(qty)}.",
                            "column": "quantity"
                        })
                        has_warning = True
                        qty = float(round(qty))
                        
                    if qty < 0:
                        row_errors.append({
                            "severity": "ERROR",
                            "message": "Quantity cannot be negative.",
                            "column": "quantity"
                        })
                        has_error = True
                    elif qty >= 1000000:
                        row_errors.append({
                            "severity": "ERROR",
                            "message": "Quantity exceeds limit of 1,000,000.",
                            "column": "quantity"
                        })
                        has_error = True
                        
                    standardized_values["quantity"] = qty
                except ValueError:
                    row_errors.append({
                        "severity": "CRITICAL",
                        "message": f"Failed to cast quantity '{raw_val}' to float.",
                        "column": "quantity"
                    })
                    has_critical = True
                    
            # 5. warehouse_code (Optional)
            if "warehouse_code" in inv_mapping:
                raw_h = inv_mapping.get("warehouse_code")
                raw_val = row_dict.get(raw_h)
                if not pd.isna(raw_val):
                    standardized_values["warehouse_code"] = str(raw_val).strip()
                    
        # Update overall flags
        for err in row_errors:
            if err["severity"] == "CRITICAL":
                has_critical = True
            elif err["severity"] == "ERROR":
                has_error = True
            elif err["severity"] == "WARNING":
                has_warning = True
                
        # Construct the payload dictionary for this row
        payload_row = {
            "source_row_index": idx,
            "standardized_values": standardized_values,
            "raw_row_data": row_dict,
            "validation_errors": row_errors
        }
        payload_list.append(payload_row)
        
    # Enforce 2MB size hard limit
    payload_size = len(json.dumps(payload_list, ensure_ascii=False).encode('utf-8'))
    if payload_size > MAX_VALIDATION_PAYLOAD_BYTES:
        raise ValidationPayloadTooLargeError(
            f"Validation payload size ({payload_size} bytes) exceeds maximum limit of 2MB."
        )
        
    return payload_list, has_critical, has_error, has_warning
