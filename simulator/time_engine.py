"""
simulator/time_engine.py
------------------------
100일간의 SCM 데이터 변동을 5분(300초) 이내로 압축 구동하는 타임 시뮬레이터.
각 틱(tick)마다 에이전트 파이프라인을 호출하고, 결과를 로그로 기록합니다.
수학적 연산 및 LLM 오버헤드로 인한 실제 소요 시간을 역계산하여 완벽한 시간 압축을 보장합니다.
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
    SCM 시뮬레이션 타임 엔진 (정밀 시간 보정 적용 버전)
    """

    def __init__(self, total_days: int = None, real_seconds: float = None):
        self.total_days = total_days or int(os.getenv("SIMULATION_DAYS", 100))
        self.real_seconds = real_seconds or float(os.getenv("SIMULATION_SPEED_SECONDS", 300))
        self.tick_interval = self.real_seconds / self.total_days  # 1일당 실제 배정된 소요 시간(초)

        self.current_day = 0
        self.is_running = False

        # 계획서 상의 가상 세계 타임라인 기준점 설정
        self.start_date = datetime(2026, 1, 1)

        # ── 스트레스 테스트 이벤트 스케줄 ──────────────────────────
        self.stress_schedule = {
            30: {
                "demand_multiplier": 5.0,
                "lead_time_multiplier": 1.0,
                "description": "수요 5배 폭증 이벤트 (트렌드 급등)"
            },
            60: {
                "demand_multiplier": 1.0,
                "lead_time_multiplier": 3.0,
                "description": "조달기간 3주 지연 이벤트 (공급망 위기)"
            },
            80: {
                "demand_multiplier": 3.0,
                "lead_time_multiplier": 2.5,
                "description": "⚠️ 최악의 시나리오: 수요 폭증 + 조달 지연 동시 발생"
            },
        }

        self._print_init_info()

    def _print_init_info(self):
        logger.info("=" * 55)
        logger.info("SCM 타임 시뮬레이터 초기화 완료")
        logger.info(f"  시뮬레이션 기간 : {self.total_days}일 (시작 가상일: {self.start_date.strftime('%Y-%m-%d')})")
        logger.info(f"  목표 소요 시간  : {self.real_seconds}초 ({self.real_seconds / 60:.1f}분)")
        logger.info(f"  1일당 압축 틱   : {self.tick_interval:.2f}초/일")
        logger.info("  스트레스 테스트 시나리오:")
        for day, event in self.stress_schedule.items():
            logger.info(f"    {day}일차 → {event['description']}")
        logger.info("=" * 55)

    def get_stress_event(self, day: int) -> dict:
        """해당 일자의 스트레스 이벤트 구조화 반환"""
        if day in self.stress_schedule:
            event = self.stress_schedule[day]
            logger.warning(f"\n[{day}일차] 스트레스 이벤트 감지 ➔ {event['description']}")
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
            "description": "정상 변동성 범위"
        }

    def _print_progress(self, day: int, current_date: datetime):
        """진행률 바에 가상 날짜 정보 추가하여 가독성 증대"""
        percent = (day / self.total_days) * 100
        bar_len = 30
        filled = int(bar_len * day / self.total_days)
        bar = "█" * filled + "░" * (bar_len - filled)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # \r과 end=""를 이용해 단일 라인에서 덮어쓰기 출력
        print(f"\r[{bar}] {percent:5.1f}% | {day}/{self.total_days}일차 ({date_str})", end="", flush=True)
        if day == self.total_days:
            print() 

    def run(self, pipeline_callback):
        """
        시뮬레이션 메인 타임 루프 (정밀 오버헤드 보정 알고리즘 적용)
        """
        self.is_running = True
        self.current_day = 0
        global_start_time = time.time()

        logger.info("🚀 SCM 자율화 파이프라인 압축 시뮬레이션을 시작합니다.")

        while self.current_day < self.total_days:
            # 1. 틱 시작 시각 기록
            tick_start_time = time.time()
            
            self.current_day += 1
            current_virtual_date = self.start_date + timedelta(days=self.current_day - 1)
            
            # 2. 스트레스 상태 확인
            stress_event = self.get_stress_event(self.current_day)

            # 3. 에이전트 파이프라인 실행 가드레일 (Isolation)
            try:
                # 콜백 아규먼트에 가상 날짜 개체(datetime)를 추가하여 데이터 수집 에이전트가 활용 가능케 함
                pipeline_callback(self.current_day, current_virtual_date, stress_event)
            except Exception as e:
                logger.error(f"❌ [{self.current_day}일차] 파이프라인 구동 중 치명적 에러 발생: {str(e)}")
                # 프로젝트 요건에 따라 break할지, continue할지 결정. 여기선 시스템 격리 후 진행 선택.

            # 4. 프로그레스 갱신
            self._print_progress(self.current_day, current_virtual_date)

            # 5. 시간 동기화 보정 계산 (Dynamic Sleep)
            tick_execution_time = time.time() - tick_start_time  # 파이프라인이 잡아먹은 실제 시간
            remaining_sleep = self.tick_interval - tick_execution_time

            if remaining_sleep > 0:
                try:
                    time.sleep(remaining_sleep)
                except KeyboardInterrupt:
                    logger.warning(f"\n⚠️ 사용자 인터럽트로 인해 {self.current_day}일차에서 강제 종료됩니다.")
                    break
            else:
                # 파이프라인 연산 오버헤드가 배정된 1일 압축 시간보다 큰 경우 경고 처리
                logger.debug(f"\n[오버헤드 경고] {self.current_day}일차 연산 지연 발생 (+{abs(remaining_sleep):.3f}초)")

        self.is_running = False
        total_elapsed = time.time() - global_start_time
        self._print_summary(total_elapsed)

    def _print_summary(self, elapsed: float):
        logger.info("=" * 55)
        logger.info("🏁 시뮬레이션 최종 구동 요약")
        logger.info(f"  총 가상 운영 일수 : {self.current_day}/{self.total_days} 일")
        logger.info(f"  실제 총 소요 시간 : {elapsed:.2f}초 ({elapsed / 60:.1f}분)")
        logger.info(f"  설정 목표 소요 시간: {self.real_seconds:.1f}초")
        logger.info(f"  타임라인 오차율    : {((elapsed - self.real_seconds) / self.real_seconds) * 100:.2f}%")
        logger.info("=" * 55)
