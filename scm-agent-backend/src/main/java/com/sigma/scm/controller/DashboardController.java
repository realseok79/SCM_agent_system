package com.sigma.scm.controller;

import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.domain.WeatherCache;
import com.sigma.scm.service.DashboardService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getSummary() {
        return ResponseEntity.ok(dashboardService.getSummary());
    }

    @GetMapping("/stock-trend")
    public ResponseEntity<List<Map<String, Object>>> getStockTrend() {
        return ResponseEntity.ok(dashboardService.getStockTrend());
    }

    @GetMapping("/region/{code}/inventory")
    public ResponseEntity<List<RegionInventory>> getRegionInventory(
            @PathVariable("code") String regionCode,
            @RequestParam(value = "product", required = false) String productName) {
        return ResponseEntity.ok(dashboardService.getRegionInventory(regionCode, productName));
    }

    @GetMapping("/region/{code}/weather")
    public ResponseEntity<List<WeatherCache>> getRegionWeather(
            @PathVariable("code") String regionCode) {
        return ResponseEntity.ok(dashboardService.getRegionWeather(regionCode));
    }

    @GetMapping("/region/{code}/integrity")
    public ResponseEntity<Map<String, Object>> getIntegrity(
            @PathVariable("code") String regionCode,
            @RequestParam("product") String productName,
            @RequestParam("date") String date) {
        return ResponseEntity.ok(dashboardService.getIntegrity(regionCode, productName, date));
    }

    @GetMapping("/region/{code}/risk-score")
    public ResponseEntity<Map<String, Object>> getRiskScore(
            @PathVariable("code") String regionCode) {
        return ResponseEntity.ok(dashboardService.getRiskScore(regionCode));
    }

    @GetMapping("/region/{code}/aging")
    public ResponseEntity<List<Map<String, Object>>> getAging(
            @PathVariable("code") String regionCode) {
        return ResponseEntity.ok(dashboardService.getAging(regionCode));
    }

    @GetMapping("/pending-orders")
    public ResponseEntity<List<com.sigma.scm.domain.PurchaseOrder>> getPendingOrders() {
        return ResponseEntity.ok(dashboardService.getPendingOrders());
    }

    @PostMapping("/orders/{id}/approve")
    public ResponseEntity<com.sigma.scm.domain.PurchaseOrder> approveOrder(
            @PathVariable("id") Long id) {
        return ResponseEntity.ok(dashboardService.approveOrder(id));
    }

    @PostMapping("/orders/{id}/reject")
    public ResponseEntity<com.sigma.scm.domain.PurchaseOrder> rejectOrder(
            @PathVariable("id") Long id,
            @RequestBody Map<String, String> body) {
        String reason = body != null ? body.getOrDefault("reason", "반려 사유 미지정") : "반려 사유 미지정";
        return ResponseEntity.ok(dashboardService.rejectOrder(id, reason));
    }

    @GetMapping("/financials")
    public ResponseEntity<List<com.sigma.scm.domain.ProductFinancialMaster>> getFinancialMaster() {
        return ResponseEntity.ok(dashboardService.getFinancialMaster());
    }
}
