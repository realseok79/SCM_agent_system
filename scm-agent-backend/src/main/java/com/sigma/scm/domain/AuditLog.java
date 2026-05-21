package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "audit_logs")
@Data
@NoArgsConstructor
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_type", length = 50, nullable = false)
    private String eventType;

    @Column(nullable = false, length = 255)
    private String message;

    @Column(name = "recorded_at")
    private LocalDateTime recordedAt = LocalDateTime.now();

    @Column(name = "triggered_by", length = 50, nullable = false)
    private String triggeredBy;

    public AuditLog(String eventType, String message, String triggeredBy) {
        this.eventType = eventType;
        this.message = message;
        this.triggeredBy = triggeredBy;
        this.recordedAt = LocalDateTime.now();
    }
}
