package com.sigma.scm.optimization.application.port.out;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import java.util.List;
import java.util.Optional;

public interface LoadItemPort {
    Optional<OptimizationItem> loadItem(String productName);
    double loadCurrentStock(String productName, String regionCode);
    int countHistoricalSalesDays(String productName, String regionCode);
    double loadDailyAverageDemand(String productName, String regionCode);
    List<Double> loadRecentSales(String productName, String regionCode, int days);
}
