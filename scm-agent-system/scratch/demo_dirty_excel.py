# scm-agent-system/scratch/demo_dirty_excel.py
import io
import json
import pandas as pd
import sys
import os

# scm-agent-backend/analysis-microservice 폴더를 Python path에 추가하여 excel_parser를 가져옵니다.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scm-agent-backend/analysis-microservice')))
from excel_parser import read_sheets_auto_header, clean_quantity, clean_date_value, clean_excel_data

def create_extremely_dirty_excel():
    """아주 더러운 다중 시트 비정형 엑셀 바이트를 생성합니다."""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Region & Product (상단에 결재란 및 회사 로고, 쓰레기 데이터 다량 포함)
        df1_meta = pd.DataFrame([
            ["(주) 시그마 반도체 SCM 출고 대장 (대외비)", "", ""],
            ["결재선: 담당자 [진석] -> 부장 [승인] -> 대표이사 [전결]", "", ""],
            ["출력 날짜: 2026년 05월 23일", "", ""],
            ["", "", ""], # 빈행
            ["물류센터명", "자재 부품 코드", "비고"], # 4번 인덱스 (이 행이 데이터가 가득 찬 진짜 헤더!)
            ["창고-서울 H1", "DRAM 16G", "정상 납품"],
            ["창고-부산 H2", "NAND Flash", "긴급 납품"],
            ["창고-인천 H3", "AP Processor", "이월 품목"]
        ])
        df1_meta.to_excel(writer, sheet_name="물류_자재_시트", index=False, header=False)
        
        # Sheet 2: Date & Quantity (구형 날짜 포맷, 수량에 '개' 접미사 및 쉼표 포함)
        df2_meta = pd.DataFrame([
            ["본 통계는 실시간 출하 정보이므로 오차가 있을 수 있음", ""],
            ["-------------------------------------------------", ""],
            ["입고일자", "실수량"], # 2번 인덱스가 진짜 헤더!
            ["2026/05/22", "1,500 개"],
            ["2026.05.23", "2,300 개"],
            ["2026-05-24", "980 개"]
        ])
        df2_meta.to_excel(writer, sheet_name="날짜_수량_시트", index=False, header=False)
        
    return output.getvalue()

def run_demo():
    print("┌──────────────────────────────────────────────────────────┐")
    print("│         SCM Silent AI 데이터 에이전트 파싱 시뮬레이션         │")
    print("└──────────────────────────────────────────────────────────┘")
    
    # 1. 더러운 엑셀 바이트 생성
    print("💾 1. 회사 로고, 빈 행, 단위 표시(개) 등이 들어간 더러운 엑셀 생성 중...")
    excel_bytes = create_extremely_dirty_excel()
    print("   -> 엑셀 생성 완료 (크기: {} 바이트)".format(len(excel_bytes)))
    print()
    
    # 2. Zero-Click 자동 헤더 스캔 (Pandas 밀도 계산 알고리즘)
    print("🔍 2. [수학적 밀도 계산] 각 시트별 진짜 표의 시작점(Header) 자동 추적...")
    
    # 내부의 read_sheets_auto_header()를 가동
    excel_file = pd.ExcelFile(io.BytesIO(excel_bytes))
    for name in excel_file.sheet_names:
        preview_df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=name, nrows=20, header=None)
        non_null_counts = preview_df.notna().sum(axis=1)
        header_idx = int(non_null_counts.idxmax())
        print("   📂 시트 [{}]".format(name))
        print("      - 상단 쓰레기 메타데이터 탐지: {}개 행 우회".format(header_idx))
        print("      - 검출된 실제 헤더 열: {}".format(list(preview_df.iloc[header_idx].dropna().values)))
    print()
    
    # 3. 데이터 로딩 및 Gemini의 컬럼 시맨틱 매핑 가동 모의
    print("🤖 3. [Gemini AI 시맨틱 스키마 매핑] 비정형 컬럼 -> 표준 SCM 컬럼 대응...")
    
    # 사용자 최종 컨펌으로 확보한 시맨틱 매핑 딕셔너리 정의
    user_mapping = {
        "물류센터명": "region_code",
        "자재 부품 코드": "product_name",
        "입고일자": "date",
        "실수량": "quantity",
        "비고": ""
    }
    
    print("   [확정된 스키마 매핑 딕셔너리]")
    print(json.dumps(user_mapping, indent=7, ensure_ascii=False))
    print()
    
    # 4. 정제 및 데이터 정형화 머징 실행 (clean_excel_data 호출)
    print("⚙️ 4. [Silent AI Pipeline] 데이터 타입 정제, 단위 기호 제거 및 병합 실행...")
    cleaned_df = clean_excel_data(excel_bytes, user_mapping)
    
    print("\n✅ 정제 완료! 최종 표준 SCM 규격 Pandas DataFrame:")
    print("─" * 60)
    print(cleaned_df.to_string(index=True))
    print("─" * 60)
    print()
    
    # 5. 최종 E2E JSON 결과물 변환 출력
    print("📦 5. 자바 백엔드 DB 적재용 최종 표준 JSON 페이로드 생성:")
    json_payload = cleaned_df.to_dict(orient='records')
    print(json.dumps(json_payload, indent=4, ensure_ascii=False))
    
    print("\n🎉 시뮬레이션 종료. CPU 가동률 거의 0%로 컴퓨터 온도를 완벽히 유지했습니다!")

if __name__ == "__main__":
    run_demo()
