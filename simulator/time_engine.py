"""
simulator/time_engine.py
------------------------
100일간의 SCM 데이터 변동을 5분(300초) 이내로 압축 구동하는 타임 시뮬레이터.
각 틱(tick)마다 에이전트 파이프라인을 호출하고, 결과를 로그로 기록합니다.
수학적 연산 오버헤드로 인한 실제 소요 시간을 dynamic sleep으로 보정하여 정밀한 시간 압축을 보장합니다.
"""

import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv()
logger = get_logger("TimeSimulator")


class TimeSimulator:
    """
    SCM 시뮬레이션 타임 엔진 (계획서 요구사항 최적화 버전)
    """

    def __init__(self, total_days: int = None, real_seconds: float = None):
        # 비기능적 요구사항: 100일 분량을 5분(300초) 이내로 처리 완료 조건 반영
        self.total_days = total_days or int(os.getenv("SIMULATION_DAYS", 100))
        self.real_seconds = real_seconds or float(os.getenv("SIMULATION_SPEED_SECONDS", 300))
        self.tick_interval = self.real_seconds / self.total_days  # 1일당 배정된 물리 시간(초)

        self.current_day = 0
        self.is_running = False

        # 계획서 상의 가상 세계 타임라인 기준점
        self.start_date = datetime(2026, 1, 1)

        # ── [구조 변경] 스트레스 테스트 위기 지속 기간(Duration) 도입 ──────────────────
        # 1틱만 유지되면 SCM 리스크 방어력 검증이 불가능하므로 지속성 부여
        self.stress_events = [
            {
                "start_day": 30,
                "end_day": 35,
                "demand_multiplier": 5.0,
                "lead_time_multiplier": 1.0,
                "description": "수요 5배 폭증 이벤트 (주말 스파이크 및 트렌드 급등)"
            },
            {
                "start_day": 60,
                "end_day": 81,  # 3주(21일)간 공급망 마비 지연 상황 완벽 재현
                "lead_time_multiplier": 3.0,
                "demand_multiplier": 1.0,
                "description": "조달기간 3주(21일) 지연 이벤트 (글로벌 공급망 위기)"
            },
            {
                "start_day": 85,
                "end_day": 90,
                "demand_multiplier": 3.0,
                "lead_time_multiplier": 2.5,
                "description": "⚠️ 최악의 복합 시나리오: 수요 폭증 + 조달 지연 동시 발생"
            }
        ]

        self._print_init_info()

    def _print_init_info(self):
        logger.info("=" * 60)
        logger.info("SCM 타임 시뮬레이터 가동 준비 완료 (Team Sigma)")
        logger.info(f"  시뮬레이션 가상 기간 : {self.total_days}일 ({self.start_date.strftime('%Y-%m-%d')} 기점)")
        logger.info(f"  목표 소요 시간      : {self.real_seconds}초 ({self.real_seconds / 60:.1f}분)")
        logger.info(f"  제어 주기(1일당)    : {self.tick_interval:.3f}초")
        logger.info("  주입 예정 스트레스 시나리오 명세:")
        for event in self.stress_events:
            logger.info(f"    [{event['start_day']}일~{event['end_day']}일] ➔ {event['description']}")
        logger.info("=" * 60)

    def get_stress_event(self, day: int) -> dict:
        """현재 가상 일자가 위기 지속 기간에 포함되는지 확인 후 가중치 전달"""
        for event in self.stress_events:
            if event["start_day"] <= day <= event["end_day"]:
                # 이벤트 시작일에만 터미널 개행 후 가시성 확보를 위한 워닝 로그 출력
                if day == event["start_day"]:
                    print()  # 프로그레스 바 깨짐 방지 개행
                    logger.warning(f"🚨 [위기 감지] {day}일차 스트레스 이벤트 주입 ➔ {event['description']}")
                
                return {
                    "is_stress": True,
                    "demand_multiplier": event["demand_multiplier"],
                    "lead_time_multiplier": event["lead_time_multiplier"],
                    "description": event["description"]
                }
                
        return {
            "is_stress": False,
            "demand_multiplier": 1.0,
            "lead_time_multiplier": 1.0,
            "description": "정상 변동성 유지"
        }

    def _print_progress(self, day: int, current_date: datetime):
        """진행률 바 가독성 고도화 및 덮어쓰기 출력 관리"""
        percent = (day / self.total_days) * 100
        bar_len = 30
        filled = int(bar_len * day / self.total_days)
        bar = "█" * filled + "░" * (bar_len - filled)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # UI 스트림의 일관성을 위해 캐리지 리턴(\r) 정렬 적용
        print(f"\r[{bar}] {percent:5.1f}% | {day:03d}/{self.total_days}일차 ({date_str})", end="", flush=True)
        if day == self.total_days:
            print() 

    def run(self, pipeline_callback):
        """
        정밀 타임 컴프레션 루프 (TDD 검증 및 에이전트 동기화 코어)
        """
        self.is_running = True
        self.current_day = 0
        global_start_time = time.time()

        logger.info("🚀 SCM 다중 에이전트 파이프라인 압축 시뮬레이션을 시작합니다.")

        while self.current_day < self.total_days:
            tick_start_time = time.time()
            
            self.current_day += 1
            current_virtual_date = self.start_date + timedelta(days=self.current_day - 1)
            
            # 1. 시나리오 기반 동적 컨텍스트(스트레스 상태) 추출
            stress_event = self.get_stress_event(self.current_day)

            # 2. 에이전트 파이프라인 자율 협업 실행 (Isolation Guard)
            try:
                # 진석 데이터 수집 ➔ 정우 확률 분석 ➔ 진석 발주 실행 구조와 동기화
                pipeline_callback(self.current_day, current_virtual_date, stress_event)
            except Exception as e:
                print()  # 에러 발생 시 UI 깨짐 방지
                logger.error(f"❌ [{self.current_day}일차] 에이전트 파이프라인 내부 연산 실패: {str(e)}")
                # 한 에이전트의 예외가 전체 시뮬레이션 스레드를 죽이지 않도록 격리 유지 후 진행

            # 3. 타임라인 진행 상태 갱신
            self._print_progress(self.current_day, current_virtual_date)

            # 4. 동적 타임 슬립 보정 (Dynamic Core Sleep)
            tick_execution_time = time.time() - tick_start_time
            remaining_sleep = self.tick_interval - tick_execution_time

            if remaining_sleep > 0:
                try:
                    time.sleep(remaining_sleep)
                except KeyboardInterrupt:
                    print()
                    logger.warning(f"⚠️ 사용자 강제 중단 명령 수신. {self.current_day}일차에서 엔진을 안전하게 정지합니다.")
                    break
            else:
                # 수학적 알고리즘 연산 누적으로 틱 타임오버 발생 시 디버그 로그 기록
                logger.debug(f"\n[오버헤드 발생] {self.current_day}일차 정밀 타임 스케줄러 지연 보정 (+{abs(remaining_sleep):.4f}초)")

        self.is_running = False
        total_elapsed = time.time() - global_start_time
        self._print_summary(total_elapsed)

    def _print_summary(self, elapsed: float):
        logger.info("=" * 60)
        logger.info("🏁 시뮬레이션 타임 엔진 구동 요약 리포트")
        logger.info(f"  최종 실행 가상 일수 : {self.current_day}/{self.total_days} 일")
        logger.info(f"  실제 총 소요 시간   : {elapsed:.2f}초 ({elapsed / 60:.2f}분)")
        logger.info(f"  목표 압축 시간      : {self.real_seconds:.1f}초")
        logger.info(f"  타임라인 정밀 오차율 : {((elapsed - self.real_seconds) / self.real_seconds) * 100:.2f}%")
        logger.info("=" * 60)
