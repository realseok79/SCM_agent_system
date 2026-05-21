package com.sigma.scm.service;

import com.sigma.scm.domain.AuditLog;
import com.sigma.scm.domain.IotDevice;
import com.sigma.scm.domain.IotTelemetry;
import com.sigma.scm.repository.AuditLogRepository;
import com.sigma.scm.repository.IotDeviceRepository;
import com.sigma.scm.repository.IotTelemetryRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
@Slf4j
public class IotService {

    private final IotDeviceRepository iotDeviceRepository;
    private final IotTelemetryRepository iotTelemetryRepository;
    private final AuditLogRepository auditLogRepository;

    public List<IotDevice> getDevices(String status) {
        if (status != null && !status.trim().isEmpty()) {
            return iotDeviceRepository.findByStatus(status);
        }
        return iotDeviceRepository.findAll();
    }

    @Transactional
    public IotDevice registerDevice(IotDevice device) {
        if (device.getStatus() == null) {
            device.setStatus("ACTIVE");
        }
        device.setCreatedAt(LocalDateTime.now());
        device.setLastPingAt(null);
        IotDevice saved = iotDeviceRepository.save(device);
        
        auditLogRepository.save(new AuditLog("DEVICE_REGISTERED",
            "신규 IoT 디바이스 등록 완료: " + saved.getDeviceId() + " (" + saved.getSensorType() + ", 지점: " + saved.getRegionCode() + ")",
            "ADMIN_USER"));
            
        return saved;
    }

    @Transactional
    public IotDevice updateDeviceStatus(String deviceId, String status) {
        IotDevice device = iotDeviceRepository.findById(deviceId)
                .orElseThrow(() -> new IllegalArgumentException("IoT Device not found with ID: " + deviceId));
        device.setStatus(status);
        IotDevice saved = iotDeviceRepository.save(device);
        
        String eventType = "ACTIVE".equals(status) ? "DEVICE_ACTIVE" : "DEVICE_MAINTENANCE";
        auditLogRepository.save(new AuditLog(eventType,
            "IoT 디바이스 상태 전환: " + deviceId + " ➔ " + status,
            "ADMIN_USER"));
            
        return saved;
    }

    @Transactional
    public List<IotTelemetry> saveTelemetry(List<IotTelemetry> telemetries) {
        List<IotTelemetry> saved = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();
        for (IotTelemetry tel : telemetries) {
            tel.setRecordedAt(now);
            saved.add(iotTelemetryRepository.save(tel));

            // Update device last ping time
            iotDeviceRepository.findById(tel.getDeviceId()).ifPresent(device -> {
                device.setLastPingAt(now);
                iotDeviceRepository.save(device);
            });
        }
        return saved;
    }

    public Map<String, Object> getHealthSummary() {
        List<IotDevice> allDevices = iotDeviceRepository.findAll();
        
        if (allDevices.isEmpty()) {
            Map<String, Object> result = new HashMap<>();
            result.put("averageHealthScore", 100.0);
            result.put("regionHealthScores", new HashMap<String, Double>());
            return result;
        }

        Map<String, List<IotDevice>> devicesByRegion = allDevices.stream()
                .collect(Collectors.groupingBy(IotDevice::getRegionCode));

        Map<String, Double> regionScores = new HashMap<>();
        double totalScoreSum = 0.0;
        int regionCount = 0;

        for (Map.Entry<String, List<IotDevice>> entry : devicesByRegion.entrySet()) {
            String regionCode = entry.getKey();
            List<IotDevice> devices = entry.getValue();
            double regionPenalty = 0.0;

            for (IotDevice dev : devices) {
                if ("MAINTENANCE".equals(dev.getStatus())) {
                    regionPenalty += 30.0; // Maintenance status penalty
                    continue;
                }

                // Get all telemetries for this device
                List<IotTelemetry> telemetries = iotTelemetryRepository.findByDeviceId(dev.getDeviceId());
                if (telemetries.isEmpty()) {
                    continue;
                }
                
                IotTelemetry latest = telemetries.stream()
                        .max(Comparator.comparing(IotTelemetry::getRecordedAt))
                        .orElse(null);

                if (latest != null) {
                    double val = latest.getValue();
                    String sType = dev.getSensorType().toLowerCase();
                    if ("temperature".equals(sType)) {
                         if (val < 10.0) regionPenalty += ((10.0 - val) / 10.0) * 25.0;
                         else if (val > 30.0) regionPenalty += ((val - 30.0) / 30.0) * 30.0;
                    } else if ("humidity".equals(sType)) {
                         if (val < 30.0) regionPenalty += ((30.0 - val) / 30.0) * 25.0;
                         else if (val > 65.0) regionPenalty += ((val - 65.0) / 65.0) * 30.0;
                    } else if ("vibration".equals(sType)) {
                         if (val < 0.0) regionPenalty += ((0.0 - val) / 0.8) * 25.0;
                         else if (val > 0.8) regionPenalty += ((val - 0.8) / 0.8) * 30.0;
                    }
                }
            }

            double regionHealth = Math.max(0.0, Math.min(100.0, 100.0 - regionPenalty));
            regionScores.put(regionCode, regionHealth);
            totalScoreSum += regionHealth;
            regionCount++;
        }

        double averageHealthScore = regionCount > 0 ? (totalScoreSum / regionCount) : 100.0;

        Map<String, Object> result = new HashMap<>();
        result.put("averageHealthScore", averageHealthScore);
        result.put("regionHealthScores", regionScores);
        return result;
    }
}
