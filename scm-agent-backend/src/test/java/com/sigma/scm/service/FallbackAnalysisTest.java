package com.sigma.scm.service;

import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.domain.RegionInventoryId;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

public class FallbackAnalysisTest {

    private BatchAnalysisProxyService proxyService;

    @BeforeEach
    public void setUp() {
        WebClient.Builder builder = mock(WebClient.Builder.class);
        proxyService = new BatchAnalysisProxyService(builder);
    }

    @Test
    public void testEmergencyParallelStreamFallbackComputation() {
        List<RegionInventory> inventories = new ArrayList<>();
        
        for (int i = 1; i <= 1000; i++) {
            RegionInventoryId id = new RegionInventoryId("KR-11", "Mask", "2026-05-19");
            RegionInventory inv = new RegionInventory();
            inv.setId(id);
            inv.setQuantity(200.0 * i);
            inventories.add(inv);
        }

        long startTime = System.nanoTime();
        Map<String, Object> result = proxyService.fallbackAnalyzeBatch(
                new RuntimeException("FastAPI microservice unreachable"),
                "BATCH_FALLBACK_TEST",
                inventories
        );
        long endTime = System.nanoTime();
        double durationMs = (endTime - startTime) / 1_000_000.0;

        assertNotNull(result);
        assertEquals("BATCH_FALLBACK_TEST", result.get("batchId"));
        assertEquals("JAVA_PARALLEL_STREAM", result.get("engine"));
        assertEquals("EMERGENCY_MODE", result.get("status"));
        
        // Assert mathematical sums
        double expectedSum = 1000.0 * 1001.0 * 100.0;
        assertEquals(expectedSum, (Double) result.get("totalQuantity"), 1e-3);
        
        // Ensure execution completes well within 3-second gate requirement (3000ms)
        assertTrue(durationMs < 3000.0, "Fallback took too long: " + durationMs + " ms");
    }
}
