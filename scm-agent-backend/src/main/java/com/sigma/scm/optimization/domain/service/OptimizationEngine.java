package com.sigma.scm.optimization.domain.service;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.optimization.domain.model.ReorderDecision;

import java.util.Map;

public class OptimizationEngine {

    public double calculateEOQ(OptimizationItem item, double dailyAvgDemand) {
        if (item == null) {
            return 0.0;
        }
        double annualDemand = Math.max(0.0, dailyAvgDemand) * 365.0;
        double s = Math.max(0.0, item.getOrderingCostFixed());
        double h = Math.max(0.0, item.getUnitPrice()) * Math.max(0.0, item.getHoldingCostRate());
        if (h <= 0.0) {
            h = 0.1; // Prevent division by zero, normalized clipping to 0.1
        }
        double eoq = Math.sqrt((2.0 * annualDemand * s) / h);
        return Double.isNaN(eoq) || Double.isInfinite(eoq) ? 0.0 : eoq;
    }

    public ReorderDecision makeDecision(
            OptimizationItem item,
            String regionCode,
            double dailyAvgDemand,
            double currentStock,
            int dataPointsCount,
            double predicted10,
            double predicted50,
            double predicted90,
            Map<String, Double> shapValues,
            String modelVersion
    ) {
        if (item == null) {
            throw new IllegalArgumentException("OptimizationItem profile cannot be null");
        }

        double eoq = calculateEOQ(item, dailyAvgDemand);
        double rop = 0.0;
        double safetyStock = 0.0;
        boolean isColdStart = dataPointsCount < 90;
        
        int leadTimeDays = Math.max(0, item.getBaseLeadTimeDays());
        String abcClass = item.getAbcClass() != null ? item.getAbcClass().trim().toUpperCase() : "C";

        if (isColdStart) {
            double z = 1.28;
            if ("A".equals(abcClass)) {
                z = 1.96;
            } else if ("B".equals(abcClass)) {
                z = 1.65;
            }
            double sigma = Math.max(0.0, dailyAvgDemand) * 0.25;
            safetyStock = z * sigma * Math.sqrt(leadTimeDays);
            rop = (Math.max(0.0, dailyAvgDemand) * leadTimeDays) + safetyStock;
        } else {
            // Safety stock is the difference between 90th percentile and 50th percentile (average) over lead time
            double diff = Math.max(0.0, predicted90 - predicted50);
            safetyStock = diff * leadTimeDays;
            rop = Math.max(0.0, predicted90) * leadTimeDays;
        }

        // Defensive normalization to prevent NaN/Infinity propagating to Database
        if (Double.isNaN(safetyStock) || Double.isInfinite(safetyStock)) {
            safetyStock = 0.0;
        }
        if (Double.isNaN(rop) || Double.isInfinite(rop)) {
            rop = 0.0;
        }
        if (Double.isNaN(eoq) || Double.isInfinite(eoq)) {
            eoq = 0.0;
        }

        boolean triggerReorder = Math.max(0.0, currentStock) <= rop;

        return ReorderDecision.builder()
                .productName(item.getProductName())
                .regionCode(regionCode != null ? regionCode : "unknown")
                .eoq(Math.round(eoq * 100.0) / 100.0)
                .rop(Math.round(rop * 100.0) / 100.0)
                .predictedDemand10(Double.isNaN(predicted10) ? 0.0 : predicted10)
                .predictedDemand50(Double.isNaN(predicted50) ? 0.0 : predicted50)
                .predictedDemand90(Double.isNaN(predicted90) ? 0.0 : predicted90)
                .safetyStock(Math.round(safetyStock * 100.0) / 100.0)
                .isColdStart(isColdStart)
                .triggerReorder(triggerReorder)
                .shapValues(shapValues)
                .modelVersion(modelVersion != null ? modelVersion : "none")
                .build();
    }
}
