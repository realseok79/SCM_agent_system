package com.sigma.scm.service;

import com.sigma.scm.domain.DailyDemandStats;
import com.sigma.scm.domain.DailyDemandStatsId;
import com.sigma.scm.domain.ProductFinancialMaster;
import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.domain.RegionInventoryId;
import com.sigma.scm.repository.DailyDemandStatsRepository;
import com.sigma.scm.repository.ProductFinancialMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class IntegrityService {

    private final RegionInventoryRepository regionInventoryRepository;
    private final DailyDemandStatsRepository dailyDemandStatsRepository;
    private final ProductFinancialMasterRepository productFinancialMasterRepository;

    public static class IntegrityResult {
        private final boolean hasDiscrepancy;
        private final double yesterdayQty;
        private final double todayQty;
        private final double computedDelta;
        private final double actualOutbound;
        private final double shrinkageQty;
        private final double shrinkageCost;
        private final String message;

        public IntegrityResult(boolean hasDiscrepancy, double yesterdayQty, double todayQty, double computedDelta,
                               double actualOutbound, double shrinkageQty, double shrinkageCost, String message) {
            this.hasDiscrepancy = hasDiscrepancy;
            this.yesterdayQty = yesterdayQty;
            this.todayQty = todayQty;
            this.computedDelta = computedDelta;
            this.actualOutbound = actualOutbound;
            this.shrinkageQty = shrinkageQty;
            this.shrinkageCost = shrinkageCost;
            this.message = message;
        }

        public boolean isHasDiscrepancy() { return hasDiscrepancy; }
        public double getYesterdayQty() { return yesterdayQty; }
        public double getTodayQty() { return todayQty; }
        public double getComputedDelta() { return computedDelta; }
        public double getActualOutbound() { return actualOutbound; }
        public double getShrinkageQty() { return shrinkageQty; }
        public double getShrinkageCost() { return shrinkageCost; }
        public String getMessage() { return message; }
    }

    public IntegrityResult verifyStockIntegrity(String regionCode, String productName, LocalDate targetDate) {
        if (targetDate == null) {
            targetDate = LocalDate.now();
        }

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        String todayStr = targetDate.format(formatter);
        String yesterdayStr = targetDate.minusDays(1).format(formatter);

        try {
            // 1. 어제 재고와 오늘 재고 조회
            RegionInventoryId yesterdayId = new RegionInventoryId(regionCode, productName, yesterdayStr);
            RegionInventoryId todayId = new RegionInventoryId(regionCode, productName, todayStr);

            double yesterdayQty = regionInventoryRepository.findById(yesterdayId)
                    .map(RegionInventory::getQuantity)
                    .orElse(-1.0);

            double todayQty = regionInventoryRepository.findById(todayId)
                    .map(RegionInventory::getQuantity)
                    .orElse(-1.0);

            // 데이터가 둘 중 하나라도 없으면 분석 불가 (정상으로 간주하여 폴백)
            if (yesterdayQty < 0 || todayQty < 0) {
                return new IntegrityResult(
                        false,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        "비교할 이전 또는 당일의 장부 재고 데이터가 부족합니다."
                );
            }

            // 전산상 감소량 (전산 변동량)
            double computedDelta = yesterdayQty - todayQty;

            // 2. 실제 기록된 트랜잭션 출고 합계 조회
            DailyDemandStatsId statsId = new DailyDemandStatsId(regionCode, productName, todayStr);
            double actualOutbound = dailyDemandStatsRepository.findById(statsId)
                    .map(DailyDemandStats::getDailyOutboundTotal)
                    .orElse(0.0);

            // 3. 불일치(Shrinkage) 계산
            double shrinkageQty = computedDelta - actualOutbound;

            // 4. 유실 자산 누수액(Cost_shrink) 산출
            int unitPrice = productFinancialMasterRepository.findById(productName)
                    .map(ProductFinancialMaster::getUnitPrice)
                    .orElse(10000);
            double shrinkageCost = shrinkageQty * unitPrice;

            // 소수점 오차 방지
            boolean hasDiscrepancy = Math.abs(shrinkageQty) > 0.01;
            String message;

            if (hasDiscrepancy) {
                if (shrinkageQty > 0) {
                    message = String.format(java.util.Locale.US, "전산 변동량(%.1f개)과 실제 트랜잭션 출고량(%.1f개)이 일치하지 않습니다. **%.1f개**의 원인 불명 유실(Shrinkage)이 의심되며, 예상 누수액은 **₩%,.0f** 입니다. 창고 실사를 권장합니다.",
                            computedDelta, actualOutbound, shrinkageQty, shrinkageCost);
                } else {
                    message = String.format(java.util.Locale.US, "경고: 실제 트랜잭션 출고량(%.1f개)이 전산 재고 변동량(%.1f개)을 초과했습니다. 초과 출고 **%.1f개** (₩%,.0f) 에 대한 오기입 검토가 필요합니다.",
                            actualOutbound, computedDelta, Math.abs(shrinkageQty), Math.abs(shrinkageCost));
                }
            } else {
                message = "전산 장부 재고 변동과 트랜잭션 출고 로그가 완벽히 일치하여 데이터 무결성이 검증되었습니다.";
            }

            return new IntegrityResult(
                    hasDiscrepancy,
                    yesterdayQty,
                    todayQty,
                    computedDelta,
                    actualOutbound,
                    shrinkageQty,
                    shrinkageCost,
                    message
            );

        } catch (Exception e) {
            return new IntegrityResult(
                    false,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    "무결성 분석 도중 에러가 발생했습니다: " + e.getMessage()
            );
        }
    }
}
