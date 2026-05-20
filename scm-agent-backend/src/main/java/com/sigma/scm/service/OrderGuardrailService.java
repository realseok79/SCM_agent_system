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
        double relativeCeiling = avg30d * maxOrderCeilingRatio;

        if (orderQty > relativeCeiling) {
            String reason = String.format("[상대 상한 초과] 요청 %.0f > 동적 한계 %.0f (평균 %.0f × %.1f)", 
                    orderQty, relativeCeiling, avg30d, maxOrderCeilingRatio);
            return new GuardrailResult("BLOCKED", reason, relativeCeiling);
        }

        return new GuardrailResult("APPROVED", "모든 가드레일 제어 조건 만족", relativeCeiling);
    }
}
