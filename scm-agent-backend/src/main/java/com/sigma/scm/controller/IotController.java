package com.sigma.scm.controller;

import com.sigma.scm.domain.IotDevice;
import com.sigma.scm.domain.IotTelemetry;
import com.sigma.scm.service.IotService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/iot")
@RequiredArgsConstructor
public class IotController {

    private final IotService iotService;

    @GetMapping("/devices")
    public ResponseEntity<List<IotDevice>> getDevices(@RequestParam(value = "status", required = false) String status) {
        return ResponseEntity.ok(iotService.getDevices(status));
    }

    @PostMapping("/devices")
    public ResponseEntity<IotDevice> registerDevice(@RequestBody IotDevice device) {
        return ResponseEntity.ok(iotService.registerDevice(device));
    }

    @PatchMapping("/devices/{id}/status")
    public ResponseEntity<IotDevice> updateDeviceStatus(
            @PathVariable("id") String deviceId,
            @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (status == null || status.trim().isEmpty()) {
            throw new IllegalArgumentException("Status body parameter is required");
        }
        return ResponseEntity.ok(iotService.updateDeviceStatus(deviceId, status));
    }

    @PostMapping("/telemetry")
    public ResponseEntity<List<IotTelemetry>> saveTelemetry(@RequestBody List<IotTelemetry> telemetries) {
        return ResponseEntity.ok(iotService.saveTelemetry(telemetries));
    }

    @GetMapping("/health-summary")
    public ResponseEntity<Map<String, Object>> getHealthSummary() {
        return ResponseEntity.ok(iotService.getHealthSummary());
    }
}
