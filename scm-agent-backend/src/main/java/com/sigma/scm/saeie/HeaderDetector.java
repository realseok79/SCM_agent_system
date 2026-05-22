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
            "출발지역", "도착지역", "배송지", "배송지역", "시도", "시군구",
            "물류창고", "창고", "창고명", "창고코드", "센터", "센터명", "물류센터",
            "거점", "거점명", "거점코드", "지사", "지사명", "영업소", "배송센터",
            "hub", "depot", "warehouse", "center", "site", "sitename", "site_name",
            "loc", "locationname", "location_name", "locationcode", "location_code",
            "destination", "origin", "from", "to", "ship_to", "shipto",
            "수령지", "발송지", "입고처", "출고처", "보관장소", "보관소",
            "공장", "공장명", "factory", "plant", "plantcode", "plant_code"
        ));
        COLUMN_ALIASES.put("product_name", Arrays.asList(
            "상품명", "상품이름", "품목", "품목명", "품명", "제품명", "제품", "물품명", "물품",
            "product", "productname", "producttitle", "product_title", "item", "product_name",
            "itemname", "item_name", "goods", "goodsname",
            "물건", "물건명", "자재", "자재명", "자재코드", "부품", "부품명", "부품코드",
            "material", "materialname", "material_name", "part", "partname", "part_name",
            "sku", "skucode", "sku_code", "skuid", "sku_id",
            "모델", "모델명", "모델코드", "model", "modelname", "model_name",
            "상품", "아이템", "아이템명", "제품코드",
            "goodsname", "goods_name", "merchandisename", "merchandise",
            "name", "itemdescription", "item_description", "description", "품명코드"
        ));
        COLUMN_ALIASES.put("quantity", Arrays.asList(
            "수량", "개수", "양", "재고량", "재고수량", "입고수량", "출고수량", "이동수량",
            "quantity", "qty", "count", "amount", "stock", "volume",
            "물량", "물품수량", "총수량", "총량", "주문수량", "발주수량", "배송수량",
            "입고량", "출고량", "반품수량", "반입수량", "반출수량",
            "재고", "현재고", "현재재고", "가용재고", "안전재고", "적정재고",
            "판매수량", "판매량", "소비량", "사용량", "투입량",
            "orderqty", "order_qty", "orderquantity", "order_quantity",
            "stockqty", "stock_qty", "onhand", "on_hand", "balance",
            "inbound", "outbound", "inboundqty", "outboundqty",
            "units", "pcs", "ea", "boxes", "pallets", "cases",
            "totalqty", "total_qty", "totalquantity", "total_quantity"
        ));
        COLUMN_ALIASES.put("date", Arrays.asList(
            "날짜", "일자", "기준일", "입고일", "출고일", "이동일", "등록일", "주문일",
            "date", "datetime", "day", "orderdate", "order_date", "shipdate", "ship_date",
            "입고날짜", "출고날짜", "배송일", "배송일자", "발주일", "발주일자",
            "거래일", "거래일자", "처리일", "처리일자", "확인일", "작업일",
            "생산일", "생산일자", "검수일", "수령일", "반입일", "반출일",
            "기준일자", "마감일", "마감일자", "정산일", "집계일",
            "createdate", "create_date", "createdat", "created_at",
            "updatedate", "update_date", "updatedat", "updated_at",
            "transactiondate", "transaction_date", "trxdate", "trx_date",
            "receiptdate", "receipt_date", "deliverydate", "delivery_date",
            "shipmentdate", "shipment_date", "processdate", "process_date",
            "year", "month", "yyyymmdd", "기간", "월", "연월", "연도"
        ));
        COLUMN_ALIASES.put("company_id", Arrays.asList(
            "회사", "회사id", "회사코드", "업체", "업체명", "거래처",
            "company", "companyid", "company_id", "vendor", "supplier",
            "고객", "고객사", "고객명", "고객코드", "거래처명", "거래처코드",
            "client", "customer", "customerid", "customer_id"
        ));
        COLUMN_ALIASES.put("warehouse_code", Arrays.asList(
            "창고", "창고코드", "창고명", "보관소",
            "warehouse", "warehousecode", "warehouse_code",
            "물류창고코드", "센터코드", "센터명", "물류센터코드",
            "storagecode", "storage_code", "storage", "wh", "whcode", "wh_code"
        ));
        COLUMN_ALIASES.put("item_code", Arrays.asList(
            "품목코드", "상품코드", "제품코드", "물품코드", "코드", "sku",
            "itemcode", "item_code", "productcode", "product_code", "sku_code",
            "자재코드", "자재번호", "부품번호", "모델번호",
            "barcode", "바코드", "serialno", "serial_no", "lotno", "lot_no"
        ));
        COLUMN_ALIASES.put("category", Arrays.asList(
            "카테고리", "분류", "품목분류", "상품분류", "대분류", "중분류", "소분류",
            "category", "categoryname", "category_name", "classification", "type",
            "구분", "종류", "유형", "그룹", "그룹명", "품목군",
            "group", "groupname", "group_name", "class", "subclass"
        ));
        COLUMN_ALIASES.put("route", Arrays.asList(
            "경로", "이동경로", "운송경로", "배송경로", "노선",
            "route", "path", "routename", "route_name",
            "운송루트", "배송루트", "물류경로", "수송경로"
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
