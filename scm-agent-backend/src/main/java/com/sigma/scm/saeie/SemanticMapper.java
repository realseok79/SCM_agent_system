package com.sigma.scm.saeie;

import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.text.Normalizer;
import java.util.*;

@Component
@RequiredArgsConstructor
public class SemanticMapper {

    private final JdbcTemplate jdbcTemplate;

    public static String canonicalizeHeader(String rawHeader) {
        if (rawHeader == null) {
            return "";
        }
        // NFC Normalization
        String norm = Normalizer.normalize(rawHeader, Normalizer.Form.NFC);
        String cleaned = norm.trim().toLowerCase();
        // Keep letters and numbers (Korean character range: 가-힣 included)
        cleaned = cleaned.replaceAll("[^a-zA-Z0-9가-힣]", "");
        return cleaned;
    }

    public static int levenshteinDistance(String s1, String s2) {
        int len1 = s1.length();
        int len2 = s2.length();

        if (len1 < len2) {
            return levenshteinDistance(s2, s1);
        }
        if (len2 == 0) {
            return len1;
        }

        int[] previousRow = new int[len2 + 1];
        for (int i = 0; i <= len2; i++) {
            previousRow[i] = i;
        }

        for (int i = 0; i < len1; i++) {
            int[] currentRow = new int[len2 + 1];
            currentRow[0] = i + 1;
            char c1 = s1.charAt(i);
            for (int j = 0; j < len2; j++) {
                int insertions = previousRow[j + 1] + 1;
                int deletions = currentRow[j] + 1;
                int substitutions = previousRow[j] + (c1 == s2.charAt(j) ? 0 : 1);
                currentRow[j + 1] = Math.min(Math.min(insertions, deletions), substitutions);
            }
            previousRow = currentRow;
        }

        return previousRow[len2];
    }

    private static final Map<String, Double> SEMANTIC_PAIRS = new HashMap<>();
    static {
        // ── quantity 계열 ──
        SEMANTIC_PAIRS.put(getPairKey("물품수량", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("수량", "quantity"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("개수", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("재고량", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("재고수량", "quantity"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("입고수량", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("출고수량", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("이동수량", "quantity"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("물량", "quantity"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("총수량", "quantity"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("총량", "quantity"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("주문수량", "quantity"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("발주수량", "quantity"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("배송수량", "quantity"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("입고량", "quantity"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("출고량", "quantity"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("현재고", "quantity"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("판매수량", "quantity"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("판매량", "quantity"), 0.80);

        // ── date 계열 ──
        SEMANTIC_PAIRS.put(getPairKey("날짜", "date"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("일자", "date"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("입고날짜", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("출고날짜", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("기준일", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("기준일자", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("입고일", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("출고일", "date"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("이동일", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("등록일", "date"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("주문일", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("배송일", "date"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("배송일자", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("발주일", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("발주일자", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("거래일", "date"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("거래일자", "date"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("처리일", "date"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("작업일", "date"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("생산일", "date"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("마감일", "date"), 0.75);

        // ── region_code 계열 ──
        SEMANTIC_PAIRS.put(getPairKey("지역", "region_code"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("지점", "region_code"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("지역명", "region_code"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("지역코드", "region_code"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("창고", "region_code"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("창고명", "region_code"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("물류창고", "region_code"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("물류센터", "region_code"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("센터", "region_code"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("센터명", "region_code"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("배송지", "region_code"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("거점", "region_code"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("거점명", "region_code"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("공장", "region_code"), 0.75);
        SEMANTIC_PAIRS.put(getPairKey("보관장소", "region_code"), 0.75);
        SEMANTIC_PAIRS.put(getPairKey("출발지", "region_code"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("도착지", "region_code"), 0.80);

        // ── product_name 계열 ──
        SEMANTIC_PAIRS.put(getPairKey("상품명", "product_name"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("품목명", "product_name"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("품명", "product_name"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("제품명", "product_name"), 0.90);
        SEMANTIC_PAIRS.put(getPairKey("물품명", "product_name"), 0.88);
        SEMANTIC_PAIRS.put(getPairKey("물품", "product_name"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("물건", "product_name"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("물건명", "product_name"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("자재명", "product_name"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("자재", "product_name"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("부품명", "product_name"), 0.80);
        SEMANTIC_PAIRS.put(getPairKey("모델명", "product_name"), 0.78);
        SEMANTIC_PAIRS.put(getPairKey("아이템", "product_name"), 0.82);
        SEMANTIC_PAIRS.put(getPairKey("아이템명", "product_name"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("상품", "product_name"), 0.85);
        SEMANTIC_PAIRS.put(getPairKey("제품", "product_name"), 0.85);

        // ── 무관한 컬럼들 (낮은 점수로 오매핑 방지) ──
        SEMANTIC_PAIRS.put(getPairKey("담당자이름", "quantity"), 0.15);
        SEMANTIC_PAIRS.put(getPairKey("담당자이름", "date"), 0.10);
        SEMANTIC_PAIRS.put(getPairKey("담당자이름", "region_code"), 0.10);
        SEMANTIC_PAIRS.put(getPairKey("담당자이름", "product_name"), 0.15);
        SEMANTIC_PAIRS.put(getPairKey("비고", "quantity"), 0.10);
        SEMANTIC_PAIRS.put(getPairKey("비고", "product_name"), 0.10);
        SEMANTIC_PAIRS.put(getPairKey("메모", "quantity"), 0.10);
        SEMANTIC_PAIRS.put(getPairKey("메모", "product_name"), 0.10);
    }

    private static String getPairKey(String s1, String s2) {
        String c1 = canonicalizeHeader(s1);
        String c2 = canonicalizeHeader(s2);
        if (c1.compareTo(c2) < 0) {
            return c1 + "::" + c2;
        } else {
            return c2 + "::" + c1;
        }
    }

    public static double getSimilarity(String rawHeader, String alias) {
        String c1 = canonicalizeHeader(rawHeader);
        String c2 = canonicalizeHeader(alias);
        if (c1.equals(c2)) {
            return 1.0;
        }
        String key = getPairKey(rawHeader, alias);
        if (SEMANTIC_PAIRS.containsKey(key)) {
            return SEMANTIC_PAIRS.get(key);
        }
        return levenshteinSimilarity(rawHeader, alias);
    }

    public static double levenshteinSimilarity(String s1, String s2) {
        String s1Clean = canonicalizeHeader(s1);
        String s2Clean = canonicalizeHeader(s2);
        int maxLen = Math.max(Math.max(s1Clean.length(), s2Clean.length()), 1);
        int dist = levenshteinDistance(s1Clean, s2Clean);
        return 1.0 - ((double) dist / maxLen);
    }

    private double getMappingDbNegativeScore(String companyId, String rawHeader, String targetCol) {
        try {
            Double score = jdbcTemplate.queryForObject(
                "SELECT negative_score FROM company_excel_mapping WHERE company_id = ? AND raw_header = ? AND mapped_column = ?",
                Double.class,
                companyId, rawHeader, targetCol
            );
            return score != null ? score : 0.0;
        } catch (Exception e) {
            return 0.0;
        }
    }

    public static double clamp(double val, double min, double max) {
        return Math.max(min, Math.min(val, max));
    }

    public static class MappingCandidate implements Comparable<MappingCandidate> {
        public String stdCol;
        public double confidence;
        public double maxSim;
        public double negativeScore;
        
        // Sorting keys matching Python:
        public int exactMatchKey; // 0 for exact, 1 otherwise
        public double negConfidenceKey; // -confidence
        public double negativeScoreKey; // negative_score
        public double negMaxSimKey; // -maxSim
        public String stdColKey; // alphabetical stable tie-breaker

        @Override
        public int compareTo(MappingCandidate o) {
            int cmp = Integer.compare(this.exactMatchKey, o.exactMatchKey);
            if (cmp != 0) return cmp;
            cmp = Double.compare(this.negConfidenceKey, o.negConfidenceKey);
            if (cmp != 0) return cmp;
            cmp = Double.compare(this.negativeScoreKey, o.negativeScoreKey);
            if (cmp != 0) return cmp;
            cmp = Double.compare(this.negMaxSimKey, o.negMaxSimKey);
            if (cmp != 0) return cmp;
            return this.stdColKey.compareTo(o.stdColKey);
        }
    }

    public Map.Entry<String, Double> resolveSemanticMapping(String companyId, String rawHeader, double minThreshold) {
        String rawClean = canonicalizeHeader(rawHeader);
        if (rawClean.isEmpty()) {
            return null;
        }

        List<MappingCandidate> candidates = new ArrayList<>();

        for (Map.Entry<String, List<String>> entry : HeaderDetector.COLUMN_ALIASES.entrySet()) {
            String stdCol = entry.getKey();
            List<String> aliases = entry.getValue();

            String stdClean = canonicalizeHeader(stdCol);
            boolean isExact = rawClean.equals(stdClean);

            double maxSim = 0.0;
            boolean isAliasExact = false;
            for (String alias : aliases) {
                String aliasClean = canonicalizeHeader(alias);
                if (rawClean.equals(aliasClean)) {
                    isAliasExact = true;
                }
                double sim = getSimilarity(rawHeader, alias);
                if (sim > maxSim) {
                    maxSim = sim;
                }
            }

            double aliasWeight;
            boolean isExactMatch;
            if (isExact) {
                aliasWeight = 1.0;
                isExactMatch = true;
            } else if (isAliasExact) {
                aliasWeight = 0.85;
                isExactMatch = true;
            } else {
                aliasWeight = 0.72;
                isExactMatch = false;
            }

            double negScore = getMappingDbNegativeScore(companyId, rawHeader, stdCol);
            double rejectionPenalty = 0.10;
            double penaltyFactor = clamp(negScore * rejectionPenalty, 0.0, 0.8);
            double confidence = aliasWeight * maxSim * (1.0 - penaltyFactor);

            MappingCandidate candidate = new MappingCandidate();
            candidate.stdCol = stdCol;
            candidate.confidence = confidence;
            candidate.maxSim = maxSim;
            candidate.negativeScore = negScore;
            
            candidate.exactMatchKey = isExactMatch ? 0 : 1;
            candidate.negConfidenceKey = -confidence;
            candidate.negativeScoreKey = negScore;
            candidate.negMaxSimKey = -maxSim;
            candidate.stdColKey = stdCol;

            candidates.add(candidate);
        }

        Collections.sort(candidates);

        MappingCandidate best = candidates.get(0);
        if (best.confidence >= minThreshold) {
            return new AbstractMap.SimpleEntry<>(best.stdCol, best.confidence);
        }

        return null;
    }
}
