package com.sigma.scm.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

public class OrderGuardrailServiceTest {

    private OrderGuardrailService guardrailService;

    @BeforeEach
    public void setUp() {
        guardrailService = new OrderGuardrailService();
        ReflectionTestUtils.setField(guardrailService, "absoluteMaxCapacity", 10000.0);
        ReflectionTestUtils.setField(guardrailService, "maxOrderCeilingRatio", 3.0);
    }

    @Test
    public void testAbsoluteCeilingBreach() {
        OrderGuardrailService.GuardrailResult result = guardrailService.validateOrder(10500.0, Collections.emptyList());
        assertEquals("BLOCKED", result.getStatus());
        assertTrue(result.getReason().contains("[절대 상한 초과]"));
    }

    @Test
    public void testInitialStateSuspension() {
        OrderGuardrailService.GuardrailResult result = guardrailService.validateOrder(500.0, Arrays.asList(100.0, 120.0, 110.0));
        assertEquals("APPROVED", result.getStatus());
        assertEquals("초기 상태 절대 상한 통과", result.getReason());
    }

    @Test
    public void testRelativeCeilingBreach() {
        OrderGuardrailService.GuardrailResult result = guardrailService.validateOrder(450.0, Arrays.asList(100.0, 100.0, 100.0, 100.0, 100.0));
        assertEquals("BLOCKED", result.getStatus());
        assertTrue(result.getReason().contains("[상대 상한 초과]"));
    }

    @Test
    public void testRelativeCeilingApproved() {
        OrderGuardrailService.GuardrailResult result = guardrailService.validateOrder(250.0, Arrays.asList(100.0, 100.0, 100.0, 100.0, 100.0));
        assertEquals("APPROVED", result.getStatus());
        assertTrue(result.getReason().contains("모든 가드레일 제어 조건 만족"));
    }

    @Test
    public void testDynamicSeasonalityCeiling() {
        // Normal ceiling is 3.0x, so with avg=100, relative ceiling is 300.
        // If order is 450, it is blocked normally.
        OrderGuardrailService.GuardrailResult resultNormal = guardrailService.validateOrder(450.0, Arrays.asList(100.0, 100.0, 100.0, 100.0, 100.0), 1.0);
        assertEquals("BLOCKED", resultNormal.getStatus());

        // With seasonality factor = 2.0, dynamic ceiling ratio becomes 6.0, relative ceiling is 600.
        // Order of 450 should be approved.
        OrderGuardrailService.GuardrailResult resultSeasonal = guardrailService.validateOrder(450.0, Arrays.asList(100.0, 100.0, 100.0, 100.0, 100.0), 2.0);
        assertEquals("APPROVED", resultSeasonal.getStatus());
        assertTrue(resultSeasonal.getReason().contains("모든 가드레일 제어 조건 만족"));
    }
}
