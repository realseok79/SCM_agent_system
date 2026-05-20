package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "import_batches")
@Data
@NoArgsConstructor
public class ImportBatch {

    @Id
    @Column(name = "batch_id", length = 100)
    private String batchId;

    @Column(name = "company_id", nullable = false, length = 100)
    private String companyId;

    @Column(name = "file_name", nullable = false, length = 255)
    private String fileName;

    @Column(name = "file_sha256", nullable = false, length = 100)
    private String fileSha256;

    @Column(nullable = false, length = 50)
    private String status;

    @Column(nullable = false)
    private Integer version = 1;

    @Column(name = "drift_score")
    private Double driftScore;

    @Column(name = "quality_score")
    private Double qualityScore;

    @Column(name = "validated_payload_snapshot")
    private byte[] validatedPayloadSnapshot;

    @Column(name = "snapshot_checksum", length = 100)
    private String snapshotChecksum;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "parsed_at")
    private LocalDateTime parsedAt;

    @Column(name = "reviewed_at")
    private LocalDateTime reviewedAt;

    @Column(name = "committed_at")
    private LocalDateTime committedAt;

    @Column(name = "failed_at")
    private LocalDateTime failedAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
