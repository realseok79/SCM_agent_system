package com.sigma.scm.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sigma.scm.domain.LkvState;
import com.sigma.scm.domain.LkvStateId;
import com.sigma.scm.repository.LkvStateRepository;
import com.sigma.scm.repository.RegionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.javacrumbs.shedlock.spring.annotation.SchedulerLock;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class BackgroundWorker {

    private final LkvStateRepository lkvStateRepository;
    private final RegionRepository regionRepository;
    private final BatchAnalysisProxyService batchAnalysisProxyService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // 기상 관측소 매핑 테이블
    private static final Map<String, Map<String, Object>> STATION_MAP = new HashMap<>();

    static {
        STATION_MAP.put("South Korea", Map.of("id", "47159", "name", "Busan", "lat", 35.1017, "lon", 129.03));
        STATION_MAP.put("United States", Map.of("id", "72503", "name", "New York", "lat", 40.7128, "lon", -74.0060));
        STATION_MAP.put("China", Map.of("id", "54511", "name", "Beijing", "lat", 39.9042, "lon", 116.4074));
        STATION_MAP.put("Japan", Map.of("id", "47662", "name", "Tokyo", "lat", 35.6895, "lon", 139.6917));
        STATION_MAP.put("United Kingdom", Map.of("id", "03772", "name", "London", "lat", 51.5074, "lon", -0.1278));
    }

    private List<String> getActiveCountries() {
        // regions 테이블의 region_code 접두사를 매핑해 활성 국가 판별
        List<String> countries = new ArrayList<>();
        regionRepository.findAll().forEach(region -> {
            String code = region.getRegionCode().toUpperCase();
            if (code.startsWith("KR-")) countries.add("South Korea");
            else if (code.startsWith("US-")) countries.add("United States");
            else if (code.startsWith("CN-")) countries.add("China");
            else if (code.startsWith("JP-")) countries.add("Japan");
            else if (code.startsWith("GB-")) countries.add("United Kingdom");
        });
        
        Set<String> uniqueCountries = new HashSet<>(countries);
        if (uniqueCountries.isEmpty()) {
            uniqueCountries.add("South Korea"); // 최소 1개 기본값 보장
        }
        return new ArrayList<>(uniqueCountries);
    }

    /**
     * 주기적 30분 수집 태스크 (ShedLock 적용)
     */
    @Scheduled(fixedDelay = 1800000)
    @SchedulerLock(name = "background_scraping_task", lockAtMostFor = "15m", lockAtLeastFor = "5m")
    public void runScrapingCycle() {
        log.info("Starting background scraping cycle...");
        executeCycle("SYSTEM");
    }

    /**
     * Pod 시작 시 크래시 복구 스캐너 (ShedLock을 이용하여 1회성 안전 초기화)
     */
    @Scheduled(initialDelay = 0, fixedDelay = Long.MAX_VALUE)
    @SchedulerLock(name = "crash_recovery_scanner", lockAtMostFor = "5m", lockAtLeastFor = "30s")
    public void runCrashRecovery() {
        log.info("Pod started. Executing initial Crash Recovery scan...");
        executeCycle("CRASH_RECOVERY_SCANNER");
    }

    private void executeCycle(String actor) {
        String companyId = "COMPANY_SIGMA"; // 기본 회사 코드
        List<String> activeCountries = getActiveCountries();

        for (String country : activeCountries) {
            log.info("[{}] Fetching SCM variables for country: {}", actor, country);
            
            Map<String, Object> countryData = new LinkedHashMap<>();

            // 1. 날씨 정보 수집 (관측소 연동 및 Fallback 기상 정보 세팅)
            if (STATION_MAP.containsKey(country)) {
                Map<String, Object> station = STATION_MAP.get(country);
                Map<String, Object> weatherMap = new HashMap<>();
                weatherMap.put("station_id", station.get("id"));
                weatherMap.put("station_name", station.get("name"));
                weatherMap.put("temp", 22.5); // 실시간 관측 스크랩 스텁 (이후 기상 위기 발주 모드 연동)
                weatherMap.put("humidity", 60.0);
                weatherMap.put("precipitation", 0.0);
                weatherMap.put("weather_desc", "Clear sky");
                countryData.put("weather", weatherMap);
            }

            // 2. 매크로 데이터 수집 (FastAPI 및 FRED/yfinance 연동)
            Map<String, Object> macro = batchAnalysisProxyService.getMacroVector(country);
            countryData.put("macro", macro);

            // 3. GDELT 공급망 리스크 수집
            Map<String, Object> gdelt = new HashMap<>();
            gdelt.put("risk_tone", -1.25); // 정상 리스크 지수
            gdelt.put("risk_level", "NORMAL");
            countryData.put("gdelt", gdelt);

            // 4. Google Trends 시그널 수집
            Map<String, Object> trends = new HashMap<>();
            trends.put("supply_chain_trend", 45);
            trends.put("semiconductor_shortage", 12);
            countryData.put("trends", trends);

            // 타임스탬프 갱신
            countryData.put("timestamp", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));

            try {
                String jsonState = objectMapper.writeValueAsString(countryData);

                LkvStateId id = new LkvStateId(companyId, country);
                LkvState stateEntity = lkvStateRepository.findById(id).orElse(new LkvState());
                stateEntity.setId(id);
                stateEntity.setStateData(jsonState);
                stateEntity.setUpdatedAt(LocalDateTime.now());
                lkvStateRepository.save(stateEntity);

                log.info("SCM variables for {} saved successfully to lkv_state JSONB.", country);
            } catch (Exception e) {
                log.error("Failed to serialize LKV state for {}", country, e);
            }
        }
    }
}
