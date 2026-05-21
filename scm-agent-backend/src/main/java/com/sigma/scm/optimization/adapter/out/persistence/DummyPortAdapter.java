package com.sigma.scm.optimization.adapter.out.persistence;

import com.sigma.scm.optimization.application.port.out.CallMlServingPort;
import com.sigma.scm.optimization.application.port.out.LoadItemPort;
import com.sigma.scm.optimization.application.port.out.SaveInferenceLogPort;
import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.optimization.domain.model.ReorderDecision;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Component
public class DummyPortAdapter implements LoadItemPort, CallMlServingPort, SaveInferenceLogPort {

    @Override
    public Optional<OptimizationItem> loadItem(String productName) {
        return Optional.empty();
    }

    @Override
    public double loadCurrentStock(String productName, String regionCode) {
        return 0.0;
    }

    @Override
    public int countHistoricalSalesDays(String productName, String regionCode) {
        return 0;
    }

    @Override
    public double loadDailyAverageDemand(String productName, String regionCode) {
        return 0.0;
    }

    @Override
    public List<Double> loadRecentSales(String productName, String regionCode, int days) {
        return Collections.emptyList();
    }

    @Override
    public MlForecastResult callForecast(OptimizationItem item, String regionCode, List<Double> recentSales) {
        return new MlForecastResult() {
            public double getPredicted10() { return 0.0; }
            public double getPredicted50() { return 0.0; }
            public double getPredicted90() { return 0.0; }
            public Map<String, Double> getShapValues() { return Collections.emptyMap(); }
            public String getModelVersion() { return "dummy"; }
        };
    }

    @Override
    public void saveInferenceLog(ReorderDecision decision) {
        // do nothing
    }
}
