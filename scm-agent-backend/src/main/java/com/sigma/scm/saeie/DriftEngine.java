package com.sigma.scm.saeie;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@Component
public class DriftEngine {

    public double calculateDriftScore(List<String> mappedCols) {
        Set<String> aEffective = new HashSet<>();
        for (String col : mappedCols) {
            if (col != null) {
                aEffective.add(col);
            }
        }

        Set<String> b = HeaderDetector.COLUMN_ALIASES.keySet();

        // Symmetric difference: (A_effective - B) union (B - A_effective)
        Set<String> symDiff = new HashSet<>(aEffective);
        symDiff.addAll(b);
        Set<String> intersection = new HashSet<>(aEffective);
        intersection.retainAll(b);
        symDiff.removeAll(intersection);

        int maxLen = Math.max(Math.max(aEffective.size(), b.size()), 1);
        double score = (double) symDiff.size() / maxLen;

        // Round to 8 decimal places
        return BigDecimal.valueOf(score)
                .setScale(8, RoundingMode.HALF_UP)
                .doubleValue();
    }

    public double validateDrift(List<String> mappedCols, int unknownColsCount) {
        double score = calculateDriftScore(mappedCols);
        if (unknownColsCount > 5) {
            throw new SaeieException.HeaderDriftException(
                "Header mapping failed: unknown columns count (" + unknownColsCount + ") exceeds maximum limit of 5."
            );
        }
        if (score > 0.5) {
            throw new SaeieException.HeaderDriftException(
                "Header mapping failed: Schema Drift Score (" + score + ") exceeds maximum limit of 0.5."
            );
        }
        return score;
    }
}
