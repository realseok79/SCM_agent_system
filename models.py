# models.py
from pydantic import BaseModel, Field
from typing import Optional

# ── Pydantic Schemas for FastAPI Validation ──

class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: Optional[str] = None
    role: str = Field(..., description="e.g. ADMIN, MANAGER, USER")

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: str

class RegionBase(BaseModel):
    region_name: str
    description: Optional[str] = None

class RegionCreate(RegionBase):
    pass

class RegionResponse(BaseModel):
    id: int
    region_name: str
    region_code: str
    description: Optional[str] = None
    created_at: str

# ── [1단계] 지역 표준코드 변환 엔진 ──

# 지역명 매핑 사전 (소문자 공백 제거 상태로 비교)
REGION_MAP = {
    # 서울
    "서울": ("서울특별시", "KR-11"),
    "seoul": ("서울특별시", "KR-11"),
    "서울특별시": ("서울특별시", "KR-11"),
    "seoulsi": ("서울특별시", "KR-11"),
    "kr11": ("서울특별시", "KR-11"),
    # 부산
    "부산": ("부산광역시", "KR-26"),
    "busan": ("부산광역시", "KR-26"),
    "부산광역시": ("부산광역시", "KR-26"),
    "busansi": ("부산광역시", "KR-26"),
    "kr26": ("부산광역시", "KR-26"),
    # 대구
    "대구": ("대구광역시", "KR-27"),
    "daegu": ("대구광역시", "KR-27"),
    "대구광역시": ("대구광역시", "KR-27"),
    "daegusi": ("대구광역시", "KR-27"),
    "kr27": ("대구광역시", "KR-27"),
    # 인천
    "인천": ("인천광역시", "KR-28"),
    "incheon": ("인천광역시", "KR-28"),
    "인천광역시": ("인천광역시", "KR-28"),
    "incheonsi": ("인천광역시", "KR-28"),
    "kr28": ("인천광역시", "KR-28"),
    # 광주
    "광주": ("광주광역시", "KR-29"),
    "gwangju": ("광주광역시", "KR-29"),
    "광주광역시": ("광주광역시", "KR-29"),
    "gwangjusi": ("광주광역시", "KR-29"),
    "kr29": ("광주광역시", "KR-29"),
    # 대전
    "대전": ("대전광역시", "KR-30"),
    "daejeon": ("대전광역시", "KR-30"),
    "대전광역시": ("대전광역시", "KR-30"),
    "daejeonsi": ("대전광역시", "KR-30"),
    "kr30": ("대전광역시", "KR-30"),
    # 울산
    "울산": ("울산광역시", "KR-31"),
    "ulsan": ("울산광역시", "KR-31"),
    "울산광역시": ("울산광역시", "KR-31"),
    "ulsansi": ("울산광역시", "KR-31"),
    "kr31": ("울산광역시", "KR-31"),
    # 세종
    "세종": ("세종특별자치시", "KR-36"),
    "sejong": ("세종특별자치시", "KR-36"),
    "세종특별자치시": ("세종특별자치시", "KR-36"),
    "sejongsi": ("세종특별자치시", "KR-36"),
    "kr36": ("세종특별자치시", "KR-36"),
    # 경기
    "경기": ("경기도", "KR-41"),
    "gyeonggi": ("경기도", "KR-41"),
    "경기도": ("경기도", "KR-41"),
    "gyeonggido": ("경기도", "KR-41"),
    "kr41": ("경기도", "KR-41"),
    # 강원
    "강원": ("강원특별자치도", "KR-42"),
    "gangwon": ("강원특별자치도", "KR-42"),
    "강원도": ("강원특별자치도", "KR-42"),
    "강원특별자치도": ("강원특별자치도", "KR-42"),
    "gangwondo": ("강원특별자치도", "KR-42"),
    "kr42": ("강원특별자치도", "KR-42"),
    # 충북
    "충북": ("충청북도", "KR-43"),
    "chungbuk": ("충청북도", "KR-43"),
    "충청북도": ("충청북도", "KR-43"),
    "chungcheong북도": ("충청북도", "KR-43"),
    "chungcheongbukdo": ("충청북도", "KR-43"),
    "kr43": ("충청북도", "KR-43"),
    # 충남
    "충남": ("충청남도", "KR-44"),
    "chungnam": ("충청남도", "KR-44"),
    "충청남도": ("충청남도", "KR-44"),
    "chungcheong남도": ("충청남도", "KR-44"),
    "chungcheongnamdo": ("충청남도", "KR-44"),
    "kr44": ("충청남도", "KR-44"),
    # 전북
    "전북": ("전북특별자치도", "KR-45"),
    "jeonbuk": ("전북특별자치도", "KR-45"),
    "전라북도": ("전북특별자치도", "KR-45"),
    "전북특별자치도": ("전북특별자치도", "KR-45"),
    "jeollabukdo": ("전북특별자치도", "KR-45"),
    "kr45": ("전북특별자치도", "KR-45"),
    # 전남
    "전남": ("전라남도", "KR-46"),
    "jeonnam": ("전라남도", "KR-46"),
    "전라남도": ("전라남도", "KR-46"),
    "jeollanamdo": ("전라남도", "KR-46"),
    "kr46": ("전라남도", "KR-46"),
    # 경북
    "경북": ("경상북도", "KR-47"),
    "gyeongbuk": ("경상북도", "KR-47"),
    "경상북도": ("경상북도", "KR-47"),
    "gyeongsangbukdo": ("경상북도", "KR-47"),
    "kr47": ("경상북도", "KR-47"),
    # 경남
    "경남": ("경상남도", "KR-48"),
    "gyeongnam": ("경상남도", "KR-48"),
    "경상남도": ("경상남도", "KR-48"),
    "gyeongsangnamdo": ("경상남도", "KR-48"),
    "kr48": ("경상남도", "KR-48"),
    # 제주
    "제주": ("제주특별자치도", "KR-49"),
    "jeju": ("제주특별자치도", "KR-49"),
    "제주특별자치도": ("제주특별자치도", "KR-49"),
    "jejudo": ("제주특별자치도", "KR-49"),
    "kr49": ("제주특별자치도", "KR-49")
}

def standardize_region(region_input: str) -> tuple[str, str]:
    """
    입력된 임의의 지역명 문자열을 표준 지역명과 ISO 표준코드로 매핑하여 변환합니다.
    매핑 불가 시 ValueError를 발생시킵니다.
    """
    if not region_input:
        raise ValueError("지역 이름이 비어있습니다.")
        
    cleaned = str(region_input).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    
    if cleaned in REGION_MAP:
        return REGION_MAP[cleaned]
    
    # 부분 매칭 시도
    for key, val in REGION_MAP.items():
        if key in cleaned or cleaned in key:
            return val
            
    raise ValueError(f"지원하지 않는 지역명입니다: '{region_input}'")
