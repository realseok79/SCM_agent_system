# agents/feedback_engine.py
import re
import db

class FeedbackEngine:
    def __init__(self):
        pass

    def parse_rejection_reason(self, reason_text):
        """
        반려 사유 텍스트를 자연어 기반 룰 매칭으로 파싱하여 임계값 보정 방향과 크기를 결정합니다.
        방향: -1 (하향), +1 (상향), 0 (중립/감지 불가)
        강도: 기본값 0.05 (5%), 텍스트에서 % 감지 시 해당 비율 적용
        """
        if not reason_text:
            return 0, 0.05

        reason_text = reason_text.lower()
        direction = 0

        # 보정 방향 결정
        down_keywords = ["하향", "낮추", "줄이", "감소", "인하", "down", "lower", "decrease", "reduce"]
        up_keywords = ["상향", "높이", "늘리", "증가", "인상", "up", "raise", "increase", "elevate"]

        for kw in down_keywords:
            if kw in reason_text:
                direction = -1
                break

        if direction == 0:
            for kw in up_keywords:
                if kw in reason_text:
                    direction = 1
                    break

        # 보정 강도 추출 (예: "15% 하향" -> 0.15)
        rate = 0.05  # 기본 5%
        percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", reason_text)
        if percent_match:
            try:
                rate = float(percent_match.group(1)) / 100.0
            except ValueError:
                pass
        else:
            # 실수 매핑 감지 (예: "0.1 하향" -> 0.10)
            float_match = re.search(r"\b(0\.\d+)\b", reason_text)
            if float_match:
                try:
                    rate = float(float_match.group(1))
                except ValueError:
                    pass

        return direction, rate

    def process_pending_feedbacks(self):
        """
        아직 반영되지 않은(applied = 0) 반려 피드백 로그들을 분석하여,
        guardrail_parameters의 current_threshold를 보정 및 Bounding Clip 처리합니다.
        """
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. 미반영 반려 로그 수집
            cursor.execute("SELECT id, order_id, sku, reason FROM order_feedback_log WHERE action = 'REJECTED' AND applied = 0")
            rows = cursor.fetchall()
            if not rows:
                return 0

            processed_count = 0
            for row in rows:
                log_id, order_id, sku, reason = row["id"], row["order_id"], row["sku"], row["reason"]
                
                # 2. 반려 사유 파싱
                direction, rate = self.parse_rejection_reason(reason)
                
                if direction == 0:
                    # 보정 방향을 알 수 없는 경우 스킵하되 applied = 1 처리
                    cursor.execute("UPDATE order_feedback_log SET applied = 1 WHERE id = ?", (log_id,))
                    continue

                # 3. guardrail_parameters 조회
                cursor.execute("SELECT current_threshold, base_threshold, min_clip_rate, max_clip_rate FROM guardrail_parameters WHERE sku = ?", (sku,))
                param_row = cursor.fetchone()
                
                if not param_row:
                    # 만약 없으면 기본값으로 인서트
                    cursor.execute("INSERT INTO guardrail_parameters (sku, current_threshold, base_threshold, min_clip_rate, max_clip_rate) VALUES (?, 1.0, 1.0, 0.5, 1.5)", (sku,))
                    cursor.execute("SELECT current_threshold, base_threshold, min_clip_rate, max_clip_rate FROM guardrail_parameters WHERE sku = ?", (sku,))
                    param_row = cursor.fetchone()

                curr_t = param_row["current_threshold"]
                base_t = param_row["base_threshold"]
                min_clip = param_row["min_clip_rate"]
                max_clip = param_row["max_clip_rate"]

                # 4. 피드백 연산 및 Bounding Clip 적용
                # 예: 15% 하향 -> curr_t = curr_t * (1 - 0.15)
                # 예: 5% 상향 -> curr_t = curr_t * (1 + 0.05)
                new_t = curr_t * (1.0 + (direction * rate))

                # 상하한 Bounding Clip 억제
                min_allowed = base_t * min_clip
                max_allowed = base_t * max_clip

                if new_t < min_allowed:
                    new_t = min_allowed
                elif new_t > max_allowed:
                    new_t = max_allowed

                # 5. DB 업데이트
                cursor.execute("""
                    UPDATE guardrail_parameters 
                    SET current_threshold = ?, updated_at = datetime('now')
                    WHERE sku = ?
                """, (new_t, sku))

                cursor.execute("UPDATE order_feedback_log SET applied = 1 WHERE id = ?", (log_id,))
                processed_count += 1

            conn.commit()
            return processed_count

        except Exception as e:
            conn.rollback()
            print(f"FeedbackEngine failed to process: {e}")
            raise e
        finally:
            conn.close()

if __name__ == "__main__":
    # 단위 테스트 코드
    engine = FeedbackEngine()
    dir_test, rate_test = engine.parse_rejection_reason("ROP 임계치가 너무 높음. 안전재고 기준 15% 하향 필요.")
    print(f"Parsed Rejection Reason: Direction={dir_test}, Rate={rate_test}")
