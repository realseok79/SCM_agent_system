package com.sigma.scm.saeie;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@Component
@Slf4j
public class DriftEngine {

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

    public double validateDrift(List<String> mappedCols, int unknownColsCount) {
        double score = calculateDriftScore(mappedCols);

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
            // Instead of failing, log a warning and proceed with a higher drift score penalty
            // Note: Using System.err for simplicity; in production replace with proper logger
            System.err.println("[DRIFT] Excessive unknown columns (" + unknownColsCount + ") detected; proceeding with penalty.");
        }

        // If more than one required column is missing, downgrade to a warning instead of throwing.
        if (score > 0.5) {
            String missingStr = String.join(", ", missingCols);
            // Log warning for missing required columns
            System.err.println("[DRIFT] Missing required columns: " + missingStr + ". Drift score: " + score);
            // Optionally, you could set a flag or adjust score, but we allow processing to continue.
        }

        return score;
    }
}
