# utils/parser/drift_engine.py
from utils.schema_registry import SCHEMA_REGISTRY
from utils.parser.exceptions import HeaderDriftError

def calculate_drift_score(mapped_cols: list[str]) -> float:
    """
    Calculates the schema drift score using the Set-based symmetric difference formula:
    DriftScore = |A_effective Delta B| / max(|A_effective|, |B|, 1)
    """
    a_effective = set(col for col in mapped_cols if col is not None)
    b = set(SCHEMA_REGISTRY.keys())
    
    sym_diff = a_effective.symmetric_difference(b)
    
    drift_score = len(sym_diff) / max(len(a_effective), len(b), 1)
    return round(drift_score, 8)

def validate_drift(mapped_cols: list[str], unknown_cols_count: int) -> float:
    """
    Validates if schema drift or unknown columns count violates the system safeguards:
    1. unknown_cols_count > 5 -> HeaderDriftError
    2. DriftScore > 0.5 -> HeaderDriftError
    """
    score = calculate_drift_score(mapped_cols)
    if unknown_cols_count > 5:
        raise HeaderDriftError(f"Header mapping failed: unknown columns count ({unknown_cols_count}) exceeds maximum limit of 5.")
    if score > 0.5:
        raise HeaderDriftError(f"Header mapping failed: Schema Drift Score ({score}) exceeds maximum limit of 0.5.")
    return score
