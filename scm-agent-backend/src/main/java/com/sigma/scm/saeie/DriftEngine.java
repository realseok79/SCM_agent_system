package com.sigma.scm.saeie;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import com.sigma.scm.repository.RegionInventoryRepository;
import com.sigma.scm.domain.RegionInventory;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;

@Component
@Slf4j
public class DriftEngine {

    private final RegionInventoryRepository regionInventoryRepository;
    private final double[] psiBins;

    public DriftEngine(
            RegionInventoryRepository regionInventoryRepository,
            @Value("${scm.drift.bins:10.0,100.0,500.0,2000.0}") String binsConfig) {
        this.regionInventoryRepository = regionInventoryRepository;
        String[] parts = binsConfig.split(",");
        this.psiBins = new double[parts.length];
        for (int i = 0; i < parts.length; i++) {
            this.psiBins[i] = Double.parseDouble(parts[i].trim());
        }
    }

    // SCM 파이프라인이 최소한으로 필요로 하는 필수 컬럼
    private static final Set<String> REQUIRED_COLUMNS = Set.of(
        "region_code", "product_name", "date", "quantity"
    );

    public double calculateDriftScore(List<String> mappedCols) {
        Set<String> mappedSet = new HashSet<>();
        for (String col : mappedCols) {
            if (col != null) {
                mappedSet.add(col);
            }
        }

        // 필수 컬럼 중 누락된 컬럼 수를 기반으로 드리프트 점수 산출
        int missingRequired = 0;
        for (String req : REQUIRED_COLUMNS) {
            if (!mappedSet.contains(req)) {
                missingRequired++;
            }
        }

        double score = (double) missingRequired / REQUIRED_COLUMNS.size();

        return BigDecimal.valueOf(score)
                .setScale(8, RoundingMode.HALF_UP)
                .doubleValue();
    }

    public double calculateStatisticalDriftScore() {
        try {
            String maxDateStr = regionInventoryRepository.findMaxDate();
            if (maxDateStr == null) {
                return 0.05;
            }

            LocalDate maxDate = LocalDate.parse(maxDateStr);
            LocalDate targetStart = maxDate.minusDays(30);
            LocalDate baselineStart = maxDate.minusDays(120);

            List<RegionInventory> inventories = regionInventoryRepository.findAll();
            List<Double> baseline = new ArrayList<>();
            List<Double> target = new ArrayList<>();

            for (RegionInventory inv : inventories) {
                if (inv.getId() == null || inv.getId().getDate() == null) {
                    continue;
                }
                try {
                    LocalDate date = LocalDate.parse(inv.getId().getDate());
                    double qty = inv.getQuantity() != null ? inv.getQuantity() : 0.0;
                    if (!date.isBefore(targetStart) && !date.isAfter(maxDate)) {
                        target.add(qty);
                    } else if (!date.isBefore(baselineStart) && date.isBefore(targetStart)) {
                        baseline.add(qty);
                    }
                } catch (Exception e) {
                    // Ignore date parsing errors
                }
            }

            if (baseline.isEmpty() || target.isEmpty()) {
                return 0.05;
            }

            // Calculate PSI (Population Stability Index)
            double[] baselineDistribution = calculateDistribution(baseline, psiBins);
            double[] targetDistribution = calculateDistribution(target, psiBins);

            double psi = 0.0;
            double epsilon = 0.0001;
            for (int i = 0; i <= psiBins.length; i++) {
                double expected = baselineDistribution[i] + epsilon;
                double actual = targetDistribution[i] + epsilon;
                psi += (actual - expected) * Math.log(actual / expected);
            }

            log.info("[DRIFT] Calculated statistical PSI drift score: {}", psi);
            double normalizedScore = Math.min(1.0, psi / 0.5);
            return BigDecimal.valueOf(normalizedScore)
                    .setScale(4, RoundingMode.HALF_UP)
                    .doubleValue();

        } catch (Exception e) {
            log.error("[DRIFT] Error calculating statistical drift, returning default fallback", e);
            return 0.1;
        }
    }

    private double[] calculateDistribution(List<Double> values, double[] bins) {
        double[] counts = new double[bins.length + 1];
        for (double val : values) {
            int binIndex = bins.length;
            for (int i = 0; i < bins.length; i++) {
                if (val <= bins[i]) {
                    binIndex = i;
                    break;
                }
            }
            counts[binIndex]++;
        }

        double total = values.size();
        double[] percentages = new double[counts.length];
        for (int i = 0; i < counts.length; i++) {
            percentages[i] = counts[i] / total;
        }
        return percentages;
    }

    public double validateDrift(List<String> mappedCols, int unknownColsCount) {
        double headerDrift = calculateDriftScore(mappedCols);
        double statisticalDrift = calculateStatisticalDriftScore();

        // Combine: header drift takes precedence if headers are majorly broken, otherwise stat drift
        double score = headerDrift > 0.5 ? headerDrift : Math.max(headerDrift, statisticalDrift);

        // 매핑된 컬럼 집합 추출
        Set<String> mappedSet = new HashSet<>();
        for (String col : mappedCols) {
            if (col != null) {
                mappedSet.add(col);
            }
        }

        // 누락된 필수 컬럼 목록 생성
        List<String> missingCols = new ArrayList<>();
        for (String req : REQUIRED_COLUMNS) {
            if (!mappedSet.contains(req)) {
                missingCols.add(req);
            }
        }

        if (unknownColsCount > 10) {
            log.warn("[DRIFT] Excessive unknown columns ({}) detected; proceeding with penalty.", unknownColsCount);
        }

        if (score > 0.25) {
            log.warn("[DRIFT] High data drift detected. Score: {}, Header Drift: {}, Stat Drift: {}", 
                    score, headerDrift, statisticalDrift);
        }

        return score;
    }
}
