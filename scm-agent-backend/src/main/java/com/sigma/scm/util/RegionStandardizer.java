package com.sigma.scm.util;

import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
public class RegionStandardizer {

    private static final Map<String, String> CODE_MAP = new HashMap<>();

    static {
        // 기본 매핑 테이블 (Python models.py 표준 매핑과 100% 동기화)
        CODE_MAP.put("US", "US-EAST");
        CODE_MAP.put("USA", "US-EAST");
        CODE_MAP.put("UNITED STATES", "US-EAST");
        
        CODE_MAP.put("KR", "KR-SOUTH");
        CODE_MAP.put("KOREA", "KR-SOUTH");
        CODE_MAP.put("SOUTH KOREA", "KR-SOUTH");
        
        CODE_MAP.put("EU", "EU-WEST");
        CODE_MAP.put("EUROPE", "EU-WEST");
        
        CODE_MAP.put("JP", "JP-EAST");
        CODE_MAP.put("JAPAN", "JP-EAST");

        // 호남권 물류 센터 매핑
        CODE_MAP.put("호남", "호남권물류CENTER-GLOBAL");
        CODE_MAP.put("호남권물류", "호남권물류CENTER-GLOBAL");
        CODE_MAP.put("호남권물류센터", "호남권물류CENTER-GLOBAL");
    }

    public String standardize(String rawInput) {
        if (rawInput == null || rawInput.trim().isEmpty()) {
            return "UNKNOWN";
        }
        
        String key = rawInput.trim().toUpperCase();
        
        // 정밀 매핑 확인
        if (CODE_MAP.containsKey(key)) {
            return CODE_MAP.get(key);
        }
        
        // 이미 표준 규격인 경우 그대로 반환
        if (key.contains("-")) {
            return key;
        }

        return key + "-GLOBAL"; // 매핑 테이블에 없는 경우 접미사 기본 할당
    }
}
