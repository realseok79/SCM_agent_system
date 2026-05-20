# utils/parser/semantic_mapper.py
import unicodedata
import re
import math
from functools import lru_cache
from utils.parser.header_detector import COLUMN_ALIASES

@lru_cache(maxsize=2048)
def canonicalize_header(raw_header: str) -> str:
    """
    Pure stateless string normalization:
    1. NFC normalization
    2. Lowercase, strip
    3. Keep only letters and numbers (remove spaces, underscores, hyphens, and noise)
    """
    if not isinstance(raw_header, str):
        raw_header = str(raw_header)
    norm = unicodedata.normalize('NFC', raw_header)
    cleaned = norm.strip().lower()
    cleaned = re.sub(r'[^a-zA-Z0-9가-힣]', '', cleaned)
    return cleaned

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate Levenshtein similarity between two strings"""
    s1_clean = canonicalize_header(s1)
    s2_clean = canonicalize_header(s2)
    max_len = max(len(s1_clean), len(s2_clean), 1)
    dist = levenshtein_distance(s1_clean, s2_clean)
    return 1.0 - (dist / max_len)

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def get_mapping_db_info(db_conn, company_id: str, raw_header: str, target_col: str) -> float:
    """
    Get the pre-computed negative_score from the database statically.
    If no record exists, defaults to 0.0.
    """
    if db_conn is None:
        return 0.0
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT negative_score FROM company_excel_mapping 
            WHERE company_id = ? AND raw_header = ? AND mapped_column = ?
            """,
            (company_id, raw_header, target_col)
        )
        row = cursor.fetchone()
        if row:
            return float(row[0])
    except Exception:
        pass
    return 0.0

def resolve_semantic_mapping(db_conn, company_id: str, raw_header: str, min_threshold: float = 0.40) -> tuple[str | None, float]:
    """
    Resolves the raw_header to a standard SCM column based on the 5-step collision resolution rule:
    1. Exact canonical match
    2. Highest alias confidence
    3. Lowest negative_score
    4. Lowest lexical distance
    5. Stable lexical ordering
    """
    raw_clean = canonicalize_header(raw_header)
    if not raw_clean:
        return None, 0.0
        
    candidates = []
    
    # Standard columns are keys of COLUMN_ALIASES
    for std_col, aliases in COLUMN_ALIASES.items():
        std_clean = canonicalize_header(std_col)
        
        # 1. Check exact canonical match
        is_exact = (raw_clean == std_clean)
        
        # Find maximum Levenshtein similarity among all aliases
        max_sim = 0.0
        is_alias_exact = False
        for alias in aliases:
            alias_clean = canonicalize_header(alias)
            if raw_clean == alias_clean:
                is_alias_exact = True
            sim = levenshtein_similarity(raw_header, alias)
            if sim > max_sim:
                max_sim = sim
                
        # Determine AliasWeight
        if is_exact:
            alias_weight = 1.0
            is_exact_match = True
        elif is_alias_exact:
            alias_weight = 0.85  # slightly higher for exact alias match
            is_exact_match = True
        else:
            alias_weight = 0.72
            is_exact_match = False
            
        # Get pre-computed negative_score from DB (Choice A)
        neg_score = get_mapping_db_info(db_conn, company_id, raw_header, std_col)
        
        # Calculate confidence
        rejection_penalty = 0.10
        penalty_factor = clamp(neg_score * rejection_penalty, 0.0, 0.8)
        confidence = alias_weight * max_sim * (1.0 - penalty_factor)
        
        # Build sort key (elements: ascending sort by default in python)
        # Element 1: Exact match status (0 for exact, 1 otherwise)
        # Element 2: -confidence (higher is better, so more negative)
        # Element 3: negative_score (lower is better)
        # Element 4: -max_sim (higher similarity is better, so more negative)
        # Element 5: ASCII target column name (stable tie-breaker)
        sort_key = (
            0 if is_exact_match else 1,
            -confidence,
            neg_score,
            -max_sim,
            std_col
        )
        
        candidates.append((std_col, confidence, max_sim, neg_score, sort_key))
        
    # Sort candidates using the sort_key
    candidates.sort(key=lambda x: x[4])
    
    best_col, best_conf, _, _, _ = candidates[0]
    
    if best_conf >= min_threshold:
        return best_col, round(best_conf, 8)
        
    return None, 0.0
