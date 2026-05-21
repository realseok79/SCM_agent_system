package com.sigma.scm.optimization.application.port.out;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import java.util.List;
import java.util.Map;

public interface CallMlServingPort {
    MlForecastResult callForecast(OptimizationItem item, String regionCode, List<Double> recentSales) throws Exception;

    interface MlForecastResult {
        double getPredicted10();
        double getPredicted50();
        double getPredicted90();
        Map<String, Double> getShapValues();
        String getModelVersion();
    }
}
