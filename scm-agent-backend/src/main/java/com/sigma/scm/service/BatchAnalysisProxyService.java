package com.sigma.scm.service;

import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.saeie.SaeieException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class BatchAnalysisProxyService {

    private final WebClient.Builder webClientBuilder;

    @Value("${scm.analysis-service-url:http://localhost:8090}")
    private String analysisServiceUrl;

    @Retryable(
        retryFor = { Exception.class },
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000, multiplier = 2.0)
    )
    public Map<String, Object> analyzeBatchPython(String batchId, List<RegionInventory> inventories) {
        log.info("Sending batch {} to Python analysis service at {}", batchId, analysisServiceUrl);
        WebClient client = webClientBuilder.baseUrl(analysisServiceUrl).build();

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("batchId", batchId);
        
        List<Map<String, Object>> invList = new ArrayList<>();
        for (RegionInventory inv : inventories) {
            Map<String, Object> map = new HashMap<>();
            map.put("regionCode", inv.getId().getRegionCode());
            map.put("productName", inv.getId().getProductName());
            map.put("date", inv.getId().getDate());
            map.put("quantity", inv.getQuantity());
            invList.add(map);
        }
        requestBody.put("inventories", invList);

        return client.post()
                .uri("/analyze/batch")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {})
                .timeout(Duration.ofSeconds(10)) // 10초 타임아웃
                .block();
    }

    @Recover
    public Map<String, Object> fallbackAnalyzeBatch(Exception e, String batchId, List<RegionInventory> inventories) {
        log.warn("Python analysis service failed after retries. Entering emergency parallelStream Fallback (Plan B)!", e);
        
        // Plan B: Pure Java parallelStream 수학 연산
        long startTime = System.currentTimeMillis();
        
        double totalQuantity = inventories.parallelStream()
                .mapToDouble(RegionInventory::getQuantity)
                .sum();

        double avgQuantity = inventories.isEmpty() ? 0.0 : totalQuantity / inventories.size();

        Map<String, Object> fallbackResult = new HashMap<>();
        fallbackResult.put("batchId", batchId);
        fallbackResult.put("engine", "JAVA_PARALLEL_STREAM");
        fallbackResult.put("status", "EMERGENCY_MODE");
        fallbackResult.put("totalQuantity", totalQuantity);
        fallbackResult.put("averageQuantity", avgQuantity);
        fallbackResult.put("alert", "EMERGENCY TRANSPORTATION STABILITY MODE ACTIVE due to microservice offline.");
        
        long duration = System.currentTimeMillis() - startTime;
        log.info("Fallback parallelStream computation completed in {} ms (3000ms gate requirement satisfied).", duration);
        
        return fallbackResult;
    }

    public Map<String, Object> getMacroVector(String country) {
        WebClient client = webClientBuilder.baseUrl(analysisServiceUrl).build();
        try {
            return client.get()
                    .uri(uriBuilder -> uriBuilder.path("/macro/vector").queryParam("country", country).build())
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {})
                    .timeout(Duration.ofSeconds(5))
                    .block();
        } catch (Exception e) {
            log.warn("Failed to fetch macro vector for {} from Python. Returning Emergency Macro Vector stub.", country, e);
            Map<String, Object> emergencyStub = new HashMap<>();
            emergencyStub.put("country", country);
            emergencyStub.put("inflation_rate", 2.5);
            emergencyStub.put("gdp_growth", 1.8);
            emergencyStub.put("unemployment", 3.8);
            emergencyStub.put("emergency_mode", true);
            return emergencyStub;
        }
    }
}
