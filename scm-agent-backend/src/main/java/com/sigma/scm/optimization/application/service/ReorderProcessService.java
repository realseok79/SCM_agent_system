package com.sigma.scm.optimization.application.service;

import com.sigma.scm.optimization.application.port.in.ReorderProcessUseCase;
import com.sigma.scm.optimization.application.port.out.CallMlServingPort;
import com.sigma.scm.optimization.application.port.out.LoadItemPort;
import com.sigma.scm.optimization.application.port.out.SaveInferenceLogPort;
import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.optimization.domain.model.ReorderDecision;
import com.sigma.scm.optimization.domain.service.OptimizationEngine;
import com.sigma.scm.optimization.domain.service.filter.ConstraintFilterChain;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ReorderProcessService implements ReorderProcessUseCase {

    private final LoadItemPort loadItemPort;
    private final SaveInferenceLogPort saveInferenceLogPort;
    private final CallMlServingPort callMlServingPort;
    private final ConstraintFilterChain constraintFilterChain;
    private final OptimizationEngine optimizationEngine = new OptimizationEngine();

    @Override
    public ReorderDecision evaluateReorder(String productName, String regionCode) {
        OptimizationItem item = loadItemPort.loadItem(productName)
                .orElseThrow(() -> new IllegalArgumentException("Product financial profile not found for: " + productName));

        double currentStock = loadItemPort.loadCurrentStock(productName, regionCode);
        int salesDaysCount = loadItemPort.countHistoricalSalesDays(productName, regionCode);
        double dailyAvg = loadItemPort.loadDailyAverageDemand(productName, regionCode);
        if (dailyAvg <= 0.0) {
            dailyAvg = 10.0;
        }

        double pred10 = 0.0;
        double pred50 = 0.0;
        double pred90 = 0.0;
        Map<String, Double> shapValues = new HashMap<>();
        String modelVersion = "none";

        boolean isColdStart = salesDaysCount < 90;
        boolean isClassC = "C".equalsIgnoreCase(item.getAbcClass());

        if (!isColdStart && !isClassC) {
            List<Double> recentSales = loadItemPort.loadRecentSales(productName, regionCode, 45);
            try {
                CallMlServingPort.MlForecastResult mlResult = callMlServingPort.callForecast(item, regionCode, recentSales);
                pred10 = mlResult.getPredicted10();
                pred50 = mlResult.getPredicted50();
                pred90 = mlResult.getPredicted90();
                shapValues = mlResult.getShapValues();
                modelVersion = mlResult.getModelVersion();
            } catch (Exception e) {
                isColdStart = true;
            }
        } else {
            isColdStart = true;
        }

        ReorderDecision decision = optimizationEngine.makeDecision(
                item,
                regionCode,
                dailyAvg,
                currentStock,
                isColdStart ? 0 : 100,
                pred10,
                pred50,
                pred90,
                shapValues,
                modelVersion
        );

        if (decision.isTriggerReorder()) {
            double filteredEoq = constraintFilterChain.process(item, decision.getEoq());
            decision = ReorderDecision.builder()
                    .productName(decision.getProductName())
                    .regionCode(decision.getRegionCode())
                    .eoq(filteredEoq)
                    .rop(decision.getRop())
                    .predictedDemand10(decision.getPredictedDemand10())
                    .predictedDemand50(decision.getPredictedDemand50())
                    .predictedDemand90(decision.getPredictedDemand90())
                    .safetyStock(decision.getSafetyStock())
                    .isColdStart(decision.isColdStart())
                    .triggerReorder(decision.isTriggerReorder())
                    .shapValues(decision.getShapValues())
                    .modelVersion(decision.getModelVersion())
                    .build();
        }

        saveInferenceLogPort.saveInferenceLog(decision);
        return decision;
    }
}
