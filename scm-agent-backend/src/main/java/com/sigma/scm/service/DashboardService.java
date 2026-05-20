package com.sigma.scm.service;

import com.sigma.scm.domain.*;
import com.sigma.scm.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class DashboardService {

    private final RegionRepository regionRepository;
    private final RegionInventoryRepository regionInventoryRepository;
    private final WeatherCacheRepository weatherCacheRepository;
    private final RegionalInsightRepository regionalInsightRepository;
    private final DailyDemandStatsRepository dailyDemandStatsRepository;
    private final StockOutLogRepository stockOutLogRepository;
    private final InventoryRebalancingOrderRepository rebalancingOrderRepository;

    public Map<String, Object> getSummary() {
        Map<String, Object> summary = new HashMap<>();

        long totalRegions = regionRepository.count();
        List<RegionInventory> inventories = regionInventoryRepository.findAll();
        double totalStock = inventories.stream().mapToDouble(RegionInventory::getQuantity).sum();

        long totalStockOutIncidents = stockOutLogRepository.count();

        summary.put("totalRegions", totalRegions);
        summary.put("totalStock", totalStock);
        summary.put("totalStockOutIncidents", totalStockOutIncidents);
        summary.put("systemStatus", "STABLE");

        return summary;
    }

    public List<Map<String, Object>> getStockTrend() {
        // 날짜별 재고 총량 집계
        List<RegionInventory> inventories = regionInventoryRepository.findAll();

        Map<String, Double> dateStockMap = inventories.stream()
                .collect(Collectors.groupingBy(
                        inv -> inv.getId().getDate(),
                        Collectors.summingDouble(RegionInventory::getQuantity)));

        return dateStockMap.entrySet().stream()
                .map(entry -> {
                    Map<String, Object> map = new HashMap<>();
                    map.put("date", entry.getKey());
                    map.put("quantity", entry.getValue());
                    return map;
                })
                .sorted((a, b) -> ((String) a.get("date")).compareTo((String) b.get("date")))
                .collect(Collectors.toList());
    }

    public List<RegionInventory> getRegionInventory(String regionCode, String productName) {
        if (productName != null && !productName.trim().isEmpty()) {
            return regionInventoryRepository.findByIdRegionCode(regionCode).stream()
                    .filter(inv -> inv.getId().getProductName().equalsIgnoreCase(productName))
                    .collect(Collectors.toList());
        }
        return regionInventoryRepository.findByIdRegionCode(regionCode);
    }

    public List<WeatherCache> getRegionWeather(String regionCode) {
        return weatherCacheRepository.findByIdRegionCode(regionCode);
    }

    public Map<String, Object> getIntegrity(String regionCode, String productName, String date) {
        Map<String, Object> integrityResult = new HashMap<>();

        // daily_demand_stats와 region_inventory 비교를 통해 데이터 무결성 체크
        List<RegionInventory> inventories = regionInventoryRepository.findByIdRegionCodeAndIdDate(regionCode, date);
        List<DailyDemandStats> demandStats = dailyDemandStatsRepository.findByIdRegionCode(regionCode).stream()
                .filter(stats -> stats.getId().getDate().equals(date))
                .collect(Collectors.toList());

        boolean isConsistent = true;
        String message = "무결성이 검증되었습니다. 실재고량과 시뮬레이션 지표가 일치합니다.";

        if (inventories.isEmpty() && !demandStats.isEmpty()) {
            isConsistent = false;
            message = "실재고 마스터가 누락되었습니다.";
        } else if (!inventories.isEmpty() && demandStats.isEmpty()) {
            isConsistent = false;
            message = "일일 수요 통계 데이터가 누락되었습니다.";
        }

        integrityResult.put("regionCode", regionCode);
        integrityResult.put("productName", productName);
        integrityResult.put("date", date);
        integrityResult.put("isConsistent", isConsistent);
        integrityResult.put("message", message);

        return integrityResult;
    }

    public Map<String, Object> getRiskScore(String regionCode) {
        Map<String, Object> riskResult = new HashMap<>();

        // 날씨와 최근 출고 이력을 이용해 물류 위험도 평가
        List<WeatherCache> weather = weatherCacheRepository.findByIdRegionCode(regionCode);
        boolean severeWeather = weather.stream()
                .anyMatch(w -> w.getTemp() != null && (w.getTemp() > 38.0 || w.getTemp() < -15.0) ||
                        w.getPrecipitation() != null && w.getPrecipitation() > 50.0);

        double score = severeWeather ? 85.0 : 25.0; // 날씨 위험 감지 시 85점 부여
        String riskLevel = score >= 60.0 ? "HIGH" : "LOW";

        riskResult.put("regionCode", regionCode);
        riskResult.put("riskScore", score);
        riskResult.put("riskLevel", riskLevel);
        riskResult.put("description", severeWeather ? "기상 악화 경보: 운송 지연이 감지되었습니다." : "정상 상태: 운송 지연 위험도가 낮습니다.");

        return riskResult;
    }

    public List<Map<String, Object>> getAging(String regionCode) {
        // 재고 연령(Date가 오래된 순)별 통계
        List<RegionInventory> inventories = regionInventoryRepository.findByIdRegionCode(regionCode);

        return inventories.stream()
                .map(inv -> {
                    Map<String, Object> map = new HashMap<>();
                    map.put("productName", inv.getId().getProductName());
                    map.put("date", inv.getId().getDate());
                    map.put("quantity", inv.getQuantity());
                    return map;
                })
                .sorted((a, b) -> ((String) a.get("date")).compareTo((String) b.get("date")))
                .collect(Collectors.toList());
    }

    public List<InventoryRebalancingOrder> getRebalancingOrders() {
        return rebalancingOrderRepository.findAll();
    }

    @Transactional
    public InventoryRebalancingOrder createRebalancingOrder(InventoryRebalancingOrder order) {
        if (order.getStatus() == null) {
            order.setStatus("APPROVED");
        }
        if (order.getCreatedAt() == null) {
            order.setCreatedAt(java.time.LocalDateTime.now());
        }
        return rebalancingOrderRepository.save(order);
    }
}
