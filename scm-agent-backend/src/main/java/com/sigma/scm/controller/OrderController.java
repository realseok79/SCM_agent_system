package com.sigma.scm.controller;

import com.sigma.scm.domain.InventoryRebalancingOrder;
import com.sigma.scm.service.DashboardService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final DashboardService dashboardService;

    @PostMapping("/{id}/approve")
    public ResponseEntity<InventoryRebalancingOrder> approveOrder(@PathVariable("id") Long id) {
        return ResponseEntity.ok(dashboardService.approveRebalancingOrder(id));
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<InventoryRebalancingOrder> rejectOrder(
            @PathVariable("id") Long id,
            @RequestBody(required = false) Map<String, String> body) {
        String reason = body != null ? body.get("reason") : null;
        return ResponseEntity.ok(dashboardService.rejectRebalancingOrder(id, reason));
    }
}
