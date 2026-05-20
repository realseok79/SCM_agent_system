package com.sigma.scm.saeie;

import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class HeaderDetector {

    public static final Map<String, List<String>> COLUMN_ALIASES = new HashMap<>();

    static {
        COLUMN_ALIASES.put("region_code", Arrays.asList("지점", "지역", "지역명", "region", "regionname", "location", "branch", "region_code", "regioncode"));
        COLUMN_ALIASES.put("product_name", Arrays.asList("상품명", "상품이름", "품목", "품목명", "product", "productname", "producttitle", "product_title", "item", "product_name"));
        COLUMN_ALIASES.put("quantity", Arrays.asList("수량", "개수", "양", "quantity", "qty", "count", "amount"));
        COLUMN_ALIASES.put("date", Arrays.asList("날짜", "일자", "기준일", "date", "datetime", "day"));
        COLUMN_ALIASES.put("company_id", Arrays.asList("회사", "회사id", "company", "companyid", "company_id", "companyid"));
        COLUMN_ALIASES.put("warehouse_code", Arrays.asList("창고", "창고코드", "warehouse", "warehousecode", "warehouse_code", "warehousecode"));
    }

    public static String cleanValue(String val) {
        if (val == null) {
            return "";
        }
        return val.trim().toLowerCase().replace(" ", "").replace("_", "").replace("-", "");
    }

    public int detectHeaderRow(List<List<String>> rows, List<String> columns, int maxScanRows) {
        int bestRowIdx = 0;
        int maxMatches = 0;

        int limit = Math.min(rows.size(), maxScanRows);
        for (int i = 0; i < limit; i++) {
            List<String> rowValues = rows.get(i);
            int matches = 0;
            Set<String> matchedStandards = new HashSet<>();

            for (String val : rowValues) {
                String cleaned = cleanValue(val);
                if (cleaned.isEmpty()) continue;

                for (Map.Entry<String, List<String>> entry : COLUMN_ALIASES.entrySet()) {
                    String stdCol = entry.getKey();
                    if (entry.getValue().contains(cleaned) && !matchedStandards.contains(stdCol)) {
                        matches++;
                        matchedStandards.add(stdCol);
                        break;
                    }
                }
            }

            if (matches > maxMatches) {
                maxMatches = matches;
                bestRowIdx = i;
            }
        }

        // Check original header columns as well
        int colMatches = 0;
        Set<String> matchedStandards = new HashSet<>();
        for (String col : columns) {
            String cleaned = cleanValue(col);
            for (Map.Entry<String, List<String>> entry : COLUMN_ALIASES.entrySet()) {
                String stdCol = entry.getKey();
                if (entry.getValue().contains(cleaned) && !matchedStandards.contains(stdCol)) {
                    colMatches++;
                    matchedStandards.add(stdCol);
                    break;
                }
            }
        }

        if (colMatches >= maxMatches && colMatches > 0) {
            return -1; // -1 indicates original schema header is the best match
        }

        return bestRowIdx;
    }
}
