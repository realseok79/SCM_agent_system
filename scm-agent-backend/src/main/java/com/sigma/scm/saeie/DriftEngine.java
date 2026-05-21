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

        if (unknownColsCount > 5) {
            throw new SaeieException.HeaderDriftException(
                "헤더 매핑 실패: 인식되지 않는 컬럼이 " + unknownColsCount + "개로 최대 허용치(5개)를 초과했습니다."
            );
        }

        // 필수 4개 컬럼 중 2개 이상 누락되면 실패 (score > 0.5)
        if (score > 0.5) {
            String missingStr = String.join(", ", missingCols);

            // 한국어 컬럼명 안내 생성
            Map<String, String> koreanHints = Map.of(
                "region_code", "지역/지점/출발지/도착지",
                "product_name", "품목명/상품명/제품명",
                "date", "날짜/일자/기준일/입고일/출고일",
                "quantity", "수량/재고량/이동수량"
            );
            StringBuilder hint = new StringBuilder();
            for (String missing : missingCols) {
                hint.append("\n  - ").append(missing).append(" (예: ").append(koreanHints.getOrDefault(missing, "")).append(")");
            }

            throw new SaeieException.HeaderDriftException(
                "헤더 매핑 실패: 필수 컬럼이 누락되었습니다. (드리프트 점수: " + score + ")\n" +
                "누락된 필수 컬럼:" + hint + "\n" +
                "매핑 성공 컬럼: " + mappedSet + "\n" +
                "엑셀 파일에 위 필수 컬럼에 해당하는 헤더가 포함된 시트가 있는지 확인해 주세요."
            );
        }

        return score;
    }
}
