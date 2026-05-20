package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "batch_status_history")
@Data
@NoArgsConstructor
public class BatchStatusHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "batch_id", nullable = false, length = 100)
    private String batchId;

    @Column(name = "from_status", length = 50)
    private String fromStatus;

    @Column(name = "to_status", nullable = false, length = 50)
    private String toStatus;

    @Column(name = "changed_by", nullable = false, length = 100)
    private String changedBy;

    @Column(columnDefinition = "TEXT")
    private String reason;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
