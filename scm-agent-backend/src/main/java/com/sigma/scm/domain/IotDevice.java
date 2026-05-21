package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "iot_devices")
@Data
@NoArgsConstructor
public class IotDevice {

    @Id
    @Column(name = "device_id", length = 50)
    private String deviceId;

    @Column(name = "region_code", nullable = false, length = 50)
    private String regionCode;

    @Column(name = "sensor_type", nullable = false, length = 20)
    private String sensorType;

    @Column(length = 20)
    private String status = "ACTIVE";

    @Column(name = "last_ping_at")
    private LocalDateTime lastPingAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
