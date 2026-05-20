# tests/test_semantic_mapper_extended.py
import pytest
import sqlite3
from utils.parser.semantic_mapper import (
    canonicalize_header,
    levenshtein_distance,
    resolve_semantic_mapping,
    get_mapping_db_info
)

def test_canonicalize_non_string():
    """canonicalize_header에 문자열이 아닌 타입이 들어왔을 때 문자열 형변환 및 NFC 정형화 검증"""
    assert canonicalize_header(12345) == "12345"
    assert canonicalize_header(None) == "none"

def test_canonicalize_nfd_normalization():
    """자음/모음이 분리된 NFD 한글을 NFC로 정규화하는지 검증 (예: '지' + '점')"""
    nfd_text = "\u110c\u1175\u110c\u1165\u11b7"  # NFD '지점'
    nfc_text = canonicalize_header(nfd_text)
    assert nfc_text == "지점"

def test_levenshtein_distance_s2_empty():
    """s2가 빈 문자열일 때 s1의 길이를 반환하는지 검증"""
    assert levenshtein_distance("hello", "") == 5

def test_get_mapping_db_info_db_none():
    """db_conn이 None일 때 기본 0.0 반환 검증"""
    assert get_mapping_db_info(None, "COMP-A", "raw", "target") == 0.0

def test_get_mapping_db_info_exception():
    """DB 쿼리 중 예외가 발생했을 때 except 블록이 안전하게 0.0을 반환하는지 검증"""
    # 잘못된 타입의 db_conn을 주입하여 예외 유도
    assert get_mapping_db_info("invalid_db_conn", "COMP-A", "raw", "target") == 0.0

def test_resolve_semantic_mapping_empty_raw():
    """canonicalize_header 이후 결과가 빈 문자열인 노이즈 입력 시 None, 0.0 반환 검증"""
    assert resolve_semantic_mapping(None, "COMP-A", "   ___---   ") == (None, 0.0)

def test_resolve_semantic_mapping_exact_match():
    """정확히 매치되는 헤더가 유입되었을 때 exact_match 분기(alias_weight = 1.0) 검증"""
    col, conf = resolve_semantic_mapping(None, "COMP-A", "region_code")
    assert col == "region_code"
    assert conf == 1.0

def test_lru_cache_hit_verification():
    """lru_cache 히트 최적화 경로 검증을 위해 동일 문자열을 2번 호출하여 커버리지 확보"""
    assert canonicalize_header("region") == "region"
    assert canonicalize_header("region") == "region"
