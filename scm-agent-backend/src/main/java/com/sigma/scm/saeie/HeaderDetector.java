package com.sigma.scm.saeie;

import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class HeaderDetector {

    public static final Map<String, List<String>> COLUMN_ALIASES = new HashMap<>();

    static {
        COLUMN_ALIASES.put("region_code", Arrays.asList(
            "지점", "지역", "지역명", "지역코드", "출발지", "도착지", "경유지",
            "region", "regionname", "location", "branch", "region_code", "regioncode",
            "출발지역", "도착지역", "배송지", "배송지역", "시도", "시군구"
        ));
        COLUMN_ALIASES.put("product_name", Arrays.asList(
            "상품명", "상품이름", "품목", "품목명", "품명", "제품명", "제품", "물품명", "물품",
            "product", "productname", "producttitle", "product_title", "item", "product_name",
            "itemname", "item_name", "goods", "goodsname"
        ));
        COLUMN_ALIASES.put("quantity", Arrays.asList(
            "수량", "개수", "양", "재고량", "재고수량", "입고수량", "출고수량", "이동수량",
            "quantity", "qty", "count", "amount", "stock", "volume"
        ));
        COLUMN_ALIASES.put("date", Arrays.asList(
            "날짜", "일자", "기준일", "입고일", "출고일", "이동일", "등록일", "주문일",
            "date", "datetime", "day", "orderdate", "order_date", "shipdate", "ship_date"
        ));
        COLUMN_ALIASES.put("company_id", Arrays.asList(
            "회사", "회사id", "회사코드", "업체", "업체명", "거래처",
            "company", "companyid", "company_id", "vendor", "supplier"
        ));
        COLUMN_ALIASES.put("warehouse_code", Arrays.asList(
            "창고", "창고코드", "창고명", "보관소",
            "warehouse", "warehousecode", "warehouse_code"
        ));
        COLUMN_ALIASES.put("item_code", Arrays.asList(
            "품목코드", "상품코드", "제품코드", "물품코드", "코드", "sku",
            "itemcode", "item_code", "productcode", "product_code", "sku_code"
        ));
        COLUMN_ALIASES.put("category", Arrays.asList(
            "카테고리", "분류", "품목분류", "상품분류", "대분류", "중분류", "소분류",
            "category", "categoryname", "category_name", "classification", "type"
        ));
        COLUMN_ALIASES.put("route", Arrays.asList(
            "경로", "이동경로", "운송경로", "배송경로", "노선",
            "route", "path", "routename", "route_name"
        ));
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
