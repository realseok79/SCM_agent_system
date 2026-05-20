package com.sigma.scm.controller;

import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.service.DashboardService;
import com.sigma.scm.service.CrossDockingService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class DashboardControllerTest {

    @Mock
    private DashboardService dashboardService;

    @Mock
    private CrossDockingService crossDockingService;

    @InjectMocks
    private DashboardController dashboardController;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testGetSummary() {
        Map<String, Object> mockSummary = new HashMap<>();
        mockSummary.put("totalRegions", 5);
        when(dashboardService.getSummary()).thenReturn(mockSummary);

        ResponseEntity<Map<String, Object>> response = dashboardController.getSummary();

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(5, response.getBody().get("totalRegions"));
    }

    @Test
    public void testGetStockTrend() {
        List<Map<String, Object>> mockTrend = new ArrayList<>();
        when(dashboardService.getStockTrend()).thenReturn(mockTrend);

        ResponseEntity<List<Map<String, Object>>> response = dashboardController.getStockTrend();

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
    }

    @Test
    public void testGetRegionInventory() {
        List<RegionInventory> mockInventory = new ArrayList<>();
        when(dashboardService.getRegionInventory("KR-11", "Mask")).thenReturn(mockInventory);

        ResponseEntity<List<RegionInventory>> response = dashboardController.getRegionInventory("KR-11", "Mask");

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
    }

    @Test
    public void testGetIntegrity() {
        Map<String, Object> mockIntegrity = new HashMap<>();
        mockIntegrity.put("isConsistent", true);
        when(dashboardService.getIntegrity("KR-11", "Mask", "2026-05-20")).thenReturn(mockIntegrity);

        ResponseEntity<Map<String, Object>> response = dashboardController.getIntegrity("KR-11", "Mask", "2026-05-20");

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(true, response.getBody().get("isConsistent"));
    }

    @Test
    public void testGetRiskScore() {
        Map<String, Object> mockRisk = new HashMap<>();
        mockRisk.put("riskLevel", "LOW");
        when(dashboardService.getRiskScore("KR-11")).thenReturn(mockRisk);

        ResponseEntity<Map<String, Object>> response = dashboardController.getRiskScore("KR-11");

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("LOW", response.getBody().get("riskLevel"));
    }

    @Test
    public void testGetRebalancingOrders() {
        List<com.sigma.scm.domain.InventoryRebalancingOrder> mockOrders = new ArrayList<>();
        when(dashboardService.getRebalancingOrders()).thenReturn(mockOrders);

        ResponseEntity<List<com.sigma.scm.domain.InventoryRebalancingOrder>> response = dashboardController.getRebalancingOrders();

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
    }

    @Test
    public void testCreateRebalancingOrder() {
        com.sigma.scm.domain.InventoryRebalancingOrder mockOrder = new com.sigma.scm.domain.InventoryRebalancingOrder();
        when(dashboardService.createRebalancingOrder(any())).thenReturn(mockOrder);

        ResponseEntity<com.sigma.scm.domain.InventoryRebalancingOrder> response = dashboardController.createRebalancingOrder(mockOrder);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
    }
}
