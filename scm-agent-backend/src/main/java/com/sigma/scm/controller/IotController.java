package com.sigma.scm.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/iot")
public class IotController {

    @GetMapping("/health-summary")
    public ResponseEntity<Map<String, Object>> getIotHealthSummary() {
        Map<String, Object> summary = new HashMap<>();
        summary.put("sensorActiveRate", 98.8);
        summary.put("temperatureStatus", "NORMAL");
        summary.put("humidityStatus", "NORMAL");
        summary.put("gpsSyncRate", 100.0);
        summary.put("connectionStatus", "STABLE");
        summary.put("lastActiveTime", java.time.LocalDateTime.now().toString());
        return ResponseEntity.ok(summary);
    }
}
