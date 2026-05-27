package com.sigma.scm.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class OrderGuardrailService {

    @Value("${scm.guardrails.absolute-max-capacity:10000.0}")
    private double absoluteMaxCapacity;

    @Value("${scm.guardrails.max-order-ceiling-ratio:3.0}")
    private double maxOrderCeilingRatio;

    public static class GuardrailResult {
        private final String status;
        private final String reason;
        private final double ceiling;

        public GuardrailResult(String status, String reason, double ceiling) {
            this.status = status;
            this.reason = reason;
            this.ceiling = ceiling;
        }

        public String getStatus() { return status; }
        public String getReason() { return reason; }
        public double getCeiling() { return ceiling; }
    }

    public GuardrailResult validateOrder(double orderQty, List<Double> recentHistory) {
        // 시스템 현재 날짜 기준으로 가을 추석(9월), 연말(11, 12월) 등 성수기 계절성 자동 반영 (Fallback)
        int currentMonth = java.time.LocalDate.now().getMonthValue();
        double seasonalityFactor = 1.0;
        if (currentMonth == 11 || currentMonth == 12) {
            seasonalityFactor = 2.0; // 블랙프라이데이 및 연말 시즌
        } else if (currentMonth == 9) {
            seasonalityFactor = 1.8; // 추석 시즌
        }
        return validateOrder(orderQty, recentHistory, seasonalityFactor);
    }

    public GuardrailResult validateOrder(double orderQty, List<Double> recentHistory, double yoySeasonalityFactor) {
        // 1. 절대 상한선 검증
        if (orderQty > absoluteMaxCapacity) {
            String reason = String.format("[절대 상한 초과] 요청 %.0f > 창고 최대 한계 %.0f", orderQty, absoluteMaxCapacity);
            return new GuardrailResult("BLOCKED", reason, absoluteMaxCapacity);
        }

        // 2. 상대 상한선 검증 (t < 5 인 초기 상태는 보류 및 자동 승인)
        if (recentHistory == null || recentHistory.size() < 5) {
            return new GuardrailResult("APPROVED", "초기 상태 절대 상한 통과", absoluteMaxCapacity);
        }

        double sum = 0.0;
        for (double val : recentHistory) {
            sum += val;
        }
        double avg30d = sum / recentHistory.size();

        // 계절성 요인을 적용하여 동적으로 천장 비율(3.0x -> 최대 7.0x) 확장
        double dynamicCeilingRatio = maxOrderCeilingRatio;
        if (yoySeasonalityFactor > 1.0) {
            dynamicCeilingRatio = Math.min(7.0, maxOrderCeilingRatio * yoySeasonalityFactor);
        }

        double relativeCeiling = avg30d * dynamicCeilingRatio;

        if (orderQty > relativeCeiling) {
            String reason = String.format("[상대 상한 초과] 요청 %.0f > 동적 한계 %.0f (평균 %.0f × 동적비율 %.1f, 계절인자 %.2f)", 
                    orderQty, relativeCeiling, avg30d, dynamicCeilingRatio, yoySeasonalityFactor);
            return new GuardrailResult("BLOCKED", reason, relativeCeiling);
        }

        return new GuardrailResult("APPROVED", 
                String.format("모든 가드레일 제어 조건 만족 (평균 %.0f × 동적비율 %.1f)", avg30d, dynamicCeilingRatio), 
                relativeCeiling);
    }
}
